"""TimestampTool 系统托盘模块

使用 pystray 创建系统托盘图标，提供右键菜单（设置、关于、退出），
在独立守护线程中运行，不阻塞主线程。
"""
import pystray
from PIL import Image
import threading

from paths import resource_path


class TrayManager:
    """系统托盘管理器
    
    在后台守护线程中运行系统托盘图标，
    通过回调接口让主程序响应菜单事件。
    """
    
    def __init__(self, on_settings=None, on_about=None, on_exit=None):
        """初始化托盘管理器
        
        Args:
            on_settings: 点击"设置"菜单项的回调函数
            on_about: 点击"关于"菜单项的回调函数
            on_exit: 点击"退出"菜单项的回调函数
        """
        self.on_settings = on_settings or (lambda: None)
        self.on_about = on_about or (lambda: None)
        self.on_exit = on_exit or (lambda: None)
        self.icon = None
        self._thread = None
    
    def start(self):
        """在后台守护线程中启动托盘图标"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        """创建并运行托盘图标（在后台线程中执行）"""
        # 加载图标文件（兼容 PyInstaller --onefile 打包）
        icon_path = resource_path("assets/icon.ico")
        try:
            image = Image.open(icon_path)
        except Exception:
            # 图标不存在时创建默认蓝色图标
            image = Image.new('RGB', (64, 64), color=(0, 120, 212))
        
        # 创建右键菜单
        menu = pystray.Menu(
            pystray.MenuItem("设置", self._on_settings),
            pystray.MenuItem("关于", self._on_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_exit),
        )
        
        # 创建托盘图标
        self.icon = pystray.Icon(
            name="TimestampTool",
            icon=image,
            title="TimestampTool - 时间戳快捷输入",
            menu=menu,
        )
        
        self.icon.run()
    
    def _on_settings(self, icon, item):
        """设置菜单项点击处理"""
        self.on_settings()
    
    def _on_about(self, icon, item):
        """关于菜单项点击处理"""
        self.on_about()
    
    def _on_exit(self, icon, item):
        """退出菜单项点击处理"""
        if self.icon:
            self.icon.stop()
        self.on_exit()
    
    def stop(self):
        """停止托盘图标"""
        if self.icon:
            self.icon.stop()
            self.icon = None
