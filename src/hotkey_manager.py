"""TimestampTool 全局热键管理模块

使用 pynput.keyboard.GlobalHotKeys 实现全局快捷键监听，
支持用户友好格式（如 "ctrl+shift+t"）的快捷键定义。
"""
from pynput import keyboard
import threading


class HotkeyManager:
    """全局热键管理器
    
    负责注册、注销和重新注册全局快捷键。
    监听器在后台守护线程中运行，不阻塞主线程。
    """
    
    def __init__(self):
        self.listener = None
        self._callback = None
        self._current_hotkey = ""
    
    def register(self, hotkey_str: str, callback):
        """注册全局快捷键
        
        Args:
            hotkey_str: 用户友好格式的快捷键，如 "ctrl+shift+t"
            callback: 触发时执行的无参回调函数
        """
        pynput_format = self._convert_hotkey(hotkey_str)
        self._callback = callback
        self._current_hotkey = hotkey_str
        
        try:
            self.listener = keyboard.GlobalHotKeys({
                pynput_format: callback
            })
            self.listener.daemon = True
            self.listener.start()
        except Exception as e:
            print(f"[热键注册失败] {e}")
            self.listener = None
    
    def _convert_hotkey(self, hotkey_str: str) -> str:
        """将用户友好格式转换为 pynput 格式
        
        "ctrl+shift+t" → "<ctrl>+<shift>+t"
        修饰键（ctrl, shift, alt, cmd, win）会被包裹在尖括号中。
        
        Args:
            hotkey_str: 如 "ctrl+shift+t"
            
        Returns:
            pynput 格式的快捷键字符串，如 "<ctrl>+<shift>+t"
        """
        modifiers = {'ctrl', 'shift', 'alt', 'cmd', 'win'}
        parts = hotkey_str.lower().split('+')
        result = []
        for part in parts:
            part = part.strip()
            if part in modifiers:
                result.append(f'<{part}>')
            else:
                result.append(part)
        return '+'.join(result)
    
    def unregister(self):
        """注销当前注册的热键"""
        if self.listener:
            self.listener.stop()
            self.listener = None
        self._current_hotkey = ""
    
    def re_register(self, hotkey_str: str, callback):
        """重新注册热键（先注销再注册）
        
        Args:
            hotkey_str: 新的快捷键字符串
            callback: 新的回调函数
        """
        self.unregister()
        self.register(hotkey_str, callback)
    
    @property
    def current_hotkey(self) -> str:
        """当前注册的快捷键字符串"""
        return self._current_hotkey
    
    @property
    def is_active(self) -> bool:
        """热键监听器是否活跃"""
        return self.listener is not None and self.listener.is_alive()
