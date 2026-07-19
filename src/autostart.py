"""开机自启管理

使用 Windows 注册表 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 实现：
- 只写当前用户配置，不需要管理员权限
- Windows 原生登录时自动加载，无第三方依赖
- 任务管理器"启动"标签页可见，用户可手动关闭
- 注册表实际状态 = 唯一真理；config.autostart 只是"用户上次偏好"

打包后 (frozen)：注册 exe 绝对路径
开发时 (unfrozen)：注册 pythonw.exe + 脚本路径（用 pythonw 静默启动，无控制台窗口）
"""
import sys
import os
from pathlib import Path

if sys.platform == 'win32':
    import winreg
else:
    winreg = None

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "TimestampTool"


def is_supported() -> bool:
    """当前平台是否支持开机自启"""
    return sys.platform == 'win32'


def _build_command() -> str:
    """构造开机自启命令行

    打包后：`"<exe路径>"`
    开发时：`"<pythonw路径>" "<main.py绝对路径>"`（用 pythonw 避免控制台窗口）
    """
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    # 开发环境：优先使用 pythonw.exe（无控制台）
    py_exe = sys.executable
    pyw_exe = py_exe.replace('python.exe', 'pythonw.exe')
    if pyw_exe != py_exe and Path(pyw_exe).exists():
        py_exe = pyw_exe
    script = Path(__file__).resolve().parent / 'main.py'
    return f'"{py_exe}" "{script}"'


def get_registered_command() -> str:
    """读取当前注册的启动命令（用于检测 exe 路径是否已过期）"""
    if winreg is None:
        return ""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return str(value)
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def is_enabled() -> bool:
    """检查开机自启是否已启用（以注册表实际状态为准）"""
    return bool(get_registered_command())


def enable() -> bool:
    """启用开机自启（写入注册表 Run 键）"""
    if winreg is None:
        return False
    try:
        cmd = _build_command()
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        return True
    except OSError as e:
        print(f"[开机自启] 启用失败: {e}")
        return False


def disable() -> bool:
    """禁用开机自启（从注册表删除 Run 键值）"""
    if winreg is None:
        return True
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_WRITE
        ) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass  # 已经不存在，视为成功
        return True
    except OSError as e:
        print(f"[开机自启] 禁用失败: {e}")
        return False


def sync(desired_enabled: bool) -> bool:
    """将实际状态同步到期望状态

    - desired_enabled=True 且当前未启用 → enable()
    - desired_enabled=False 且当前已启用 → disable()
    - 状态一致 → 无操作
    - 已启用但 exe 路径变了 → 自动更新到当前路径
    """
    current = is_enabled()
    if desired_enabled and current:
        # 已启用，检查命令是否需要更新（用户移动了 exe 位置）
        expected = _build_command()
        if get_registered_command() != expected:
            return enable()  # 覆盖为新路径
        return True
    if desired_enabled == current:
        return True
    return enable() if desired_enabled else disable()
