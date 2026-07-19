# TimestampTool

一个 Windows 后台常驻的**时间戳快捷输入工具**：按 `Ctrl+Shift+Z` 弹出模板菜单，一键把带时间戳的文本注入到任意应用的当前焦点位置（重命名文件、编辑器、聊天窗口都可以）。

## 特点

- **一键呼出**：全局快捷键 `Ctrl+Shift+Z`（可自定义）
- **模板化**：多个模板可选，支持 `{YYYY}{MM}{DD}{hh}{mm}{ss}` 时间占位符 + `##` 内容占位符
- **自动选中占位符**：粘贴后 `##` 处会被选中，直接输入替换
- **不打断编辑态**：在文件重命名等场景呼出菜单不会失焦
- **单文件分发**：`TimestampTool.exe` 一个文件，60 MB，双击即用
- **零外显文件**：配置存放在 `%APPDATA%\TimestampTool\`，用户看不到"神秘文件"
- **开机自启**：可选，通过注册表实现（无 UAC 提示）

## 快速上手

1. 从 [Releases](#) 下载最新版 `TimestampTool.exe` 到任意文件夹
2. 双击运行，托盘会出现蓝色 T 图标
3. 按 `Ctrl+Shift+Z` 呼出菜单，选中一个模板即可粘贴
4. 右键托盘 → 设置，管理模板 / 修改快捷键 / 开启自启

## 从源码构建

```bash
pip install -r requirements.txt
python build.py         # 打包为 dist/TimestampTool.exe
```

## 项目结构

```
时间戳/
├── src/                 # Python 源码
│   ├── main.py          # 应用入口
│   ├── config.py        # 配置管理（AppData）
│   ├── template_engine.py  # 时间戳模板引擎
│   ├── clipboard.py     # 剪贴板注入
│   ├── hotkey_manager.py   # 全局快捷键
│   ├── window_utils.py     # Win32 窗口工具
│   ├── autostart.py     # 开机自启
│   ├── paths.py         # 资源/配置路径
│   ├── tray.py          # 系统托盘
│   ├── __version__.py   # 版本号中央管理
│   └── ui/              # 界面模块
│       ├── styles.py
│       ├── popup_menu.py   # 浮窗菜单
│       └── settings.py     # 设置窗口
├── harmony/             # 鸿蒙 PC 版（ArkTS）
├── assets/              # 图标资源
├── config/              # 打包内嵌默认配置
├── releases/            # 各版本 exe 归档
├── scripts/             # 工具脚本（release.py 等）
├── docs/                # 开发文档（RELEASE.md 等）
├── build.py             # 打包脚本
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## 开发文档

- [变更日志](CHANGELOG.md)
- [发布流程](docs/RELEASE.md)

## 作者

Sampson
