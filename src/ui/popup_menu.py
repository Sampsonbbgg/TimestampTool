"""TimestampTool 浮窗模板选择菜单

设计核心（第一性原理）：
- 弹窗设置 WS_EX_NOACTIVATE，**永不抢焦点** → 用户在"新建文件夹重命名"
  等场景下按快捷键呼出菜单，原编辑框保持编辑态不被打断
- 用 Windows RegisterHotKey 在菜单打开期间**独占** 1-9 / ESC 全局按键，
  按键既能被菜单接收，也不会传递到原窗口（避免污染编辑框输入）
- 菜单选中后不需要 SetForegroundWindow（原窗口从没失焦），
  clipboard 直接 SendInput 粘贴，注入到原编辑框
"""
import sys
from pathlib import Path

# 确保 src 目录在导入路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk
from template_engine import TemplateEngine
from ui.styles import Colors, Fonts, Sizes
from window_utils import (
    make_noactivate,
    get_foreground_hwnd,
    get_tk_hwnd,
    MenuHotkeyGrabber,
)


class PopupMenu:
    """浮窗模板选择菜单"""

    def __init__(self, master, templates, on_select_callback, target_hwnd=0):
        """
        Args:
            master: tkinter 主窗口（隐藏的根窗口）
            templates: 模板列表 [{"name": "...", "format": "..."}, ...]
            on_select_callback: 选择回调 callback(template_dict)
            target_hwnd: 触发菜单前的前台窗口 HWND，用于失焦自动关闭判断
        """
        self.templates = templates
        self.on_select = on_select_callback
        self.target_hwnd = target_hwnd or get_foreground_hwnd()
        self.window = None
        self._item_frames = []
        self._hotkey_grabber = None
        self._closed = False
        self._focus_check_after_id = None
        self._create_window(master)

    def _create_window(self, master):
        """创建不抢焦点的浮窗"""
        self.window = ctk.CTkToplevel(master)
        self.window.overrideredirect(True)  # 无标题栏
        self.window.attributes('-topmost', True)  # 置顶
        self.window.configure(fg_color=Colors.BG_CARD)

        # ==== 关键：设置 WS_EX_NOACTIVATE，弹窗不抢焦点 ====
        # 必须在窗口 update 之后设置样式才生效
        self.window.update_idletasks()
        make_noactivate(self.window)

        # ==== 动态计算容器高度 ====
        # pack_propagate(False) 会锁死 width 和 height 两个维度，
        # 若不按实际模板数计算高度，会导致第 5+ 个模板被裁掉。
        n_items = min(len(self.templates), 9)
        container_h = self._compute_container_height(n_items)

        # 主容器（带圆角效果 + 固定宽高）
        container = ctk.CTkFrame(
            self.window,
            fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_RADIUS_MENU,
            border_width=1,
            border_color=Colors.BORDER,
            width=Sizes.MENU_MAX_WIDTH,
            height=container_h,
        )
        container.pack(fill="both", expand=True, padx=2, pady=2)
        container.pack_propagate(False)  # 固定宽高，让内部按容器尺寸铺开

        # 标题
        title = ctk.CTkLabel(
            container,
            text="选择时间戳模板",
            font=Fonts.SUBTITLE,
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(pady=(14, 10), padx=16)

        # 分隔线（细微感）
        sep = ctk.CTkFrame(container, height=1, fg_color=Colors.BORDER)
        sep.pack(fill="x", padx=16, pady=(0, 6))

        # 模板列表项（最多9个，对应数字键1-9）
        for idx, tmpl in enumerate(self.templates[:9]):
            preview = TemplateEngine.format_template(tmpl['format'])
            self._create_menu_item(container, idx + 1, tmpl['name'], preview, tmpl)

        # 底部提示（含操作说明和数量信息）
        n = len(self.templates)
        hint_frame = ctk.CTkFrame(container, fg_color="transparent")
        hint_frame.pack(pady=(8, 12))

        # 第一行：操作提示
        ctk.CTkLabel(
            hint_frame,
            text="按数字键 1-9 快速选择  ·  ESC 关闭",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_HINT,
        ).pack()

        # 第二行：功能说明（用户觉得设计好的提醒小文字）
        ctk.CTkLabel(
            hint_frame,
            text=f"共 {n} 个模板  ·  选中后自动粘贴，## 处会被选中供输入",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_HINT,
        ).pack(pady=(2, 0))

        # 直接使用计算好的容器高度（避免依赖 winfo_reqheight，
        # 因为 pack_propagate=False 下 reqheight 是锁死的容器高度而不是内容真实高度）
        target_h = container_h + 4  # +4 是 container 外围的 pady*2
        self.window.geometry(f"{Sizes.MENU_MAX_WIDTH + 6}x{target_h}")

        # 定位到鼠标位置
        self._position_at_mouse()

        # ==== 关键：启动全局按键独占（1-9 / ESC）====
        # 这里不再用 tkinter bind，因为窗口不激活时收不到按键
        self._hotkey_grabber = MenuHotkeyGrabber(
            on_number=lambda i: self._schedule(lambda: self._select_by_index(i)),
            on_escape=lambda: self._schedule(self.close),
        )
        self._hotkey_grabber.start()

        # 定时检查前台窗口是否被切走（用户切到别的 App 就自动关菜单）
        self._focus_check_after_id = self.window.after(400, self._check_foreground)

    def _compute_container_height(self, n_items: int) -> int:
        """根据模板数量精确计算 container 高度

        高度组成（与 _create_window 里的 pack padding 严格对应）：
        - title 区: pady(14+10) + Fonts.SUBTITLE 字号高度 ≈ 46
        - separator: 1 + pady(6) = 7
        - items: n_items * (MENU_ITEM_HEIGHT + pady*2 = 58+2 = 60)
        - hint_frame: pady(8+12) + 两行 SMALL 字号 + gap(2) ≈ 55
        - buffer: 4（防止边界渲染裁剪）
        """
        title_area = 46
        separator_area = 7
        items_area = n_items * (Sizes.MENU_ITEM_HEIGHT + 2)
        hint_area = 55
        buffer = 4
        return title_area + separator_area + items_area + hint_area + buffer

    def _schedule(self, fn):
        """从 hotkey 线程安全地调度到 tkinter 主线程"""
        if self.window is not None:
            try:
                self.window.after(0, fn)
            except Exception:
                pass

    def _create_menu_item(self, parent, number, name, preview, template):
        """创建单个菜单项 - Fluent 双行卡片布局

        视觉层次：
        - 左侧：数字标记（蓝色圆角方块，突出可点击性）
        - 右侧上行：模板名（大字重字，主要信息）
        - 右侧下行：实时预览（等宽小字灰色，辅助信息）
        """
        item_frame = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            corner_radius=Sizes.CORNER_RADIUS_CARD,
            height=Sizes.MENU_ITEM_HEIGHT,
        )
        item_frame.pack(fill="x", padx=8, pady=1)
        item_frame.pack_propagate(False)

        # 左侧数字标记（更粗、更方正的 badge）
        badge = ctk.CTkLabel(
            item_frame,
            text=str(number),
            font=(Fonts.FAMILY, 13, "bold"),
            text_color="#FFFFFF",
            fg_color=Colors.ACCENT,
            corner_radius=6,
            width=Sizes.MENU_BADGE_SIZE,
            height=Sizes.MENU_BADGE_SIZE,
        )
        badge.pack(side="left", padx=(10, 12), pady=15)

        # 右侧文本容器（垂直堆叠：名称 + 预览）
        text_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=8, padx=(0, 10))

        # 第一行：模板名（主要信息）
        name_label = ctk.CTkLabel(
            text_frame,
            text=name,
            font=(Fonts.FAMILY, 13, "bold"),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
            justify="left",
        )
        name_label.pack(fill="x", anchor="w")

        # 第二行：实时预览（辅助信息，等宽字体）
        preview_label = ctk.CTkLabel(
            text_frame,
            text=preview,
            font=("Consolas", 10),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
        )
        preview_label.pack(fill="x", anchor="w", pady=(2, 0))

        # 悬停 & 点击
        def on_enter(e):
            item_frame.configure(fg_color=Colors.BG_HOVER)

        def on_leave(e):
            item_frame.configure(fg_color="transparent")

        def on_click(e):
            self._select_template(template)

        for widget in [item_frame, badge, text_frame, name_label, preview_label]:
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
            widget.bind('<Button-1>', on_click)

        self._item_frames.append(item_frame)

    def _position_at_mouse(self):
        """将窗口定位到鼠标位置，考虑屏幕边界"""
        self.window.update_idletasks()
        x = self.window.winfo_pointerx()
        y = self.window.winfo_pointery()
        w = self.window.winfo_reqwidth()
        h = self.window.winfo_reqheight()
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()

        if x + w > screen_w - 10:
            x = screen_w - w - 10
        if y + h > screen_h - 50:
            y = y - h - 10
        if x < 10:
            x = 10
        if y < 10:
            y = 10
        self.window.geometry(f"+{x}+{y}")

    def _check_foreground(self):
        """周期检查前台窗口：用户切走了就关闭菜单

        菜单本身 WS_EX_NOACTIVATE 不会成为前台，所以：
        - 前台仍是 target_hwnd 或其亲缘窗口 → 保持菜单打开
        - 前台变成完全无关的窗口 → 用户明显切走了，关闭菜单
        """
        if self._closed or self.window is None or not self.window.winfo_exists():
            return
        try:
            fg = get_foreground_hwnd()
            menu_hwnd = get_tk_hwnd(self.window)
            # 菜单永远不会成为 fg（NOACTIVATE），所以 fg == menu_hwnd 不会发生
            # 只在 fg 变化且不是原窗口时关菜单
            if fg and fg != menu_hwnd and self.target_hwnd and fg != self.target_hwnd:
                self.close()
                return
        except Exception:
            pass
        self._focus_check_after_id = self.window.after(400, self._check_foreground)

    def _select_by_index(self, idx):
        """通过数字键选择模板"""
        if 1 <= idx <= len(self.templates):
            self._select_template(self.templates[idx - 1])

    def _select_template(self, template):
        """选择模板并执行回调"""
        self.close()
        if self.on_select:
            self.on_select(template)

    def close(self):
        """关闭菜单：释放热键独占 + 销毁窗口"""
        if self._closed:
            return
        self._closed = True

        # 先停 hotkey grabber（释放 1-9 / ESC 独占）
        if self._hotkey_grabber:
            try:
                self._hotkey_grabber.stop()
            except Exception:
                pass
            self._hotkey_grabber = None

        # 取消定时检查
        if self._focus_check_after_id and self.window:
            try:
                self.window.after_cancel(self._focus_check_after_id)
            except Exception:
                pass
            self._focus_check_after_id = None

        # 销毁窗口
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
