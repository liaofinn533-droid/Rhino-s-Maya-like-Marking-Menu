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
  拖拽时，对应方向的扇区亮起蓝色半透明高亮，直观指示当前选择。

- **轨迹辅助线**  
  从按下点到鼠标位置绘制浅蓝色引导线，清晰展示拖拽方向。

- **自动关闭**  
  失去焦点（点击菜单外区域）或按下 `ESC` 键，菜单自动关闭。

- **误触保护**  
  拖拽距离小于 20 像素时自动取消，避免误操作。

- **彩色符号图标**  
  每个工具使用专属 Unicode 符号和颜色标识，无需外部图片资源。

- **纯 Python 单文件**  
  无外部依赖，兼容 Rhino 6 / 7 / 8。

---

## 📦 安装

### 方法一：别名（推荐）

1. 将 `MarkingMenu.py` 复制到 Rhino 脚本目录：
   ```
   %APPDATA%\McNeel\Rhinoceros\8.0\scripts\MarkingMenu.py
   ```
   > Rhino 7 将 `8.0` 改为 `7.0`，Rhino 6 改为 `6.0`。

2. 在 Rhino 中输入 `Options` → **别名** → **新建**：

   | 字段 | 值 |
   |------|-----|
   | 别名 | `DM` |
   | 指令宏 | `! _-RunPythonScript "MarkingMenu.py"` |

3. 之后在 Rhino 中按 `DM` + `Space` 即可唤出菜单。

### 方法二：工具栏按钮

1. Rhino → **工具** → **工具栏布局**
2. 选择一个工具栏，右键 → **新增按钮**
3. 填入：

   | 字段 | 值 |
   |------|-----|
   | 指令 | `! _-RunPythonScript "MarkingMenu.py"` |
   | 按钮文字 | `标记菜单` |
   | 提示 | `Maya 风格标记菜单` |

4. 可导入下方图标或使用默认位图，确定保存。

### 方法三：直接运行

在 Rhino 中执行 `RunPythonScript`，选择脚本文件即可单次使用。

---

## 🎮 使用方式

1. 通过别名、按钮或快捷键唤出菜单。
2. 在菜单窗口中**按住鼠标左键并拖拽**。
3. 将鼠标滑向目标工具方向，**松手**即弹出对应工具栏。
4. 按 `ESC` 或点击菜单外区域可随时取消。

---

## 🎨 自定义

### 修改工具符号与颜色

编辑脚本开头的 `SECTORS` 列表即可自由调整每个工具的 Unicode 符号和颜色：

```python
SECTORS = [
    ("Point",    330, "●", drawing.Color.FromArgb(255, 100, 200, 255)),
    ("Lines",    30,  "╱", drawing.Color.FromArgb(255, 180, 255, 100)),
    ("Curve",    90,  "∿", drawing.Color.FromArgb(255, 255, 180, 100)),
    ("Arc",      150, "⌒", drawing.Color.FromArgb(255, 255, 100, 180)),
    ("Rectangle",210, "▣", drawing.Color.FromArgb(255, 255, 255, 100)),
    ("Circle",   270, "○", drawing.Color.FromArgb(255, 100, 255, 180)),
]
```

每一项的格式：`(工具名称, 起始角度(数学角度, 右=0°逆时针), Unicode符号, 颜色)`

工具栏名与 `SECTORS` 中定义的工具名称**自动对应**，无需额外修改 `cmd_map`。

### 添加 / 减少扇区

1. 在 `SECTORS` 中添加或删除条目
2. 修改 `SPAN = 360 / 扇区数量` 使角度覆盖完整圆周
3. 确保对应名称的 Rhino 工具栏已存在

### 调整 UI 参数

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WINDOW_SIZE` | 800 | 菜单窗口尺寸（像素） |
| `outer_radius` | 200 | 圆环外半径 |
| `inner_radius` | 80 | 圆环内半径 |
| 误触阈值 | 20 | `math.hypot` 距离判断（`on_mouse_up` 内） |

---

## 📋 兼容性

| Rhino 版本 | 状态 | 备注 |
|------------|------|------|
| Rhino 8 | ✅ 已测试 | 当前主力版本 |
| Rhino 7 | ✅ | — |
| Rhino 6 | ✅ | — |
| Mac 版 | ⚠️ 未测试 | Eto API 可能存在差异 |

> **注意**：如果你在 VSCode 等编辑器中看到 Pylance 类型检查报错（如 `"." 后应为属性名称`），这是正常现象 —— Pylance 无法解析 IronPython 的 .NET 互操作层。脚本头部已添加 `# type: ignore` 抑制误报，不影响 Rhino 运行。

---

## 🔧 技术细节

- **图形框架**：Eto.Forms + Eto.Drawing（Rhino 内置 UI 框架）
- **Python 引擎**：IronPython（.NET 集成）
- **事件驱动**：Drawable 控件承接鼠标拖拽 + Paint 自定义绘制
- **单例管理**：通过 `scriptcontext.sticky` 存储窗口引用，防止多重打开
- **坐标系**：屏幕坐标（Y 向下）与数学坐标（Y 向上）在扇区判断时转换

---

## 🙏 致谢

灵感来源于 Autodesk Maya 的 Marking Menu 交互方式。

---

## 📄 许可证

MIT License © 2024
