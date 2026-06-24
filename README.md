# RhinoMarkingMenu

🐏 **Rhino 仿 Maya 标记菜单**  
按住左键拖拽，在圆形菜单中快速切换 Rhino 建模工具。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Rhino](https://img.shields.io/badge/Rhino-6%2F7%2F8-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

---

## ✨ 功能

- **方向拖拽选择**  
  向 6 个方向拖拽，分别打开 Point、Lines、Curve、Arc、Rectangle、Circle 工具栏。

- **扇区高亮反馈**  
  拖拽时，对应方向扇区亮起蓝色半透明高亮，指示当前选择。

- **轨迹辅助线**  
  从按下点到鼠标位置绘制浅蓝色引导线。

- **自动关闭**  
  失去焦点（点击其他区域）或按下 `ESC` 键，菜单自动关闭。

- **误触保护**  
  拖拽距离小于 20 像素时自动取消，避免误操作。

- **彩色符号图标**  
  每个工具使用专属 Unicode 符号和颜色标识，无需依赖外部图片。

- **纯 Python 单文件**  
  无外部依赖，兼容 Rhino 6 / 7 / 8。

---

## 🎮 使用方式

1. 在 Rhino 中运行脚本（`RunPythonScript` 或 `EditPythonScript`）。
2. 在模型视图里**按住鼠标左键并拖拽**。
3. 将鼠标滑向目标工具方向，**松手**即弹出对应工具栏。
4. 按 `ESC` 或点击菜单外区域可随时取消。

> 建议将脚本绑定到快捷键（如 `Alt + Space`），一键唤出菜单。

---

## 🎨 自定义

### 修改工具符号与颜色
编辑脚本开头的 `SECTORS` 列表，可自由调整每个工具的 Unicode 符号和颜色。
```
SECTORS = [
    ("Point",    330, "●", drawing.Color.FromArgb(255, 100, 200, 255)),
    ("Lines",    30,  "╱", drawing.Color.FromArgb(255, 180, 255, 100)),
    ("Curve",    90,  "∿", drawing.Color.FromArgb(255, 255, 180, 100)),
    ("Arc",      150, "⌒", drawing.Color.FromArgb(255, 255, 100, 180)),
    ("Rectangle",210, "▣", drawing.Color.FromArgb(255, 255, 255, 100)),
    ("Circle",   270, "○", drawing.Color.FromArgb(255, 100, 255, 180)),
]
```
### 更换弹出工具栏

修改 `on_mouse_up` 中的 `cmd_map`，使方向对应你自定义的 Rhino 工具栏名称。

```
cmd_map = {
    "Point":     "! _PopupToolbar \"Point\"",
    "Lines":     "! _PopupToolbar \"Lines\"",
    "Curve":     "! _PopupToolbar \"Curve\"",
    "Arc":       "! _PopupToolbar \"Arc\"",
    "Rectangle": "! _PopupToolbar \"Rectangle\"",
    "Circle":    "! _PopupToolbar \"Circle\"",
}
```
*** 
## 📋 兼容性

|Rhino 版本|状态|
|---|---|
|Rhino 6|✅|
|Rhino 7|✅|
|Rhino 8|✅|
|Mac 版|⚠️ 未测试|

---

## 🙏 致谢

灵感来源于 Autodesk Maya 的 Marking Menu 交互方式。

***
## 📄 许可证

MIT License © 2024

