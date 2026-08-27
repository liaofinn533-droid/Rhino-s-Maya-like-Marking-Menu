# -*- coding: utf-8 -*-
# ============================================================
#  Rhino 仿 Maya 标记菜单 (Marking Menu) v3
#  功能：鼠标拖拽呼出扇形菜单，松开后直接执行对应 Rhino 命令
#  配置：同目录 config.json（扇区/命令/颜色/提示），改完即生效
#  呼出：Rhino 别名 _MM（工具 -> 选项 -> 别名）
#  兼容：Rhino 8（IronPython 2.7 / CPython 3.9）
# ============================================================

import codecs
import json
import math
import os

import Eto.Drawing as drawing
import Eto.Forms as forms
import Rhino.UI
import rhinoscriptsyntax as rs
import scriptcontext as sc

# ---------------- 默认配置（config.json 缺失/损坏时兜底） ----------------
DEFAULT_CONFIG = {
    "menu_size": 800,
    "min_drag": 20,
    "sectors": [
        {"name": "布尔差集", "command": "BooleanDifference", "symbol": "⊖", "color": "#E86496FA", "tooltip": "布尔差集 BooleanDifference"},
        {"name": "布尔并集", "command": "BooleanUnion", "symbol": "∪", "color": "#E84AC26C", "tooltip": "布尔并集 BooleanUnion"},
        {"name": "混接曲面", "command": "BlendSrf", "symbol": "≈", "color": "#E8F0A54A", "tooltip": "混接曲面 BlendSrf"},
        {"name": "边缘圆角", "command": "FilletEdge", "symbol": "⌒", "color": "#E8E06C6C", "tooltip": "边缘圆角 FilletEdge"},
        {"name": "双轨扫掠", "command": "Sweep2", "symbol": "∥", "color": "#E8A06CD8", "tooltip": "双轨扫掠 Sweep2"},
        {"name": "曲面偏移", "command": "OffsetSrf", "symbol": "↗", "color": "#E86CA8D8", "tooltip": "曲面偏移 OffsetSrf"},
    ],
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    """读取 config.json；失败时回退到内置默认配置"""
    try:
        with codecs.open(CONFIG_PATH, "r", "utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict) or not isinstance(cfg.get("sectors"), list) or len(cfg["sectors"]) < 2:
            raise ValueError("sectors 配置无效")
        size = int(cfg.get("menu_size", 800))
        cfg["menu_size"] = size if 400 <= size <= 1600 else 800
        cfg["min_drag"] = max(5, int(cfg.get("min_drag", 20)))
        for s in cfg["sectors"]:
            s["name"] = s.get("name") or ""
            s["command"] = (s.get("command") or "").strip()
            s["symbol"] = s.get("symbol") or "?"
            s["color"] = s.get("color") or "#FFFFFFFF"
            s["tooltip"] = s.get("tooltip") or s["name"]
        return cfg
    except Exception as e:
        print("[标记菜单] 配置读取失败，已使用内置默认配置：%s" % e)
        return DEFAULT_CONFIG


def parse_color(hex_str):
    """#AARRGGBB 或 #RRGGBB -> Eto 颜色；失败返回白色"""
    try:
        h = hex_str.strip().lstrip("#")
        if len(h) == 6:
            h = "FF" + h
        a = int(h[0:2], 16)
        r = int(h[2:4], 16)
        g = int(h[4:6], 16)
        b = int(h[6:8], 16)
        return drawing.Color.FromArgb(a, r, g, b)
    except Exception:
        return drawing.Color.FromArgb(255, 255, 255, 255)


def command_exists(command):
    """判断 Rhino 中是否存在该命令；无法判断时返回 None（不拦截）"""
    try:
        import Rhino.Commands as rc
        name = command.lstrip("!_").strip()
        return bool(rc.Command.IsCommand(name))
    except Exception:
        return None




def make_font(name, size):
    """创建字体；指定字体不可用时回退 Arial"""
    try:
        return drawing.Font(name, size)
    except Exception:
        return drawing.Font("Arial", size)

class MarkingMenuWindow(forms.Form):
    def __init__(self, config):
        forms.Form.__init__(self)
        self.config = config
        self.size = int(config["menu_size"])
        self.half = self.size // 2
        self.sectors = config["sectors"]
        self.count = len(self.sectors)
        self.span = 360.0 / self.count
        self.min_drag = int(config["min_drag"])

        self._closed = False
        self.WindowStyle = forms.WindowStyle.None
        self.Size = drawing.Size(self.size, self.size)
        self.BackgroundColor = drawing.Colors.Transparent
        self.Topmost = True

        self.drag_start = None
        self.current_mouse = drawing.PointF(self.half, self.half)
        self.highlighted_index = -1
        self.current_tooltip = ""

        self.canvas = forms.Drawable()
        self.canvas.Paint += self.on_paint
        self.Content = self.canvas

        self.canvas.KeyDown += self.on_key_down
        self.KeyDown += self.on_key_down
        self.canvas.MouseDown += self.on_mouse_down
        self.canvas.MouseMove += self.on_mouse_move
        self.canvas.MouseUp += self.on_mouse_up
        self.LostFocus += self.on_lost_focus

    # ---------------- 绘制 ----------------
    def on_paint(self, sender, e):
        g = e.Graphics
        cx, cy = self.half, self.half
        outer_radius = self.half - 40
        inner_radius = int(outer_radius * 0.35)
        if outer_radius <= 0:
            return

        # 1. 半透明外圆背景
        bg_brush = drawing.SolidBrush(drawing.Color.FromArgb(25, 255, 255, 255))
        g.FillEllipse(bg_brush, cx - outer_radius, cy - outer_radius,
                      outer_radius * 2, outer_radius * 2)

        # 2. 高亮扇区（拖拽/悬停时）
        if self.highlighted_index >= 0:
            center_math = (self.highlighted_index * self.span + self.span / 2.0) % 360.0
            center_eto = (-center_math) % 360.0
            start_eto = (center_eto - self.span / 2.0) % 360.0
            highlight_brush = drawing.SolidBrush(drawing.Color.FromArgb(80, 100, 180, 255))
            g.FillPie(highlight_brush,
                      cx - outer_radius, cy - outer_radius,
                      outer_radius * 2, outer_radius * 2,
                      start_eto, self.span)

        # 3. 中心圆环 + 分隔线
        outer_pen = drawing.Pen(drawing.Color.FromArgb(200, 180, 180, 200), 3)
        g.DrawEllipse(outer_pen, cx - outer_radius, cy - outer_radius,
                      outer_radius * 2, outer_radius * 2)
        inner_pen = drawing.Pen(drawing.Color.FromArgb(200, 180, 180, 200), 3)
        g.DrawEllipse(inner_pen, cx - inner_radius, cy - inner_radius,
                      inner_radius * 2, inner_radius * 2)
        ring_brush = drawing.SolidBrush(drawing.Color.FromArgb(100, 30, 30, 30))
        g.FillEllipse(ring_brush, cx - inner_radius, cy - inner_radius,
                      inner_radius * 2, inner_radius * 2)
        sep_pen = drawing.Pen(drawing.Color.FromArgb(120, 200, 200, 220), 1)
        for i in range(self.count):
            a = math.radians(i * self.span)
            x1 = cx + inner_radius * math.cos(a)
            y1 = cy - inner_radius * math.sin(a)
            x2 = cx + outer_radius * math.cos(a)
            y2 = cy - outer_radius * math.sin(a)
            g.DrawLine(sep_pen, x1, y1, x2, y2)

        # 4. 工具符号（彩色 Unicode 图标）
        symbol_font = make_font("Arial", 26)
        text_radius = (inner_radius + outer_radius) // 2
        for i, s in enumerate(self.sectors):
            center_math = (i * self.span + self.span / 2.0) % 360.0
            rad = math.radians(center_math)
            x_center = cx + text_radius * math.cos(rad)
            y_center = cy - text_radius * math.sin(rad)
            color = parse_color(s.get("color"))
            sym = s.get("symbol") or "?"
            ts = g.MeasureString(symbol_font, sym)
            g.DrawText(symbol_font, color, x_center - ts.Width / 2,
                       y_center - ts.Height / 2, sym)

        # 5. 拖拽轨迹线
        if self.drag_start is not None:
            line_pen = drawing.Pen(drawing.Colors.LightSkyBlue, 3)
            g.DrawLine(line_pen, self.drag_start, self.current_mouse)

        # 6. 命令名提示（悬停/拖拽时显示在鼠标旁）
        if self.current_tooltip:
            tip_font = make_font("Microsoft YaHei", 12)
            ts = g.MeasureString(tip_font, self.current_tooltip)
            tip_x = min(self.current_mouse.X + 14, self.size - ts.Width - 8)
            tip_y = min(self.current_mouse.Y + 14, self.size - ts.Height - 4)
            tip_x = max(tip_x, 4)
            tip_y = max(tip_y, 4)
            bg = drawing.SolidBrush(drawing.Color.FromArgb(210, 20, 20, 20))
            g.FillRectangle(bg, tip_x - 6, tip_y - 2,
                            ts.Width + 12, ts.Height + 6)
            g.DrawText(tip_font, drawing.Colors.White, tip_x, tip_y,
                       self.current_tooltip)

    # ---------------- 扇区判断（角度自动均分，通用算法） ----------------
    def update_highlight(self, mouse_x, mouse_y):
        dx = mouse_x - self.half
        dy = self.half - mouse_y          # 屏幕 Y 转数学 Y（向上为正）
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360.0
        idx = int(angle // self.span) % self.count
        self.highlighted_index = idx
        self.current_tooltip = self.sectors[idx].get("tooltip") or self.sectors[idx].get("name") or ""

    # ---------------- 事件处理 ----------------
    def close_once(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.Close()
        except Exception:
            pass

    def on_lost_focus(self, sender, e):
        self.close_once()

    def on_key_down(self, sender, e):
        if e.Key == forms.Keys.Escape:
            self.close_once()

    def on_mouse_down(self, sender, e):
        if e.Buttons == forms.MouseButtons.Primary:
            self.drag_start = e.Location
            self.current_mouse = e.Location
            self.update_highlight(e.Location.X, e.Location.Y)
            self.canvas.Invalidate()

    def on_mouse_move(self, sender, e):
        self.current_mouse = e.Location
        self.update_highlight(e.Location.X, e.Location.Y)
        self.canvas.Invalidate()

    def on_mouse_up(self, sender, e):
        if self.drag_start is None:
            return

        selected = None
        if self.highlighted_index >= 0:
            selected = self.sectors[self.highlighted_index]

        drag_x = e.Location.X - self.drag_start.X
        drag_y = self.drag_start.Y - e.Location.Y
        distance = math.hypot(drag_x, drag_y)

        self.close_once()   # 先关闭菜单，再执行命令

        if distance < self.min_drag:
            print("[标记菜单] 滑动距离太短，取消")
            return
        if selected is None:
            print("[标记菜单] 未识别扇区，取消")
            return

        command = selected.get("command") or ""
        if not command:
            print("[标记菜单] 该扇区未配置命令：%s" % selected.get("name"))
            return

        exists = command_exists(command)
        if exists is False:
            print("[标记菜单] 命令不存在，已取消：%s" % command)
            return

        print("[标记菜单] 执行命令：%s" % command)
        try:
            rs.Command("!_" + command, echo=False)
        except Exception as ex:
            print("[标记菜单] 执行命令出错：%s (%s)" % (command, ex))


def run_menu():
    """启动标记菜单（别名 _MM 的入口）"""
    if "MyMarkingMenu" in sc.sticky:
        try:
            sc.sticky["MyMarkingMenu"].close_once()
        except Exception:
            pass

    config = load_config()
    size = int(config["menu_size"])
    half = size // 2

    # 获取鼠标屏幕位置
    try:
        import System.Windows.Forms as swf
        pos = swf.Cursor.Position
        mouse_x, mouse_y = pos.X, pos.Y
    except Exception:
        try:
            p = forms.Mouse.Position
            mouse_x, mouse_y = p.X, p.Y
        except Exception:
            mouse_x, mouse_y = 400, 400

    x = int(mouse_x) - half
    y = int(mouse_y) - half

    # 屏幕边界限制（多显示器/DPI 下菜单不超出屏幕）
    try:
        import System.Windows.Forms as swf
        screen = swf.Screen.FromPoint(swf.Cursor.Position)
        b = screen.Bounds
        x = max(b.Left, min(x, max(b.Left, b.Right - size)))
        y = max(b.Top, min(y, max(b.Top, b.Bottom - size)))
    except Exception:
        pass

    menu = MarkingMenuWindow(config)
    menu.Location = drawing.Point(int(x), int(y))
    menu.Owner = Rhino.UI.RhinoEtoApp.MainWindow

    sc.sticky["MyMarkingMenu"] = menu
    menu.Show()


if __name__ == "__main__":
    run_menu()