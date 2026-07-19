"""TimestampTool 版本号中央管理

所有其它模块（main.py、settings.py、build.py 等）都应从这里读取版本号，
避免多处硬编码不一致。发布新版本时只需修改此文件即可。

SemVer 语义化版本号（MAJOR.MINOR.PATCH）：
- MAJOR: 破坏性变更（例如配置文件格式不兼容）
- MINOR: 新功能（例如添加开机自启）
- PATCH: bug 修复（例如浮窗第 5 个模板显示不全）
"""

__version__ = "1.1.0"
__build_date__ = "2026-07-19"
__author__ = "Sampson"


def version_string() -> str:
    """完整版本字符串，用于"关于"对话框显示

    格式：v1.0.0 (2026-07-19)
    """
    return f"v{__version__} ({__build_date__})"


def version_short() -> str:
    """短版本号，用于打包命名等

    格式：v1.0.0
    """
    return f"v{__version__}"
