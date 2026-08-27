# -*- coding: utf-8 -*-
# ============================================================
#  Rhino 仿 Maya 标记菜单 (Marking Menu) v7（两级 · 圆形标签环）
#  逻辑：
#    第一步：一级菜单 = 中心一圈"工具集"；点一下（或按住拖上去）选中一个工具集
#    第二步：选中的工具集变成新的圆心，它的工具绕成一个"圆形标签环"；
#            点某个工具执行；点空白/中心返回上一级；ESC 关闭
#  样式：文字小方框 + 中心连线（参考 RS2 文字菜单风格）
#  视觉：透明底 + 淡白柔光、柔和发光、圆角方框、玻璃高光、渐变中心圆点
#  配置：同目录 config.json（groups/tools/命令/颜色/提示），改完即生效
#  呼出：Rhino 别名 _MM，或"工具 -> 选项 -> 键盘"绑快捷键；
#        按住 Ctrl 呼出时 = 松手提交模式（悬停选中，松手执行）
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
    "menu_size": 460,
    "min_drag": 20,
    "groups": [
        {"name": "布尔", "color": "#E86496FA", "default_command": "BooleanUnion", "tooltip": "布尔运算", "tools": [
            {"name": "差集", "command": "BooleanDifference", "tooltip": "布尔差集 BooleanDifference"},
            {"name": "并集", "command": "BooleanUnion", "tooltip": "布尔并集 BooleanUnion"},
            {"name": "交集", "command": "BooleanIntersection", "tooltip": "布尔交集 BooleanIntersection"},
            {"name": "分割", "command": "Split", "tooltip": "分割 Split"},
        ]},
        {"name": "曲面", "color": "#E84AC26C", "default_command": "BlendSrf", "tooltip": "曲面", "tools": [
            {"name": "混接曲面", "command": "BlendSrf", "tooltip": "混接曲面 BlendSrf"},
            {"name": "双轨扫掠", "command": "Sweep2", "tooltip": "双轨扫掠 Sweep2"},
            {"name": "放样", "command": "Loft", "tooltip": "放样 Loft"},
            {"name": "曲面偏移", "command": "OffsetSrf", "tooltip": "曲面偏移 OffsetSrf"},
        ]},
        {"name": "圆角", "color": "#E8F0A54A", "default_command": "FilletEdge", "tooltip": "圆角倒角", "tools": [
            {"name": "边缘圆角", "command": "FilletEdge", "tooltip": "边缘圆角 FilletEdge"},
            {"name": "边倒角", "command": "ChamferEdge", "tooltip": "边倒角 ChamferEdge"},
        ]},
        {"name": "修剪", "color": "#E8E06C6C", "default_command": "Trim", "tooltip": "修剪编辑", "tools": [
            {"name": "修剪", "command": "Trim", "tooltip": "修剪 Trim"},
            {"name": "延伸", "command": "Extend", "tooltip": "延伸 Extend"},
            {"name": "偏移", "command": "Offset", "tooltip": "偏移 Offset"},
            {"name": "炸开", "command": "Explode", "tooltip": "炸开 Explode"},
        ]},
        {"name": "结构", "color": "#E8A06CD8", "default_command": "ExtractIsocurve", "tooltip": "结构线提取", "tools": [
            {"name": "抽离结构线", "command": "ExtractIsocurve", "tooltip": "抽离结构线 ExtractIsocurve"},
            {"name": "复制边缘", "command": "DupEdge", "tooltip": "复制边缘 DupEdge"},
            {"name": "抽离曲面", "command": "ExtractSrf", "tooltip": "抽离曲面 ExtractSrf"},
        ]},
        {"name": "编辑", "color": "#E86CA8D8", "default_command": "Move", "tooltip": "基础编辑", "tools": [
            {"name": "移动", "command": "Move", "tooltip": "移动 Move"},
            {"name": "旋转", "command": "Rotate", "tooltip": "旋转 Rotate"},
            {"name": "缩放", "command": "Scale", "tooltip": "缩放 Scale"},
            {"name": "镜像", "command": "Mirror", "tooltip": "镜像 Mirror"},
        ]},
    ],
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ---------------- 布局常量 ----------------
GROUP_W = 88     # 一级工具集方框宽度
GROUP_H = 30     # 一级工具集方框高度
HUB_R = 20       # 一级中心圆点半径
TOOL_W = 64      # 二级工具方框宽度
TOOL_H = 24      # 二级工具方框高度
RING_R_MIN = 60.0   # 二级工具环最小半径
RING_R_MAX = 104.0  # 二级工具环最大半径（保证不超出窗口）

# ---------------- 视觉常量（注意：Eto 的 FromArgb 顺序是 红,绿,蓝,透明度） ----------------
FONT_LABEL = "Microsoft YaHei"
FONT_LABEL_SIZE = 13
FONT_TIP_SIZE = 12
BOX_RADIUS = 9    # 方框圆角半径
PALETTE = {
    "text":        drawing.Color.FromArgb(238, 240, 244, 255),
    "text_dim":    drawing.Color.FromArgb(150, 158, 172, 255),
    "text_shadow": drawing.Color.FromArgb(0, 0, 0, 110),
    "idle_fill":   drawing.Color.FromArgb(24, 27, 34, 200),
    "idle_fill_dim": drawing.Color.FromArgb(20, 22, 28, 110),
    "idle_border": drawing.Color.FromArgb(150, 156, 168, 130),
    "idle_border_dim": drawing.Color.FromArgb(150, 156, 168, 60),
    "line":        drawing.Color.FromArgb(165, 171, 185, 160),
    "line_dim":    drawing.Color.FromArgb(150, 156, 168, 55),
    "glass":       drawing.Color.FromArgb(255, 255, 255, 46),
    "glass_dim":   drawing.Color.FromArgb(255, 255, 255, 24),
    "hub_top":     drawing.Color.FromArgb(63, 70, 86, 255),
    "hub_bottom":  drawing.Color.FromArgb(18, 21, 28, 255),
    "hub_border":  drawing.Color.FromArgb(205, 212, 226, 210),
    "hub_glow":    drawing.Color.FromArgb(140, 175, 255, 70),
    "tip_bg":      drawing.Color.FromArgb(13, 15, 21, 235),
    "tip_border":  drawing.Color.FromArgb(150, 156, 168, 150),
}


def load_config():
    """读取 config.json；失败时回退到内置默认配置"""
    try:
        with codecs.open(CONFIG_PATH, "r", "utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            raise ValueError("配置无效")
        # 兼容旧版 sectors 配置：每个扇区转成一个"单工具"的工具集
        if not isinstance(cfg.get("groups"), list) or len(cfg["groups"]) < 1:
            if isinstance(cfg.get("sectors"), list) and len(cfg["sectors"]) >= 1:
                groups = []
                for s in cfg["sectors"]:
                    groups.append({
                        "name": s.get("name") or "",
                        "color": s.get("color") or "#FF5C9BFF",
                        "tooltip": s.get("tooltip") or "",
                        "tools": [{"name": s.get("name") or "", "command": s.get("command") or ""}],
                    })
                cfg["groups"] = groups
            else:
                raise ValueError("groups 配置无效")
        size = int(cfg.get("menu_size", 460))
        cfg["menu_size"] = size if 400 <= size <= 1600 else 460
        cfg["min_drag"] = max(5, int(cfg.get("min_drag", 20)))
        for g in cfg["groups"]:
            g["name"] = (g.get("name") or "组").strip()
            g["color"] = g.get("color") or "#FF5C9BFF"
            g["tooltip"] = g.get("tooltip") or (g["name"] + "（工具集）")
            tools = g.get("tools")
            if not isinstance(tools, list) or len(tools) < 1:
                tools = [{"name": g["name"], "command": g.get("default_command") or ""}]
            for t in tools:
                t["name"] = (t.get("name") or "").strip()
                t["command"] = (t.get("command") or "").strip()
                t["tooltip"] = t.get("tooltip") or t["command"] or t["name"]
            g["tools"] = tools
        return cfg
    except Exception as e:
        print("[标记菜单] 配置读取失败，已使用内置默认配置：%s" % e)
        return DEFAULT_CONFIG


def parse_color(hex_str):
    """#AARRGGBB 或 #RRGGBB -> Eto 颜色（Eto 参数顺序：红,绿,蓝,透明度）；失败返回蓝色"""
    try:
        h = hex_str.strip().lstrip("#")
        if len(h) == 6:
            h = "FF" + h
        a = int(h[0:2], 16)
        r = int(h[2:4], 16)
        g = int(h[4:6], 16)
        b = int(h[6:8], 16)
        return drawing.Color.FromArgb(r, g, b, a)
    except Exception:
        return drawing.Color.FromArgb(92, 155, 255, 255)


def color_parts(col):
    """Eto 颜色 -> (r, g, b) 0-255 整数（Eto 的 R/G/B 是 0~1 浮点）"""
    return (int(col.R * 255 + 0.5), int(col.G * 255 + 0.5), int(col.B * 255 + 0.5))


def make_font(name, size):
    """创建字体；指定字体不可用时回退 Arial"""
    try:
        return drawing.Font(name, size)
    except Exception:
        return drawing.Font("Arial", size)


def command_exists(command):
    """判断 Rhino 中是否存在该命令；无法判断时返回 None（不拦截）"""
    try:
        import Rhino.Commands as rc
        name = command.lstrip("!_").strip().split()[0]   # 支持 "Rectangle _3Point" 这类带选项的写法
        return bool(rc.Command.IsCommand(name))
    except Exception:
        return None


def _is_ctrl_held():
    """检测当前是否按住 Ctrl（VK_CONTROL=0x11）；检测失败返回 False"""
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000)
    except Exception:
        try:
            import System.Windows.Forms as swf
            return (swf.Control.ModifierKeys & swf.Keys.Control) == swf.Keys.Control
        except Exception:
            return False


def fill_round_rect(g, brush, x, y, w, h, r):
    """用 3 个矩形 + 4 个圆角椭圆拼出圆角矩形（不依赖路径 API，兼容性最好）"""
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    g.FillRectangle(brush, x + r, y, w - 2 * r, h)
    g.FillRectangle(brush, x, y + r, w, h - 2 * r)
    g.FillEllipse(brush, x, y, 2 * r, 2 * r)
    g.FillEllipse(brush, x + w - 2 * r, y, 2 * r, 2 * r)
    g.FillEllipse(brush, x, y + h - 2 * r, 2 * r, 2 * r)
    g.FillEllipse(brush, x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r)


def draw_text_centered(g, font, text, x, y, w, h, color, shadow=True):
    """在 (x,y,w,h) 内居中绘制文字，带 1px 投影"""
    ts = g.MeasureString(font, text)
    tx = x + (w - ts.Width) / 2.0
    ty = y + (h - ts.Height) / 2.0
    if shadow:
        g.DrawText(font, PALETTE["text_shadow"], tx + 1, ty + 1, text)
    g.DrawText(font, color, tx, ty, text)


class MarkingMenuWindow(forms.Form):
    def __init__(self):
        forms.Form.__init__(self)
        # 默认布局值；真正的配置在 setup() 里应用
        self.size = 460
        self.half = 230
        self.groups = DEFAULT_CONFIG["groups"]
        self.count = len(self.groups)
        self.span = 360.0 / self.count
        self.min_drag = 20
        self.ring_r = max(int(self.half * 0.39), 72)   # 一级（工具集）环半径
        self.group_w = GROUP_W

        # 两级状态
        self.phase = 1            # 1=选工具集，2=选工具
        self.level2_group = -1    # 当前进入二级的工具集
        self.entered_this_gesture = False   # 本次手势是否刚从一级拖进二级
        self.ctrl_mode = False      # 按住 Ctrl 呼出模式（悬停选中，松手执行）
        self._ctrl_timer = None     # Ctrl 松开检测定时器

        self._closed = False
        self.WindowStyle = forms.WindowStyle.None
        self.Size = drawing.Size(self.size, self.size)
        self.BackgroundColor = drawing.Colors.Transparent
        self.Topmost = True

        self.drag_start = None
        self.current_mouse = drawing.PointF(self.half, self.half)
        self.highlight_group = -1
        self.highlight_tool = -1
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

    def setup(self, config):
        """应用配置（构造后、显示前调用）"""
        self.config = config
        self.size = int(config["menu_size"])
        self.half = self.size // 2
        self.groups = config["groups"]
        self.count = len(self.groups)
        self.span = 360.0 / self.count
        self.min_drag = int(config["min_drag"])
        self.ring_r = max(int(self.half * 0.39), 72)
        self.group_w = GROUP_W
        if self.count > 1:
            arc = self.ring_r * (2.0 * math.pi / self.count)
            self.group_w = min(GROUP_W, max(58.0, arc - 6.0))
        self.Size = drawing.Size(self.size, self.size)
        self.current_mouse = drawing.PointF(self.half, self.half)
        self.phase = 1
        self.level2_group = -1
        self.highlight_group = -1
        self.highlight_tool = -1

    # ---------------- 几何（一级：工具集环） ----------------
    def _group_angle(self, i):
        """第 i 个工具集的方向角（数学角：0 度=右，逆时针）"""
        return math.radians(i * self.span + self.span / 2.0)

    def _group_center(self, i):
        a = self._group_angle(i)
        return (self.half + self.ring_r * math.cos(a),
                self.half - self.ring_r * math.sin(a))

    def _group_rect(self, i):
        bx, by = self._group_center(i)
        return (bx - self.group_w / 2.0, by - GROUP_H / 2.0, self.group_w, GROUP_H)

    def _hit_group(self, x, y):
        for i in range(self.count):
            rx, ry, rw, rh = self._group_rect(i)
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return i
        return -1

    def _group_of(self, x, y):
        """按角度判断指向的工具集（拖拽容错用）"""
        dx = x - self.half
        dy = self.half - y
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360.0
        return int(angle // self.span) % self.count

    def _tool_radius(self, x, y):
        return math.hypot(x - self.half, y - self.half)

    # ---------------- 几何（二级：工具圆形标签环） ----------------
    def _ring_center(self, gi):
        """二级工具环的圆心 = 选中的工具集方框中心"""
        return self._group_center(gi)

    def _ring_radius(self, gi):
        """工具环半径：按工具数量自适应，保证相邻不重叠"""
        n = len(self.groups[gi]["tools"])
        if n <= 1:
            return RING_R_MIN
        chord = 2.0 * math.sin(math.pi / n)   # 单位半径下相邻工具的弦长
        r = TOOL_W / chord + 16.0
        return max(RING_R_MIN, min(r, RING_R_MAX))

    def _ring_tool_angle(self, gi, ti):
        """第 ti 个工具在环上的角度（从正上方开始，顺时针）"""
        n = len(self.groups[gi]["tools"])
        return math.radians(-90.0 + 360.0 * ti / n)

    def _ring_tool_center(self, gi, ti):
        rcx, rcy = self._ring_center(gi)
        a = self._ring_tool_angle(gi, ti)
        R = self._ring_radius(gi)
        return (rcx + R * math.cos(a), rcy + R * math.sin(a))

    def _ring_tool_rect(self, gi, ti):
        bx, by = self._ring_tool_center(gi, ti)
        return (bx - TOOL_W / 2.0, by - TOOL_H / 2.0, TOOL_W, TOOL_H)

    def _hit_ring_tool(self, gi, x, y):
        if gi < 0 or gi >= self.count:
            return -1
        for ti in range(len(self.groups[gi]["tools"])):
            rx, ry, rw, rh = self._ring_tool_rect(gi, ti)
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return ti
        return -1

    def _nearest_ring_tool(self, gi, x, y):
        """按角度找离鼠标最近的环上工具（拖拽松手容错）"""
        rcx, rcy = self._ring_center(gi)
        dx, dy = x - rcx, rcy - y
        ang = math.degrees(math.atan2(dy, dx))
        if ang < 0:
            ang += 360.0
        best, best_d = 0, 1e9
        for ti in range(len(self.groups[gi]["tools"])):
            ta = (-math.degrees(self._ring_tool_angle(gi, ti))) % 360.0
            d = abs((ta - ang + 180.0) % 360.0 - 180.0)
            if d < best_d:
                best_d, best = d, ti
        return best

    def _ring_dist(self, x, y):
        gi = self.level2_group
        if gi < 0:
            return math.hypot(x - self.half, y - self.half)
        rcx, rcy = self._ring_center(gi)
        return math.hypot(x - rcx, y - rcy)

    # ---------------- 状态切换 ----------------
    def enter_level2(self, gi):
        """选中工具集 -> 进入二级：以该工具集为圆心生成工具环"""
        self.phase = 2
        self.level2_group = gi
        self.highlight_group = gi
        self.highlight_tool = -1

    def back_to_level1(self):
        self.phase = 1
        self.level2_group = -1
        self.highlight_group = -1
        self.highlight_tool = -1

    # ---------------- 选中判断 / 高亮 ----------------
    def update_highlight(self, x, y, dragging):
        if self.ctrl_mode:
            self._update_highlight_ctrl(x, y)
            return
        if self.phase == 1:
            gi = self._hit_group(x, y)
            if gi >= 0:
                self.highlight_group, self.highlight_tool = gi, -1
                self.current_tooltip = self.groups[gi].get("tooltip") or self.groups[gi].get("name") or ""
            elif dragging and self._tool_radius(x, y) >= self.ring_r - 12:
                gi = self._group_of(x, y)
                self.highlight_group, self.highlight_tool = gi, -1
                self.current_tooltip = self.groups[gi].get("tooltip") or self.groups[gi].get("name") or ""
            else:
                self.highlight_group, self.highlight_tool = -1, -1
                self.current_tooltip = ""
        else:
            gi = self.level2_group
            if gi < 0:
                return
            ti = self._hit_ring_tool(gi, x, y)
            if ti >= 0:
                self.highlight_group, self.highlight_tool = gi, ti
                t = self.groups[gi]["tools"][ti]
                self.current_tooltip = t.get("tooltip") or t.get("command") or t.get("name") or ""
            else:
                g2 = self._hit_group(x, y)
                if g2 >= 0:
                    if g2 != gi:
                        # 其它一级工具集（已变暗）：悬停提示可切换
                        self.highlight_group, self.highlight_tool = g2, -1
                        self.current_tooltip = (self.groups[g2].get("name") or "") + "（点击切换）"
                    else:
                        # 中心 hub = 当前选中的工具集
                        self.highlight_group, self.highlight_tool = gi, -1
                        self.current_tooltip = (self.groups[gi].get("name") or "") + "（点中心/空白返回上一级）"
                elif dragging and self._ring_dist(x, y) >= self._ring_radius(gi) - 16:
                    ti = self._nearest_ring_tool(gi, x, y)
                    self.highlight_group, self.highlight_tool = gi, ti
                    t = self.groups[gi]["tools"][ti]
                    self.current_tooltip = t.get("tooltip") or t.get("command") or t.get("name") or ""
                else:
                    self.highlight_group, self.highlight_tool = -1, -1
                    self.current_tooltip = ""
    def _update_highlight_ctrl(self, x, y):
        """按住 Ctrl 模式：悬停即选中/展开，松手提交"""
        if self.phase == 1:
            gi = self._hit_group(x, y)
            if gi >= 0:
                self.enter_level2(gi)
            elif self._tool_radius(x, y) >= self.ring_r - 12:
                gi = self._group_of(x, y)
                self.enter_level2(gi)
            else:
                self.highlight_group, self.highlight_tool = -1, -1
                self.current_tooltip = ""
            return
        gi = self.level2_group
        if gi < 0:
            return
        ti = self._hit_ring_tool(gi, x, y)
        if ti >= 0:
            self.highlight_group, self.highlight_tool = gi, ti
            t = self.groups[gi]["tools"][ti]
            self.current_tooltip = t.get("tooltip") or t.get("command") or t.get("name") or ""
            return
        rx, ry, rw, rh = self._group_rect(gi)
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            self.highlight_group, self.highlight_tool = gi, -1
            self.current_tooltip = (self.groups[gi].get("name") or "") + "（松手=默认工具）"
            return
        g2 = self._hit_group(x, y)
        if g2 >= 0 and g2 != gi:
            self.enter_level2(g2)
            self.highlight_group, self.highlight_tool = g2, -1
            self.current_tooltip = (self.groups[g2].get("name") or "") + "（松手=默认工具）"
            return
        if self._tool_radius(x, y) <= HUB_R + 14:
            self.back_to_level1()
            self.current_tooltip = ""
            return
        if self._ring_dist(x, y) >= self._ring_radius(gi) - 20:
            ti = self._nearest_ring_tool(gi, x, y)
            self.highlight_group, self.highlight_tool = gi, ti
            t = self.groups[gi]["tools"][ti]
            self.current_tooltip = t.get("tooltip") or t.get("command") or t.get("name") or ""
            return
        self.highlight_group, self.highlight_tool = -1, -1
        self.current_tooltip = ""

    # ---------------- 绘制 ----------------
    def _paint_soft_glow(self, g, cx, cy, max_r):
        for rr, aa in ((max_r, 5), (max_r * 0.85, 6), (max_r * 0.7, 8),
                       (max_r * 0.55, 10), (max_r * 0.4, 12), (max_r * 0.25, 14)):
            g.FillEllipse(drawing.SolidBrush(
                drawing.Color.FromArgb(255, 255, 255, aa)),
                cx - rr, cy - rr, rr * 2, rr * 2)

    def _paint_highlight_halo(self, g, col, x, y, w, h, infl_max=11):
        """高亮方框的彩色光晕"""
        r, gg, b = color_parts(col)
        for infl, aa in ((3, 70), (7, 30), (infl_max, 12)):
            fill_round_rect(g, drawing.SolidBrush(
                drawing.Color.FromArgb(r, gg, b, aa)),
                x - infl, y - infl, w + infl * 2, h + infl * 2,
                BOX_RADIUS + infl)

    def _paint_hub(self, g, cx, cy, P):
        """一级中心圆点（渐变 + 发光 + 拖拽进度环）"""
        for rr, aa in ((HUB_R + 16, 10), (HUB_R + 10, 16), (HUB_R + 5, 26)):
            g.FillEllipse(drawing.SolidBrush(
                drawing.Color.FromArgb(140, 175, 255, aa)),
                cx - rr, cy - rr, rr * 2, rr * 2)
        try:
            grad = drawing.LinearGradientBrush(
                P["hub_top"], P["hub_bottom"],
                drawing.PointF(cx, cy - HUB_R), drawing.PointF(cx, cy + HUB_R))
            g.FillEllipse(grad, cx - HUB_R, cy - HUB_R, HUB_R * 2, HUB_R * 2)
        except Exception:
            g.FillEllipse(drawing.SolidBrush(P["hub_top"]),
                          cx - HUB_R, cy - HUB_R, HUB_R * 2, HUB_R * 2)
        g.DrawEllipse(drawing.Pen(P["hub_border"], 1.5),
                      cx - HUB_R, cy - HUB_R, HUB_R * 2, HUB_R * 2)

    def _paint_progress_ring(self, g, cx, cy, max_r):
        """拖拽进度环（沿中心外圈，随拖拽距离增长）"""
        if self.drag_start is None:
            return
        dx = self.current_mouse.X - cx
        dy = cy - self.current_mouse.Y
        dist = math.hypot(dx, dy)
        frac = min(1.0, dist / max(float(max_r), 1.0))
        if frac > 0.03:
            try:
                arc_r = HUB_R + 4
                g.DrawArc(drawing.Pen(drawing.Color.FromArgb(255, 255, 255, 235), 2),
                          drawing.RectangleF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2),
                          90, -360.0 * frac)
            except Exception:
                pass

    def _paint_tooltip(self, g, cx, cy):
        if not self.current_tooltip:
            return
        tip_font = make_font(FONT_LABEL, FONT_TIP_SIZE)
        ts = g.MeasureString(tip_font, self.current_tooltip)
        tw, th = ts.Width + 16, ts.Height + 8
        tip_x = min(self.current_mouse.X + 14, self.size - tw - 6)
        tip_y = min(self.current_mouse.Y + 14, self.size - th - 4)
        tip_x = max(tip_x, 4)
        tip_y = max(tip_y, 4)
        fill_round_rect(g, drawing.SolidBrush(drawing.Color.FromArgb(0, 0, 0, 120)),
                        tip_x, tip_y + 2, tw, th, 10)
        fill_round_rect(g, drawing.SolidBrush(PALETTE["tip_border"]),
                        tip_x - 1, tip_y - 1, tw + 2, th + 2, 11)
        fill_round_rect(g, drawing.SolidBrush(PALETTE["tip_bg"]),
                        tip_x, tip_y, tw, th, 10)
        g.DrawText(tip_font, drawing.Colors.White,
                   tip_x + 8, tip_y + 4, self.current_tooltip)

    def _paint_hint(self, g, text):
        hf = make_font(FONT_LABEL, 11)
        hs = g.MeasureString(hf, text)
        g.DrawText(hf, drawing.Color.FromArgb(150, 158, 172, 150),
                   self.half - hs.Width / 2.0, self.size - 28, text)

    def _paint_level1(self, g, cx, cy, P):
        self._paint_soft_glow(g, cx, cy, float(self.half))
        # 轨道圆
        g.DrawEllipse(drawing.Pen(drawing.Color.FromArgb(205, 212, 226, 72), 1),
                      cx - self.ring_r, cy - self.ring_r,
                      self.ring_r * 2, self.ring_r * 2)
        # 工具集连线
        for i in range(self.count):
            bx, by = self._group_center(i)
            if i == self.highlight_group:
                col = parse_color(self.groups[i].get("color"))
                r, gg, b = color_parts(col)
                g.DrawLine(drawing.Pen(drawing.Color.FromArgb(r, gg, b, 90), 6),
                           cx, cy, bx, by)
                g.DrawLine(drawing.Pen(drawing.Color.FromArgb(r, gg, b, 255), 2.5),
                           cx, cy, bx, by)
            else:
                g.DrawLine(drawing.Pen(P["line"], 1.5), cx, cy, bx, by)
        # 工具集方框
        for i, grp in enumerate(self.groups):
            rx, ry, rw, rh = self._group_rect(i)
            hl = (i == self.highlight_group)
            font = make_font(FONT_LABEL, FONT_LABEL_SIZE)
            if hl:
                col = parse_color(grp.get("color"))
                self._paint_highlight_halo(g, col, rx, ry, rw, rh)
                fill_round_rect(g, drawing.SolidBrush(
                    drawing.Color.FromArgb(250, 251, 253, 235)),
                    rx - 1, ry - 1, rw + 2, rh + 2, BOX_RADIUS + 1)
                fill_round_rect(g, drawing.SolidBrush(col), rx, ry, rw, rh, BOX_RADIUS)
                g.FillRectangle(drawing.SolidBrush(P["glass"]),
                                rx + 5, ry + 2, rw - 10, 2)
                draw_text_centered(g, font, grp.get("name") or "?", rx, ry, rw, rh,
                                   drawing.Colors.White)
            else:
                fill_round_rect(g, drawing.SolidBrush(P["idle_border_dim"]),
                                rx - 1, ry - 1, rw + 2, rh + 2, BOX_RADIUS + 1)
                fill_round_rect(g, drawing.SolidBrush(P["idle_fill_dim"]),
                                rx, ry, rw, rh, BOX_RADIUS)
                g.FillRectangle(drawing.SolidBrush(P["glass_dim"]),
                                rx + 5, ry + 2, rw - 10, 2)
                draw_text_centered(g, font, grp.get("name") or "?", rx, ry, rw, rh,
                                   P["text"])
        # 中心圆点 + 进度环
        self._paint_hub(g, cx, cy, P)
        self._paint_progress_ring(g, cx, cy, float(self.ring_r))
        if self.ctrl_mode:
            self._paint_hint(g, "按住 Ctrl 移向工具集 · 松手执行 · ESC 关闭")
        else:
            self._paint_hint(g, "点/拖 工具集 → 展开工具 · ESC 关闭")

    def _paint_level2(self, g, cx, cy, P):
        gi = self.level2_group
        if gi < 0:
            return
        rcx, rcy = self._ring_center(gi)
        R = self._ring_radius(gi)
        n = len(self.groups[gi]["tools"])
        col = parse_color(self.groups[gi].get("color"))
        r, gg, b = color_parts(col)
        # 局部柔光（以二级圆心为中心）
        self._paint_soft_glow(g, rcx, rcy, max(R + 46, self.half * 0.55))
        # 一级背景：未选中的工具集透明度降到 ~10%，保留空间感；悬停/点击可切换
        g.DrawEllipse(drawing.Pen(drawing.Color.FromArgb(205, 212, 226, 20), 1),
                      cx - self.ring_r, cy - self.ring_r,
                      self.ring_r * 2, self.ring_r * 2)
        for i in range(self.count):
            if i == gi:
                continue
            bx, by = self._group_center(i)
            g.DrawLine(drawing.Pen(drawing.Color.FromArgb(150, 156, 168, 16), 1.0),
                       cx, cy, bx, by)
            rx, ry, rw, rh = self._group_rect(i)
            dim_hl = (i == self.highlight_group)
            if dim_hl:
                col2 = parse_color(self.groups[i].get("color"))
                self._paint_highlight_halo(g, col2, rx, ry, rw, rh)
                fill_round_rect(g, drawing.SolidBrush(
                    drawing.Color.FromArgb(250, 251, 253, 90)),
                    rx - 1, ry - 1, rw + 2, rh + 2, BOX_RADIUS + 1)
                fill_round_rect(g, drawing.SolidBrush(col2), rx, ry, rw, rh, BOX_RADIUS)
                draw_text_centered(g, make_font(FONT_LABEL, FONT_LABEL_SIZE),
                                   self.groups[i].get("name") or "?", rx, ry, rw, rh,
                                   drawing.Colors.White)
            else:
                fill_round_rect(g, drawing.SolidBrush(
                    drawing.Color.FromArgb(150, 156, 168, 14)),
                    rx - 1, ry - 1, rw + 2, rh + 2, BOX_RADIUS + 1)
                fill_round_rect(g, drawing.SolidBrush(
                    drawing.Color.FromArgb(24, 27, 34, 22)),
                    rx, ry, rw, rh, BOX_RADIUS)
                g.FillRectangle(drawing.SolidBrush(
                    drawing.Color.FromArgb(255, 255, 255, 6)),
                    rx + 5, ry + 2, rw - 10, 2)
                draw_text_centered(g, make_font(FONT_LABEL, FONT_LABEL_SIZE),
                                   self.groups[i].get("name") or "?", rx, ry, rw, rh,
                                   drawing.Color.FromArgb(168, 176, 190, 40), shadow=False)
        # 一级中心圆点（淡）
        for rr, aa in ((HUB_R + 10, 4), (HUB_R + 5, 8)):
            g.FillEllipse(drawing.SolidBrush(
                drawing.Color.FromArgb(140, 175, 255, aa)),
                cx - rr, cy - rr, rr * 2, rr * 2)
        g.FillEllipse(drawing.SolidBrush(
            drawing.Color.FromArgb(63, 70, 86, 40)),
            cx - HUB_R, cy - HUB_R, HUB_R * 2, HUB_R * 2)
        # 引导圆环
        g.DrawEllipse(drawing.Pen(drawing.Color.FromArgb(205, 212, 226, 72), 1),
                      rcx - R, rcy - R, R * 2, R * 2)
        g.DrawEllipse(drawing.Pen(drawing.Color.FromArgb(r, gg, b, 60), 1),
                      rcx - R + 2, rcy - R + 2, (R - 2) * 2, (R - 2) * 2)
        # 连线：圆心 -> 每个工具
        for ti in range(n):
            bx, by = self._ring_tool_center(gi, ti)
            if ti == self.highlight_tool and self.highlight_group == gi:
                g.DrawLine(drawing.Pen(drawing.Color.FromArgb(r, gg, b, 90), 6),
                           rcx, rcy, bx, by)
                g.DrawLine(drawing.Pen(drawing.Color.FromArgb(r, gg, b, 255), 2.5),
                           rcx, rcy, bx, by)
            else:
                g.DrawLine(drawing.Pen(drawing.Color.FromArgb(r, gg, b, 70), 1.5),
                           rcx, rcy, bx, by)
        # 工具方框（环）
        font = make_font(FONT_LABEL, FONT_LABEL_SIZE - 1)
        for ti, t in enumerate(self.groups[gi]["tools"]):
            rx, ry, rw, rh = self._ring_tool_rect(gi, ti)
            hl = (ti == self.highlight_tool and self.highlight_group == gi)
            if hl:
                self._paint_highlight_halo(g, col, rx, ry, rw, rh)
                fill_round_rect(g, drawing.SolidBrush(
                    drawing.Color.FromArgb(250, 251, 253, 235)),
                    rx - 1, ry - 1, rw + 2, rh + 2, BOX_RADIUS + 1)
                fill_round_rect(g, drawing.SolidBrush(col), rx, ry, rw, rh, BOX_RADIUS)
                draw_text_centered(g, font, t.get("name") or "?", rx, ry, rw, rh,
                                   drawing.Colors.White)
            else:
                fill_round_rect(g, drawing.SolidBrush(P["idle_border"]),
                                rx - 1, ry - 1, rw + 2, rh + 2, BOX_RADIUS + 1)
                fill_round_rect(g, drawing.SolidBrush(P["idle_fill"]),
                                rx, ry, rw, rh, BOX_RADIUS)
                g.FillRectangle(drawing.SolidBrush(P["glass_dim"]),
                                rx + 5, ry + 2, rw - 10, 2)
                draw_text_centered(g, font, t.get("name") or "?", rx, ry, rw, rh,
                                   P["text"])
        # 中心 hub：选中的工具集方框（点击=返回上一级）
        rx, ry, rw, rh = self._group_rect(gi)
        hl = (self.highlight_group == gi and self.highlight_tool < 0)
        if hl:
            self._paint_highlight_halo(g, col, rx, ry, rw, rh)
        fill_round_rect(g, drawing.SolidBrush(
            drawing.Color.FromArgb(250, 251, 253, 225)),
            rx - 1, ry - 1, rw + 2, rh + 2, BOX_RADIUS + 1)
        fill_round_rect(g, drawing.SolidBrush(col), rx, ry, rw, rh, BOX_RADIUS)
        g.FillRectangle(drawing.SolidBrush(P["glass"]),
                        rx + 5, ry + 2, rw - 10, 2)
        draw_text_centered(g, make_font(FONT_LABEL, FONT_LABEL_SIZE),
                           self.groups[gi].get("name") or "?", rx, ry, rw, rh,
                           drawing.Colors.White)
        # 拖拽进度环（围绕 hub）
        if self.drag_start is not None:
            dx = self.current_mouse.X - rcx
            dy = rcy - self.current_mouse.Y
            dist = math.hypot(dx, dy)
            frac = min(1.0, dist / max(R, 1.0))
            if frac > 0.03:
                try:
                    arc_r = max(rw, rh) / 2.0 + 6
                    g.DrawArc(drawing.Pen(drawing.Color.FromArgb(255, 255, 255, 235), 2),
                              drawing.RectangleF(rcx - arc_r, rcy - arc_r, arc_r * 2, arc_r * 2),
                              90, -360.0 * frac)
                except Exception:
                    pass
        if self.ctrl_mode:
            self._paint_hint(g, "松手执行高亮工具 · 移向中心返回 · ESC 关闭")
        else:
            self._paint_hint(g, "点工具执行 · 点其它工具集切换 · 点空白/中心返回 · ESC 关闭")

    def on_paint(self, sender, e):
        g = e.Graphics
        cx, cy = self.half, self.half
        P = PALETTE
        if self.phase == 1:
            self._paint_level1(g, cx, cy, P)
        else:
            self._paint_level2(g, cx, cy, P)
        self._paint_tooltip(g, cx, cy)

    # ---------------- 事件处理 ----------------
    def close_once(self):
        if self._closed:
            return
        self._closed = True
        self.stop_ctrl_watch()
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
        if self.ctrl_mode:
            self.current_mouse = e.Location
            return
        if e.Buttons == forms.MouseButtons.Primary:
            self.drag_start = e.Location
            self.current_mouse = e.Location
            self.entered_this_gesture = False
            if self.phase == 1:
                gi = self._hit_group(e.Location.X, e.Location.Y)
                if gi >= 0:
                    self.enter_level2(gi)
                    self.entered_this_gesture = True
            self.update_highlight(e.Location.X, e.Location.Y, True)
            self.canvas.Invalidate()

    def on_mouse_move(self, sender, e):
        self.current_mouse = e.Location
        dragging = self.drag_start is not None
        if self.phase == 1 and dragging:
            gi = self._hit_group(e.Location.X, e.Location.Y)
            if gi >= 0:
                self.enter_level2(gi)
                self.entered_this_gesture = True
        self.update_highlight(e.Location.X, e.Location.Y, dragging)
        self.canvas.Invalidate()

    def on_mouse_up(self, sender, e):
        if self.ctrl_mode:
            self.drag_start = None
            return
        if self.drag_start is None:
            return

        x, y = e.Location.X, e.Location.Y
        dx = x - self.drag_start.X
        dy = self.drag_start.Y - y
        distance = math.hypot(dx, dy)
        self.drag_start = None

        # ---- 一级：松手 -> 选中工具集（进入二级），空点 -> 取消 ----
        if self.phase == 1:
            gi = self._hit_group(x, y)
            if gi >= 0:
                self.enter_level2(gi)
                self.canvas.Invalidate()
                return
            if distance >= self.min_drag and self._tool_radius(x, y) >= self.ring_r - 12:
                gi = self._group_of(x, y)
                self.enter_level2(gi)
                self.canvas.Invalidate()
                return
            self.close_once()
            print("[标记菜单] 未选中任何功能，取消")
            return

        # ---- 二级：松手 -> 执行工具 / 返回一级 ----
        gi = self.level2_group
        if gi < 0:
            self.close_once()
            return

        # 1) 点在工具上 -> 执行
        ti = self._hit_ring_tool(gi, x, y)
        if ti >= 0:
            self.close_once()
            self._execute(self.groups[gi]["tools"][ti])
            return

        # 2) 点在某一级工具集上：其它工具集 -> 直接切换；自己(hub) -> 返回一级
        g2 = self._hit_group(x, y)
        if g2 >= 0:
            if g2 != gi:
                self.enter_level2(g2)
                self.canvas.Invalidate()
                return
            if self.entered_this_gesture:
                self.entered_this_gesture = False
                self.canvas.Invalidate()
                return
            self.back_to_level1()
            self.canvas.Invalidate()
            return

        # 3) 拖得够远（连续拖拽直奔工具）-> 按角度选最近工具执行
        if distance >= self.min_drag and self._ring_dist(x, y) >= self._ring_radius(gi) - 16:
            ti = self._nearest_ring_tool(gi, x, y)
            self.close_once()
            self._execute(self.groups[gi]["tools"][ti])
            return

        # 4) 本次手势刚拖进来但没点到工具 -> 停在二级，方便下一步点选
        if self.entered_this_gesture:
            self.entered_this_gesture = False
            self.canvas.Invalidate()
            return

        # 5) 点空白 -> 返回一级
        self.back_to_level1()
        self.canvas.Invalidate()

    # ---------------- 按住 Ctrl 模式：轮询与提交 ----------------
    def start_ctrl_watch(self):
        """启动 Ctrl 松开检测（每 30ms 轮询）"""
        try:
            import System.Threading
            self._ctrl_timer = System.Threading.Timer(
                self._on_ctrl_tick, None, 100, 30)
        except Exception:
            self._ctrl_timer = None

    def stop_ctrl_watch(self):
        if getattr(self, "_ctrl_timer", None) is not None:
            try:
                self._ctrl_timer.Dispose()
            except Exception:
                pass
            self._ctrl_timer = None

    def _on_ctrl_tick(self, state):
        if self._closed:
            return
        if not _is_ctrl_held():
            try:
                forms.Application.Instance.Invoke(self.commit_ctrl_release)
            except Exception:
                try:
                    self.close_once()
                except Exception:
                    pass

    def commit_ctrl_release(self):
        """松手 Ctrl：高亮工具 -> 执行；停在工具集上 -> 默认工具；否则取消"""
        if self._closed:
            return
        gi = self.level2_group
        if self.phase == 2 and gi >= 0:
            ti = self.highlight_tool
            if ti >= 0 and self.highlight_group == gi:
                self.close_once()
                self._execute(self.groups[gi]["tools"][ti])
                return
            x, y = self.current_mouse.X, self.current_mouse.Y
            rx, ry, rw, rh = self._group_rect(gi)
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                self.close_once()
                self._execute_group(gi)
                return
        self.close_once()
        print("[标记菜单] 取消")

    def _group_default_command(self, gi):
        g = self.groups[gi]
        cmd = g.get("default_command") or ""
        if not cmd and g.get("tools"):
            cmd = g["tools"][0].get("command") or ""
        return cmd

    def _execute_group(self, gi):
        """执行工具集的默认命令"""
        g = self.groups[gi]
        cmd = self._group_default_command(gi)
        if not cmd:
            print("[标记菜单] 该工具集未配置命令：%s" % g.get("name"))
            return
        print("[标记菜单] 执行（默认）：%s" % cmd)
        try:
            rs.Command("!_" + cmd, echo=False)
        except Exception as ex:
            print("[标记菜单] 执行命令出错：%s (%s)" % (cmd, ex))

    def _execute(self, tool):
        """执行某个具体工具"""
        command = tool.get("command") or ""
        if not command:
            print("[标记菜单] 该工具未配置命令：%s" % tool.get("name"))
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

    # 鼠标位置：用 Eto 的逻辑坐标（与窗口 Location 同一坐标系，自动适配高分屏 DPI）
    try:
        p = forms.Mouse.Position
        mouse_x, mouse_y = p.X, p.Y
    except Exception:
        try:
            import System.Windows.Forms as swf
            pos = swf.Cursor.Position
            mouse_x, mouse_y = pos.X, pos.Y
        except Exception:
            mouse_x, mouse_y = 400, 400

    # 找鼠标所在屏幕：限制菜单尺寸不超出屏幕，并做边界夹紧
    x = int(mouse_x) - size // 2
    y = int(mouse_y) - size // 2
    try:
        for scr in forms.Screen.Screens:
            if scr.DisplayBounds.Contains(drawing.PointF(mouse_x, mouse_y)):
                b = scr.DisplayBounds
                max_size = int(min(b.Width, b.Height) - 60)
                if size > max_size:
                    size = max_size
                half = size // 2
                x = int(mouse_x) - half
                y = int(mouse_y) - half
                x = max(int(b.Left), min(x, int(b.Right) - size))
                y = max(int(b.Top), min(y, int(b.Bottom) - size))
                break
    except Exception:
        pass

    config["menu_size"] = size   # 若被屏幕限制过，同步给窗口

    menu = MarkingMenuWindow()
    menu.setup(config)
    menu.Location = drawing.Point(int(x), int(y))
    menu.Owner = Rhino.UI.RhinoEtoApp.MainWindow

    # 按住 Ctrl 呼出 -> 开启"松手提交"模式；否则普通点击模式
    menu.ctrl_mode = _is_ctrl_held()
    if menu.ctrl_mode:
        menu.start_ctrl_watch()
        mx, my = mouse_x - x, mouse_y - y
        menu.current_mouse = drawing.PointF(float(mx), float(my))
        menu.update_highlight(float(mx), float(my), False)

    sc.sticky["MyMarkingMenu"] = menu
    menu.Show()


if __name__ == "__main__":
    run_menu()
