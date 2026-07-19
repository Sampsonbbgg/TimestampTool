"""TimestampTool 剪贴板与文本注入模块

负责将格式化后的时间戳文本注入到当前焦点窗口，
并在注入完成后恢复原始剪贴板内容。
"""
import pyperclip
from pynput.keyboard import Controller, Key
import time
import threading

from window_utils import set_foreground_hwnd


class ClipboardInjector:
    """剪贴板注入器
    
    通过剪贴板 + 模拟粘贴的方式将文本注入到当前焦点窗口。
    注入后自动恢复原始剪贴板内容，并尝试选中占位符 **。
    """
    
    def __init__(self):
        self.keyboard = Controller()
        self._saved_clipboard = ""
    
    def inject_text(self, text: str, target_hwnd: int = 0):
        """将文本注入到目标窗口（保险起见，先切前台再粘贴）
        
        流程：切前台窗口 → 保存剪贴板 → 写入文本 → 模拟粘贴 → 选中占位符 → 恢复剪贴板
        
        Args:
            text: 要注入的文本内容
            target_hwnd: 目标窗口 HWND；因为菜单不抢焦点原窗口从未失焦，
                通常这一步是冗余保险。传 0 表示跳过前台切换。
        """
        # 0. 保险：切换目标窗口到前台（弹窗不抢焦点时此步通常是 no-op）
        if target_hwnd:
            set_foreground_hwnd(target_hwnd)
            time.sleep(0.03)

        # 1. 保存当前剪贴板内容
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""
        
        # 2. 将新文本写入剪贴板
        pyperclip.copy(text)
        time.sleep(0.05)
        
        # 3. 模拟 Ctrl+V 粘贴
        self.keyboard.press(Key.ctrl)
        self.keyboard.press('v')
        self.keyboard.release('v')
        self.keyboard.release(Key.ctrl)
        time.sleep(0.15)
        
        # 4. 尝试选中占位符 **
        self._select_placeholder(text)
        
        # 5. 延迟恢复剪贴板（在后台线程中，确保粘贴完成）
        threading.Timer(0.3, self._restore_clipboard).start()
    
    def _restore_clipboard(self):
        """恢复原始剪贴板内容"""
        try:
            pyperclip.copy(self._saved_clipboard)
        except Exception:
            pass
    
    def _select_placeholder(self, text: str):
        """选中文本中的内容占位符（## 或 ** 兼容）
        
        粘贴后光标位于文本末尾，通过键盘操作移动光标并选中占位符。
        使用统一的占位符查找逻辑，兼容 ##（推荐）和 **（旧格式）。
        
        Args:
            text: 已注入的文本内容
        """
        from template_engine import TemplateEngine
        result = TemplateEngine.find_content_placeholder(text)
        if not result:
            return
        
        placeholder, pos = result
        ph_len = len(placeholder)
        # 占位符后的字符数（光标从末尾需要左移的距离）
        chars_after = len(text) - pos - ph_len
        
        time.sleep(0.05)
        
        # 从文本末尾向左移动到占位符之后的位置
        if chars_after > 0:
            for _ in range(chars_after):
                self.keyboard.press(Key.left)
                self.keyboard.release(Key.left)
                time.sleep(0.01)
        
        # 用 Shift+Left 选中占位符全部字符
        time.sleep(0.02)
        self.keyboard.press(Key.shift)
        for _ in range(ph_len):
            self.keyboard.press(Key.left)
            self.keyboard.release(Key.left)
            time.sleep(0.01)
        self.keyboard.release(Key.shift)
