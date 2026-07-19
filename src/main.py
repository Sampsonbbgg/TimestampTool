"""TimestampTool - 时间戳快捷输入工具 (Python版)"""
import sys
import os
from pathlib import Path

# 确保src目录在路径中
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import customtkinter as ctk
from config import ConfigManager
from template_engine import TemplateEngine
from hotkey_manager import HotkeyManager
from clipboard import ClipboardInjector
from tray import TrayManager
from ui.popup_menu import PopupMenu
from ui.settings import SettingsWindow, show_about_dialog
from window_utils import get_foreground_hwnd
from __version__ import version_short
import autostart


class TimestampToolApp:
    """时间戳快捷输入工具主应用"""

    VERSION = version_short()
    
    def __init__(self):
        # 初始化配置
        self.config = ConfigManager()
        
        # 创建隐藏的根窗口（tkinter事件循环载体）
        self.root = ctk.CTk()
        self.root.withdraw()  # 隐藏主窗口
        self.root.title("TimestampTool")
        
        # 设置DPI感知
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        # 初始化各模块
        self.hotkey_mgr = HotkeyManager()
        self.clipboard = ClipboardInjector()
        self.settings_window = None
        self.popup_menu = None
        # 热键触发瞬间的前台窗口 HWND（用于把粘贴精准送回原窗口）
        self._original_hwnd = 0
        
        # 注册全局快捷键
        self._register_hotkey()
        
        # 同步开机自启状态（应对用户移动 exe 或手动删除注册表项）
        try:
            autostart.sync(self.config.autostart)
        except Exception as e:
            print(f"[开机自启] 同步失败: {e}")
        
        # 启动系统托盘
        self.tray = TrayManager(
            on_settings=self._show_settings,
            on_about=self._show_about,
            on_exit=self._exit_app
        )
        self.tray.start()
    
    def _register_hotkey(self):
        """注册全局快捷键"""
        self.hotkey_mgr.register(
            self.config.hotkey,
            self._on_hotkey_triggered
        )
    
    def _on_hotkey_triggered(self):
        """快捷键触发回调（在 pynput 线程中调用）"""
        # 立即捕获前台窗口 HWND —— 弹窗一旦创建可能改变前台，
        # 必须在弹窗前记录，才能确保注入回原窗口
        self._original_hwnd = get_foreground_hwnd()
        # 调度到主线程执行 UI 操作
        self.root.after(0, self._show_popup_menu)
    
    def _show_popup_menu(self):
        """在主线程中显示弹出菜单"""
        # 重新加载配置（获取最新模板 + 列数偏好）
        self.config.reload()

        # 用 list copy 传给 popup_menu，避免引用共享导致数据回流
        templates_snapshot = list(self.config.templates)

        # 创建弹出菜单（传入原窗口 HWND 用于失焦判断 + 列数偏好）
        self.popup_menu = PopupMenu(
            master=self.root,
            templates=templates_snapshot,
            on_select_callback=self._on_template_selected,
            target_hwnd=self._original_hwnd,
            columns=self.config.menu_columns,
        )
    
    def _on_template_selected(self, template):
        """模板选择回调"""
        # 格式化模板
        formatted_text = TemplateEngine.format_template(template['format'])
        target_hwnd = self._original_hwnd
        
        # 短暂延迟后注入（确保菜单已关闭）
        self.root.after(
            50, lambda: self.clipboard.inject_text(formatted_text, target_hwnd)
        )
    
    def _show_settings(self):
        """显示设置窗口（从托盘线程调用，需调度到主线程）"""
        self.root.after(0, self._show_settings_ui)
    
    def _show_settings_ui(self):
        """在主线程中显示设置窗口"""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(
                self.config,
                on_save_callback=self._on_settings_saved
            )
        self.settings_window.show()
    
    def _on_settings_saved(self):
        """设置保存后的回调"""
        # 重新注册热键（可能已更改）
        self.hotkey_mgr.re_register(
            self.config.hotkey,
            self._on_hotkey_triggered
        )
    
    def _show_about(self):
        """显示关于对话框"""
        self.root.after(0, lambda: show_about_dialog(self.root))
    
    def _exit_app(self):
        """退出应用"""
        self.hotkey_mgr.unregister()
        self.root.after(0, self.root.quit)
    
    def run(self):
        """启动应用主循环"""
        # 进入tkinter事件循环
        self.root.mainloop()


def main():
    """程序入口"""
    # 设置CustomTkinter外观
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    # 创建并运行应用
    app = TimestampToolApp()
    app.run()


if __name__ == "__main__":
    main()
