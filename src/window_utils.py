"""Windows 窗口 & 全局键盘工具

- get_foreground_hwnd / set_foreground_hwnd: 前台窗口句柄读写
- make_noactivate: 让 tkinter 弹窗不抢焦点（WS_EX_NOACTIVATE + WS_EX_TOOLWINDOW）
    → 关键效果：弹窗显示时，原窗口（如资源管理器的"重命名编辑框"）
      不会失去焦点，编辑态被保留
- MenuHotkeyGrabber: 菜单打开期间独占 1-9 / ESC 全局按键
    → 关键效果：这些按键不会传递到原窗口，用户按 "1" 不会先在编辑框
      输入 "1" 再关闭菜单；ESC 只关菜单不会取消原窗口操作
"""
import sys
import threading
import ctypes
from ctypes import wintypes

if sys.platform == 'win32':
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
else:
    _user32 = None
    _kernel32 = None

# ---- Windows API 常量 ----
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

VK_ESCAPE = 0x1B
VK_1 = 0x31          # 主键盘 '1'
VK_NUMPAD1 = 0x61    # 小键盘 '1'


# ============ 前台窗口句柄读写 ============

def get_foreground_hwnd() -> int:
    """获取当前前台窗口 HWND（Win32 handle），非 Windows 返回 0"""
    if _user32 is None:
        return 0
    try:
        return int(_user32.GetForegroundWindow())
    except Exception:
        return 0


def set_foreground_hwnd(hwnd: int) -> bool:
    """将指定窗口设为前台窗口。若原窗口焦点已保持则通常无需调用。"""
    if _user32 is None or not hwnd:
        return False
    try:
        return bool(_user32.SetForegroundWindow(hwnd))
    except Exception:
        return False


# ============ tkinter 窗口不抢焦点 ============

def make_noactivate(tk_toplevel):
    """给 tkinter 顶层窗口打上 WS_EX_NOACTIVATE + WS_EX_TOOLWINDOW 扩展样式。

    作用：
    - WS_EX_NOACTIVATE：窗口不能被激活（点击/显示都不抢焦点）
    - WS_EX_TOOLWINDOW：不在任务栏显示、不参与 Alt+Tab

    必须在窗口已创建（wm_frame 可取到 HWND）后调用。
    """
    if _user32 is None:
        return False
    try:
        tk_toplevel.update_idletasks()
        hwnd_str = tk_toplevel.wm_frame()
        if not hwnd_str:
            return False
        hwnd = int(hwnd_str, 16)
        if not hwnd:
            return False
        cur = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        new = cur | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new)
        return True
    except Exception:
        return False


def get_tk_hwnd(tk_toplevel) -> int:
    """获取 tkinter 顶层窗口的 Win32 HWND（用于比较前台窗口是否切换）"""
    if _user32 is None:
        return 0
    try:
        hwnd_str = tk_toplevel.wm_frame()
        if hwnd_str:
            return int(hwnd_str, 16)
    except Exception:
        pass
    return 0


# ============ 菜单期间独占 1-9 / ESC 全局按键 ============

class MenuHotkeyGrabber:
    """通过 Windows RegisterHotKey 在菜单打开期间独占按键。

    关键行为：注册的热键会被系统独占，按键不会传递到任何其他窗口，
    因此在"新建文件夹重命名"场景下按数字键选模板，原编辑框不会先输入数字。

    实现细节：
    - RegisterHotKey 需要在同一线程 GetMessage 才能收到 WM_HOTKEY，
      所以我们用独立守护线程运行消息循环。
    - stop() 通过 PostThreadMessageW(WM_QUIT) 让 GetMessage 返回、循环退出。
    """
    # 热键 ID 分配（避免冲突）
    _ID_NUM_BASE = 101        # 101-109 主键盘 1-9
    _ID_NUMPAD_BASE = 121     # 121-129 小键盘 1-9
    _ID_ESCAPE = 199

    def __init__(self, on_number, on_escape):
        """
        Args:
            on_number: callable(idx: int)，用户按 1-9 时触发（1<=idx<=9）
            on_escape: callable()，用户按 ESC 时触发
        """
        self.on_number = on_number
        self.on_escape = on_escape
        self._thread = None
        self._tid = 0
        self._stopped = threading.Event()

    def start(self):
        if _user32 is None:
            return
        self._stopped.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            self._tid = _kernel32.GetCurrentThreadId()
            # 注册 1-9（主键盘 & 小键盘）
            for i in range(9):
                _user32.RegisterHotKey(
                    None, self._ID_NUM_BASE + i, 0, VK_1 + i
                )
                _user32.RegisterHotKey(
                    None, self._ID_NUMPAD_BASE + i, 0, VK_NUMPAD1 + i
                )
            _user32.RegisterHotKey(None, self._ID_ESCAPE, 0, VK_ESCAPE)

            msg = wintypes.MSG()
            while not self._stopped.is_set():
                ret = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:  # WM_QUIT 或错误
                    break
                if msg.message == WM_HOTKEY:
                    hk_id = int(msg.wParam)
                    if self._ID_NUM_BASE <= hk_id < self._ID_NUM_BASE + 9:
                        idx = hk_id - self._ID_NUM_BASE + 1
                        self._safe_call(self.on_number, idx)
                    elif self._ID_NUMPAD_BASE <= hk_id < self._ID_NUMPAD_BASE + 9:
                        idx = hk_id - self._ID_NUMPAD_BASE + 1
                        self._safe_call(self.on_number, idx)
                    elif hk_id == self._ID_ESCAPE:
                        self._safe_call(self.on_escape)
        finally:
            self._unregister_all()

    @staticmethod
    def _safe_call(func, *args):
        try:
            func(*args)
        except Exception:
            pass

    def _unregister_all(self):
        if _user32 is None:
            return
        for i in range(9):
            try:
                _user32.UnregisterHotKey(None, self._ID_NUM_BASE + i)
                _user32.UnregisterHotKey(None, self._ID_NUMPAD_BASE + i)
            except Exception:
                pass
        try:
            _user32.UnregisterHotKey(None, self._ID_ESCAPE)
        except Exception:
            pass

    def stop(self):
        """请求停止（线程安全，可从任意线程调用）"""
        if self._stopped.is_set():
            return
        self._stopped.set()
        if self._tid and _user32 is not None:
            try:
                _user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            except Exception:
                pass
