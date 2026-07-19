"""路径工具：兼容 PyInstaller --onefile 打包与开发环境

策略：
- 只读资源（icon.ico、默认 config.json 模板等）：
    * 打包后位于 sys._MEIPASS 临时解压目录
    * 开发时位于项目根目录
- 用户可写配置（config.json）：
    * 打包后位于 %APPDATA%\\TimestampTool\\config.json（Windows 隐藏目录）
      → 用户看不到、发 exe 给别人不带私人配置、符合桌面应用惯例
    * 开发时位于项目根目录 / config / config.json
"""
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包后的 exe 中"""
    return getattr(sys, 'frozen', False)


def resource_path(rel_path: str) -> Path:
    """定位只读资源文件

    Args:
        rel_path: 相对于项目根 / _MEIPASS 的相对路径，如 "assets/icon.ico"

    Returns:
        绝对 Path 对象（不保证一定存在）
    """
    if is_frozen():
        # PyInstaller 解压运行时目录
        base = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    else:
        # 开发环境：src/paths.py -> src -> project_root
        base = Path(__file__).resolve().parent.parent
    return base / rel_path


def user_config_dir() -> Path:
    """用户配置目录

    打包后：%APPDATA%\\TimestampTool\\
    开发环境：项目根目录 / config /
    """
    if is_frozen():
        appdata = os.environ.get('APPDATA')
        if appdata:
            return Path(appdata) / "TimestampTool"
        # AppData 不可用（极少见），退回 exe 同目录
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent / "config"


def user_config_path() -> Path:
    """用户配置文件路径（可读写，需要持久化）

    打包后：%APPDATA%\\TimestampTool\\config.json
        → 用户看不见的隐藏位置，发 exe 给别人时不会带过去
    开发环境：项目根目录 / config / config.json
    """
    return user_config_dir() / "config.json"


def legacy_config_paths() -> list:
    """列出可能存在的历史配置文件路径（供迁移清理用）

    历史版本把 config.json 放在 exe 同目录，导致用户看到"神秘文件"污染。
    从 v2.3 起改用 %APPDATA%\\TimestampTool\\，需要迁移并清理。
    """
    if not is_frozen():
        return []
    exe_dir = Path(sys.executable).resolve().parent
    return [
        exe_dir / "config.json",
        exe_dir / "config.json.bak",
    ]


def default_config_resource() -> Path:
    """打包内嵌的默认 config.json 路径（首次启动时作为模板）"""
    if is_frozen():
        return resource_path("config/config.json")
    return user_config_path()
