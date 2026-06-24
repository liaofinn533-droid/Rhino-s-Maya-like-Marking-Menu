# -*- coding: utf-8 -*-
# ============================================================
#  Rhino 仿 Maya 标记菜单 (Marking Menu)
#  版本：v2.0 - 彩色符号图标 + 扇区高亮 + 拖拽触发
#  兼容：Rhino 6/7/8
#  作者：(你的名字)
#  仓库：(你的 GitHub 地址)
# ============================================================

import Eto.Forms as forms
import Eto.Drawing as drawing
import Rhino.UI
import rhinoscriptsyntax as rs
import math
import scriptcontext as sc

# 窗口尺寸（感应区域大小）
WINDOW_SIZE = 800
HALF_SIZE = WINDOW_SIZE // 2

# 扇区定义：名称, 起始数学角度(0°=右, 逆时针), 符号, 符号颜色
SECTORS = [
    ("Point",    330, "●", drawing.Color.FromArgb(255, 100, 200, 255)),   # 亮蓝点
    ("Lines",    30,  "╱", drawing.Color.FromArgb(255, 180, 255, 100)),   # 亮绿斜线
    ("Curve",    90,  "∿", drawing.Color.FromArgb(255, 255, 180, 100)),   # 橙色曲线
    ("Arc",      150, "⌒", drawing.Color.FromArgb(255, 255, 100, 180)),   # 粉红弧
    ("Rectangle",210, "▣", drawing.Color.FromArgb(255, 255, 255, 100)),   # 黄色方块
    ("Circle",   270, "○", drawing.Color.FromArgb(255, 100, 255, 180)),   # 薄荷绿空心圆
]
SPAN = 60  # 每个扇区覆盖角度


class MarkingMenuWindow(forms.Form):
    def __init__(self):
        forms.Form.__init__(self)
        self.WindowStyle = forms.WindowStyle.None
        self.Size = drawing.Size(WINDOW_SIZE, WINDOW_SIZE)
        self.BackgroundColor = drawing.Colors.Transparent
        self.Topmost = True

        self.drag_start = None
        self.current_mouse = drawing.PointF(HALF_SIZE, HALF_SIZE)
        self.highlighted_index = -1

        # 使用 Drawable 控件承载绘制内容（Eto Form.Paint 不可靠）
        self.canvas = forms.Drawable()
        self.canvas.Paint += self.on_paint
        self.Content = self.canvas

        self.canvas.KeyDown += self.on_key_down
        self.canvas.MouseDown += self.on_mouse_down
        self.canvas.MouseMove += self.on_mouse_move
        self.canvas.MouseUp += self.on_mouse_up
        self.LostFocus += self.on_lost_focus   # 失焦自动关闭

    # ---- 绘制 ----
    def on_paint(self, sender, e):
        g = e.Graphics
        cx, cy = HALF_SIZE, HALF_SIZE
        outer_radius = 200
        inner_radius = 80

        # 1. 半透明外圆背景（让菜单在复杂模型上也能看清）
        bg_brush = drawing.SolidBrush(drawing.Color.FromArgb(25, 255, 255, 255))
        g.FillEllipse(bg_brush, cx - outer_radius, cy - outer_radius,
                      outer_radius * 2, outer_radius * 2)

        # 2. 高亮扇区（拖拽时显示，指示当前方向）
        if self.drag_start is not None and self.highlighted_index >= 0:
            _, start_math, _, _ = SECTORS[self.highlighted_index]
            center_math = (start_math + SPAN / 2) % 360
            center_eto = (-center_math) % 360           # 数学角→Eto绘制角
            start_eto = (center_eto - SPAN / 2) % 360
            sweep_eto = SPAN
            highlight_brush = drawing.SolidBrush(
                drawing.Color.FromArgb(80, 100, 180, 255)
            )
            g.FillPie(highlight_brush,
                      cx - outer_radius, cy - outer_radius,
                      outer_radius * 2, outer_radius * 2,
                      start_eto, sweep_eto)

        # 3. 中心圆环（内外圆叠加，形成环状）
        outer_pen = drawing.Pen(drawing.Color.FromArgb(200, 180, 180, 200), 3)
        g.DrawEllipse(outer_pen, cx - outer_radius, cy - outer_radius,
                      outer_radius * 2, outer_radius * 2)
        inner_pen = drawing.Pen(drawing.Color.FromArgb(200, 180, 180, 200), 3)
        g.DrawEllipse(inner_pen, cx - inner_radius, cy - inner_radius,
                      inner_radius * 2, inner_radius * 2)
        # 环内填充暗色，让图标更突出
        ring_brush = drawing.SolidBrush(drawing.Color.FromArgb(100, 30, 30, 30))
        g.FillEllipse(ring_brush, cx - inner_radius, cy - inner_radius,
                      inner_radius * 2, inner_radius * 2)

        # 4. 工具符号（彩色 Unicode 图标，代替文字）
        symbol_font = drawing.Font("Arial", 26)
        text_radius = (inner_radius + outer_radius) // 2   # 图标放在环中间

        for name, start_math, symbol, color in SECTORS:
            center_math = (start_math + SPAN / 2) % 360
            center_rad = math.radians(center_math)
            x_center = cx + text_radius * math.cos(center_rad)
            y_center = cy - text_radius * math.sin(center_rad)

            # 居中绘制符号
            size = g.MeasureString(symbol_font, symbol)
            tx = x_center - size.Width / 2
            ty = y_center - size.Height / 2
            g.DrawText(symbol_font, color, tx, ty, symbol)

        # 5. 拖拽轨迹线（从按下点到当前鼠标位置）
        if self.drag_start is not None:
            line_pen = drawing.Pen(drawing.Colors.LightSkyBlue, 3)
            g.DrawLine(line_pen, self.drag_start, self.current_mouse)

    # ---- 扇区判断 ----
    def update_highlight(self, mouse_x, mouse_y):
        """根据鼠标位置计算当前所在的扇区索引"""
        dx = mouse_x - HALF_SIZE
        dy = HALF_SIZE - mouse_y          # 屏幕 Y 转为数学 Y (向上为正)
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360

        self.highlighted_index = -1
        for i, (_, start_math, _, _) in enumerate(SECTORS):
            end_math = (start_math + SPAN) % 360
            if start_math < end_math:
                if start_math <= angle < end_math:
                    self.highlighted_index = i
                    break
            else:   # 跨 0° 的扇区（Point）
                if angle >= start_math or angle < end_math:
                    self.highlighted_index = i
                    break

    # ---- 事件处理 ----
    def on_lost_focus(self, sender, e):
        """窗口失去焦点时自动关闭"""
        self.Close()

    def on_key_down(self, sender, e):
        """ESC 键关闭菜单"""
        if e.Key == forms.Keys.Escape:
            self.Close()

    def on_mouse_down(self, sender, e):
        """鼠标左键按下：开始拖拽"""
        if e.Buttons == forms.MouseButtons.Primary:
            self.drag_start = e.Location
            self.current_mouse = e.Location
            self.update_highlight(e.Location.X, e.Location.Y)
            self.Content.Invalidate()

    def on_mouse_move(self, sender, e):
        """鼠标移动：更新拖拽线和高亮扇区"""
        if self.drag_start is not None:
            self.current_mouse = e.Location
            self.update_highlight(e.Location.X, e.Location.Y)
            self.Content.Invalidate()

    def on_mouse_up(self, sender, e):
        """鼠标左键松开：执行对应的工具栏命令"""
        if self.drag_start is None:
            return

        # 获取选中的工具名
        selected = None
        if self.highlighted_index >= 0:
            selected = SECTORS[self.highlighted_index][0]

        self.Close()   # 无论是否选中，先关闭菜单

        # 距离太短视为误触，取消
        delta_x = e.Location.X - self.drag_start.X
        delta_y = self.drag_start.Y - e.Location.Y
        if math.hypot(delta_x, delta_y) < 20:
            print("[ACTION] 滑动距离太短，取消")
            return

        if selected is None:
            print("[ACTION] 未识别扇区，取消")
            return

        # 弹出对应工具栏（工具栏名与扇区名一致，从 SECTORS 自动派生）
        try:
            rs.Command('! _PopupToolbar "{}"'.format(selected))
        except:
            print("[ERROR] 无法弹出工具栏: {}".format(selected))


def run_menu():
    """启动标记菜单（外部调用入口）"""
    # 关闭已存在的旧菜单，避免多个窗口叠加
    if "MyMarkingMenu" in sc.sticky:
        try:
            sc.sticky["MyMarkingMenu"].Close()
        except:
            pass

    # 获取当前鼠标屏幕位置（带空值保护）
    mouse_pos = forms.Mouse.Position
    if mouse_pos is None:
        import System.Windows.Forms as swf
        screen_center = drawing.Point(
            swf.Screen.PrimaryScreen.Bounds.Width // 2,
            swf.Screen.PrimaryScreen.Bounds.Height // 2
        )
        mouse_pos = screen_center

    # 创建菜单窗口，使中心对准鼠标
    menu = MarkingMenuWindow()
    menu.Location = drawing.Point(
        int(mouse_pos.X) - HALF_SIZE,
        int(mouse_pos.Y) - HALF_SIZE
    )
    # 绑定到 Rhino 主窗口（防止空引用，且确保随 Rhino 关闭而释放）
    menu.Owner = Rhino.UI.RhinoEtoApp.MainWindow

    # 保存引用并显示
    sc.sticky["MyMarkingMenu"] = menu
    menu.Show()


# 直接运行脚本时启动菜单
if __name__ == "__main__":
    run_menu()