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
import time
import ctypes
from ctypes import wintypes

if sys.platform == 'win32':
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _dwmapi = ctypes.windll.dwmapi
else:
    _user32 = None
    _kernel32 = None
    _dwmapi = None

# ---- Windows API 常量 ----
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

# SetWindowPos 标志
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

# DWM 窗口属性（Win11 圆角）——实测 overrideredirect 窗口上圆角生效、
# 投影不生效（DWMWA_NCRENDERING_POLICY 强制后无阴影），故投影由
# popup_menu 的逐层阴影窗实现，这里只借用 DWM 拿原生圆角。
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2  # 标准 ~8px 圆角

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


def apply_dwm_rounding(tk_toplevel, preference: int = DWMWCP_ROUND) -> bool:
    """给窗口设置 Win11 DWM 圆角偏好（DWMWA_WINDOW_CORNER_PREFERENCE）。

    实测：对 overrideredirect + WS_EX_NOACTIVATE 窗口生效，DWM 会把窗口
    裁成原生圆角（约 8px），与 container 的 12px 圆角叠加后观感更柔和。
    设置失败（非 Win11 / API 不可用）时静默返回 False，不影响窗口功能。
    """
    if _dwmapi is None:
        return False
    try:
        tk_toplevel.update_idletasks()
        hwnd = get_tk_hwnd(tk_toplevel)
        if not hwnd:
            return False
        value = ctypes.c_int(preference)
        hr = _dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(value), ctypes.sizeof(value),
        )
        return hr == 0
    except Exception:
        return False


def set_window_pos(tk_toplevel, x: int, y: int, w: int, h: int) -> bool:
    """用 Win32 SetWindowPos 原子地设定窗口尺寸+位置（不激活、不动层序）。

    为什么阴影窗不走 Tk geometry：overrideredirect 窗在 map 过渡期间，
    Tk 挂起的"位置请求"可能丢失（实测：合并串只应用尺寸、拆开的
    位置调用也被忽略），而 SetWindowPos 在已 map 的窗口上始终生效。
    SWP_NOACTIVATE 保持不抢焦点，SWP_NOZORDER 保持既有叠放次序。
    """
    if _user32 is None:
        return False
    try:
        hwnd = get_tk_hwnd(tk_toplevel)
        if not hwnd:
            return False
        return bool(_user32.SetWindowPos(
            hwnd, 0, int(x), int(y), int(w), int(h),
            SWP_NOZORDER | SWP_NOACTIVATE,
        ))
    except Exception:
        return False


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
                self._register_with_retry(self._ID_NUM_BASE + i, VK_1 + i)
                self._register_with_retry(self._ID_NUMPAD_BASE + i, VK_NUMPAD1 + i)
            self._register_with_retry(self._ID_ESCAPE, VK_ESCAPE)

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

    @staticmethod
    def _register_with_retry(hk_id, vk, attempts=5, delay=0.03):
        """RegisterHotKey 带短暂重试。

        菜单淡出动画期间 close() 已 stop() 旧 grabber，但旧线程的
        UnregisterHotKey 是异步完成的；若用户在 80ms 淡出内再次呼出
        菜单，新 grabber 可能撞上"热键尚未被旧线程注销"而注册失败。
        重试 5×30ms（≈150ms）足以覆盖该窗口期，且不影响正常路径。
        """
        for i in range(attempts):
            try:
                if _user32.RegisterHotKey(None, hk_id, 0, vk):
                    return True
            except Exception:
                return False
            time.sleep(delay)
        return False

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
