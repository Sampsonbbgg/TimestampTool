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
import tkinter
from pathlib import Path

# 确保 src 目录在导入路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk
from template_engine import TemplateEngine
from ui.styles import Colors, Fonts, Sizes, Motion
from ui.components import content_placeholder_note
from window_utils import (
    make_noactivate,
    apply_dwm_rounding,
    set_window_pos,
    get_foreground_hwnd,
    get_tk_hwnd,
    MenuHotkeyGrabber,
)


# ========== 动效颜色工具（仅本模块使用） ==========

def _parse_hex_color(value):
    """'#rgb'/'#rrggbb'/'#rrggbbaa' → ((r, g, b), alpha 0..1)

    SHADOW 令牌 light 态带 AA 通道（如 "#00000014"），解析出 alpha 用于
    阴影窗的整体 -alpha；6 位色值 alpha 记为 1.0。
    """
    s = str(value).lstrip('#')
    if len(s) == 3:
        s = ''.join(c * 2 for c in s)
    a = 1.0
    if len(s) == 8:
        a = int(s[6:8], 16) / 255.0
        s = s[:6]
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)), a


def _lerp_color(rgb1, rgb2, t):
    """两个 (r,g,b) 间线性插值，返回 '#rrggbb' 单值色"""
    return "#%02x%02x%02x" % tuple(
        round(a + (b - a) * t) for a, b in zip(rgb1, rgb2)
    )


class PopupMenu:
    """浮窗模板选择菜单"""

    def __init__(self, master, templates, on_select_callback, target_hwnd=0, columns=1,
                 animations=True):
        """
        Args:
            master: tkinter 主窗口（隐藏的根窗口）
            templates: 模板列表 [{"name": "...", "format": "..."}, ...]
            on_select_callback: 选择回调 callback(template_dict)
            target_hwnd: 触发菜单前的前台窗口 HWND，用于失焦自动关闭判断
            columns: 浮窗每行显示的卡片数量（1/2/3），窗口宽度按此计算
            animations: 是否启用淡入/淡出/悬停渐变动效（关闭时动画帧数=1，
                直接终态；投影保留）
        """
        self.templates = templates
        self.on_select = on_select_callback
        self.target_hwnd = target_hwnd or get_foreground_hwnd()
        self.columns = max(1, min(3, int(columns) if columns else 1))
        self.animations = bool(animations)
        self.window = None
        self._item_frames = []
        self._hotkey_grabber = None
        self._closed = False
        self._focus_check_after_id = None
        # ==== 动效状态 ====
        self._shadow_windows = []    # [(toplevel, 该层独立alpha)] 由外(L1)到内(L3)
        self._shadow_margins = []    # 每层阴影窗相对主窗的外扩边距（递减）
        self._fade_after_id = None   # 淡入/淡出当前排定的 after id
        self._alpha_factor = 1.0     # 当前全局透明度系数（阴影窗 alpha 随之缩放）
        self._hover_after_ids = {}   # 卡片悬停动画 after id（keyed by widget id）
        self._hover_colors = {}      # 卡片当前显示色（渐变中间态，供打断续接）
        self._target_w = 0           # 主窗逻辑宽度（未经 CTk DPI 放大）
        self._target_h = 0           # 主窗逻辑高度
        self._create_window(master)

    def _create_window(self, master):
        """创建不抢焦点的浮窗"""
        self.window = ctk.CTkToplevel(master)
        self.window.overrideredirect(True)  # 无标题栏
        self.window.attributes('-topmost', True)  # 置顶
        self.window.configure(fg_color=Colors.BG_CARD)

        # ==== 动效：淡入从全透明起步（在窗口 map 之前设置，避免首帧闪白） ====
        if self.animations:
            try:
                self.window.attributes('-alpha', 0.0)
            except Exception:
                pass
            self._alpha_factor = 0.0

        # ==== 关键：设置 WS_EX_NOACTIVATE，弹窗不抢焦点 ====
        # 必须在窗口 update 之后设置样式才生效
        self.window.update_idletasks()
        make_noactivate(self.window)
        # Win11 DWM 原生圆角（实测对 overrideredirect 窗口生效；失败则保持现状）
        apply_dwm_rounding(self.window)

        # ==== 多列布局：计算行数、卡片宽度、容器尺寸 ====
        n_items = min(len(self.templates), 9)
        cols = self.columns
        n_rows = (n_items + cols - 1) // cols  # 向上取整
        card_w = Sizes.MENU_CARD_WIDTH
        gap = Sizes.MENU_CARD_GAP
        hpad = Sizes.MENU_HORIZONTAL_PADDING
        # 容器宽度 = 两侧留白 + N 张卡片宽度 + (N-1) 个卡片间隙
        container_w = hpad * 2 + card_w * cols + gap * (cols - 1)
        container_h = self._compute_container_height(n_rows)

        # 主容器（固定宽高，让内部按精确布局展开）
        container = ctk.CTkFrame(
            self.window,
            fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_RADIUS_MENU,
            border_width=1,
            border_color=Colors.BORDER,
            width=container_w,
            height=container_h,
        )
        container.pack(fill="both", expand=True, padx=2, pady=2)
        container.pack_propagate(False)

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

        # ==== 模板卡片：按行分组、每行内横向排布 ====
        for row_idx in range(n_rows):
            row_frame = ctk.CTkFrame(container, fg_color="transparent")
            row_frame.pack(fill="x", padx=hpad, pady=1)
            for col_idx in range(cols):
                item_idx = row_idx * cols + col_idx
                if item_idx >= n_items:
                    break
                tmpl = self.templates[item_idx]
                preview = TemplateEngine.format_template(tmpl['format'])
                item = self._build_menu_item(
                    row_frame, item_idx + 1, tmpl['name'], preview, tmpl
                )
                # 各卡片间用 gap 分隔（第一张卡片左边不加）
                left_pad = gap if col_idx > 0 else 0
                item.pack(side="left", padx=(left_pad, 0))

        # 底部提示（含操作说明和数量信息）
        n = len(self.templates)
        hint_frame = ctk.CTkFrame(container, fg_color="transparent")
        hint_frame.pack(pady=(8, 14), fill="x")

        # 第一行：操作提示
        ctk.CTkLabel(
            hint_frame,
            text="按数字键 1-9 快速选择  ·  ESC 关闭",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY,
        ).pack()

        # 第二行：功能说明（数量 + 粘贴机制，## 说明来自公共单一来源）
        ctk.CTkLabel(
            hint_frame,
            text=f"共 {n} 个模板  ·  选中后自动粘贴，{content_placeholder_note(compact=True)}",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_HINT,
        ).pack(pady=(3, 0))

        # 直接使用计算好的容器高度（避免依赖 winfo_reqheight）
        target_h = container_h + 4  # +4 是 container 外围的 pady*2
        target_w = container_w + 6  # +6 是 container 外围 padx*2 + border 补偿
        self.window.geometry(f"{target_w}x{target_h}")
        # 记录逻辑尺寸（CTk 会按 DPI 把 WxH 放大为物理像素，定位时反推比例）
        self._target_w, self._target_h = target_w, target_h

        # 阴影窗（逐层外扩、垫在主窗之下），创建后统一定位
        self._create_shadow_windows()

        # 定位到鼠标位置（主窗 + 阴影窗统一算，含阴影外扩边距）
        self._position_at_mouse()

        # ==== 关键：启动全局按键独占（1-9 / ESC）====
        self._hotkey_grabber = MenuHotkeyGrabber(
            on_number=lambda i: self._schedule(lambda: self._select_by_index(i)),
            on_escape=lambda: self._schedule(self.close),
        )
        self._hotkey_grabber.start()

        # 定时检查前台窗口是否被切走
        self._focus_check_after_id = self.window.after(400, self._check_foreground)

        # ==== 动效：启动淡入（alpha 0→1，MENU_FADE_IN_MS 内 FADE_STEPS 帧） ====
        if self.animations:
            self._start_fade_in()

    def _compute_container_height(self, n_rows: int) -> int:
        """根据行数精确计算 container 高度

        高度组成（与 _create_window 里的 pack padding 严格对应）：
        - title 区: pady(14+10) + SUBTITLE 字号 ≈ 46
        - separator: 1 + pady(6) = 7
        - rows: n_rows * (MENU_ITEM_HEIGHT + pady*2 = 58+2 = 60)
        - hint_frame: pady(8+14) + 两行 SMALL + gap(3) ≈ 68
        - buffer: 10（防止边界渲染裁剪）
        """
        title_area = 46
        separator_area = 7
        rows_area = n_rows * (Sizes.MENU_ITEM_HEIGHT + 2)
        hint_area = 68
        buffer = 10
        return title_area + separator_area + rows_area + hint_area + buffer

    # ========== 投影：逐层外扩阴影窗 ==========

    def _create_shadow_windows(self):
        """按 SHADOW_L1/L2/L3 令牌创建 Motion.SHADOW_LAYERS 个阴影窗。

        overrideredirect 窗口拿不到 DWM 投影（实测 DwmSetWindowAttribute
        返回 S_OK 但无阴影渲染），改用垫窗方案：
        - 每层一个 topmost + NOACTIVATE 的纯色窗，边距由外到内递减；
        - 颜色取 resolve(SHADOW_Lx) 的 RGB，透明度取令牌 AA 通道；
          6 位色值（dark 主题）按"相对 BG_PRIMARY 的变暗比例"推导 alpha；
        - 各层窗 alpha 经叠算，使叠加后的逐环变暗量正好等于令牌累计值；
        - 阴影窗 alpha 随主窗淡入/淡出系数同步缩放，避免闪边。
        """
        n_layers = max(1, min(3, int(Motion.SHADOW_LAYERS)))
        tokens = [Colors.SHADOW_L1, Colors.SHADOW_L2, Colors.SHADOW_L3][:n_layers]

        ref_rgb, _ = _parse_hex_color(Colors.resolve(Colors.BG_PRIMARY))
        lum_ref = sum(ref_rgb) / 3 / 255.0

        colors, cum_alphas = [], []
        for tok in tokens:
            rgb, a = _parse_hex_color(Colors.resolve(tok))
            if a >= 1.0:
                # 6 位色值：以参考底色（BG_PRIMARY）的相对变暗比例推导
                lum = sum(rgb) / 3 / 255.0
                a = max(0.0, min(0.6, 1.0 - lum / lum_ref)) if lum_ref > 0 else 0.1
            colors.append("#%02x%02x%02x" % rgb)
            cum_alphas.append(a)

        # 累计变暗 → 每层独立 alpha：1-(1-prev)(1-x)=cum → x=(cum-prev)/(1-prev)
        own_alphas, prev = [], 0.0
        for cum in cum_alphas:
            x = (cum - prev) / (1.0 - prev) if prev < 1.0 else 0.0
            own_alphas.append(max(0.0, min(1.0, x)))
            prev = max(prev, cum)

        outer = Sizes.MENU_SHADOW_MARGIN
        step = Sizes.MENU_SHADOW_MARGIN_STEP
        self._shadow_margins = [max(2, outer - i * step) for i in range(n_layers)]

        for color, alpha, margin in zip(colors, own_alphas, self._shadow_margins):
            # 用原生 tkinter.Toplevel：CTkToplevel.geometry 会把 WxH 再乘一次
            # DPI 系数导致阴影窗尺寸错乱，原生窗几何即物理像素，且阴影窗
            # 无任何子控件，纯色垫底即可
            sw = tkinter.Toplevel(self.window.master, bg=color)
            sw.overrideredirect(True)
            sw.attributes('-topmost', True)
            if self.animations:
                try:
                    sw.attributes('-alpha', 0.0)  # 随主窗淡入逐步显现
                except Exception:
                    pass
            # 先在屏幕外完成 map（避免正式定位前在 (0,0) 闪一帧），
            # 之后 _position_at_mouse 用 SetWindowPos 原子落位
            sw.geometry("1x1+-32000+-32000")
            sw.update_idletasks()
            make_noactivate(sw)          # 同样不抢焦点
            apply_dwm_rounding(sw)       # 阴影窗也裁圆角，外缘不生硬
            try:
                sw.update()              # 强制完成映射，SetWindowPos 才稳定生效
            except Exception:
                pass
            self._shadow_windows.append((sw, alpha))

    # ========== 淡入 / 淡出 ==========

    def _apply_alpha(self, factor):
        """把主窗 alpha 设为 factor，并把所有阴影窗 alpha 同比例缩放"""
        self._alpha_factor = factor
        try:
            self.window.attributes('-alpha', max(0.0, min(1.0, factor)))
        except Exception:
            pass
        for sw, base in self._shadow_windows:
            try:
                sw.attributes('-alpha', max(0.0, min(1.0, factor * base)))
            except Exception:
                pass

    def _start_fade_in(self):
        """淡入：FADE_STEPS 帧 ease-out 从 0 → 1（时长 MENU_FADE_IN_MS）"""
        steps = max(1, int(Motion.FADE_STEPS))
        interval = max(1, int(Motion.MENU_FADE_IN_MS) // steps)
        seq = [1.0 - (1.0 - k / steps) ** 2 for k in range(1, steps + 1)]
        self._fade_tick(seq, interval, on_done=None)

    def _start_fade_out(self):
        """淡出：FADE_STEPS 帧线性从当前系数 → 0，走完再销毁（MENU_FADE_OUT_MS）"""
        if self.window is None or not self.window.winfo_exists():
            self._destroy_all()
            return
        start = max(0.0, min(1.0, self._alpha_factor))
        if start <= 0.02:
            self._destroy_all()
            return
        steps = max(1, int(Motion.FADE_STEPS))
        interval = max(1, int(Motion.MENU_FADE_OUT_MS) // steps)
        seq = [start * (1.0 - k / steps) for k in range(1, steps + 1)]
        self._fade_tick(seq, interval, on_done=self._destroy_all)

    def _fade_tick(self, seq, interval, on_done):
        """逐帧应用 alpha 序列（窗口销毁即静默停止）"""
        if self.window is None or not self.window.winfo_exists():
            return
        if not seq:
            if on_done:
                on_done()
            return
        self._apply_alpha(seq[0])
        self._fade_after_id = self.window.after(
            interval, lambda: self._fade_tick(seq[1:], interval, on_done)
        )

    def _cancel_all_animations(self):
        """取消淡入/淡出与全部悬停动画的待执行 after 回调"""
        if self._fade_after_id is not None and self.window:
            try:
                self.window.after_cancel(self._fade_after_id)
            except Exception:
                pass
        self._fade_after_id = None
        for key, after_id in list(self._hover_after_ids.items()):
            try:
                self.window.after_cancel(after_id)
            except Exception:
                pass
        self._hover_after_ids.clear()

    # ========== 悬停渐变 ==========

    def _animate_hover(self, widget, to_hover):
        """卡片悬停：BG_CARD ↔ BG_HOVER 分帧插值（HOVER_FADE_MS / FADE_STEPS）

        - 卡片 transparent 态实际底色是 BG_CARD，故插值区间取
          resolve(BG_CARD) → resolve(BG_HOVER) 的 RGB 线性渐变；
        - 每次进/出先取消该卡片上一个未完成的动画（保存 after id），
          并从当前中间色续接，快速划过多个卡片不会出现
          "已离开还在变深"的竞态；
        - animations 关闭时帧数=1，直接终态。
        """
        key = id(widget)
        prev_id = self._hover_after_ids.pop(key, None)
        if prev_id is not None and self.window:
            try:
                self.window.after_cancel(prev_id)
            except Exception:
                pass

        if self.window is None or not self.window.winfo_exists():
            return
        try:
            if not widget.winfo_exists():
                return
        except Exception:
            return

        base_rgb = _parse_hex_color(Colors.resolve(Colors.BG_CARD))[0]
        hover_rgb = _parse_hex_color(Colors.resolve(Colors.BG_HOVER))[0]
        current = self._hover_colors.get(key)
        start_rgb = (_parse_hex_color(current)[0] if current
                     else (base_rgb if to_hover else hover_rgb))
        end_rgb = hover_rgb if to_hover else base_rgb

        steps = max(1, int(Motion.FADE_STEPS)) if self.animations else 1
        interval = (max(1, int(Motion.HOVER_FADE_MS) // max(1, int(Motion.FADE_STEPS)))
                    if self.animations else 0)

        def tick(k):
            if self.window is None or not self.window.winfo_exists():
                return
            try:
                if not widget.winfo_exists():
                    self._hover_after_ids.pop(key, None)
                    return
            except Exception:
                return
            color = _lerp_color(start_rgb, end_rgb, k / steps)
            try:
                widget.configure(fg_color=color)
            except Exception:
                return
            self._hover_colors[key] = color
            if k < steps:
                self._hover_after_ids[key] = widget.after(interval, lambda: tick(k + 1))
            else:
                self._hover_after_ids.pop(key, None)

        tick(1)  # 第一帧立即推进（steps=1 时即终态）

    def _schedule(self, fn):
        """从 hotkey 线程安全地调度到 tkinter 主线程"""
        if self.window is not None:
            try:
                self.window.after(0, fn)
            except Exception:
                pass

    def _build_menu_item(self, parent, number, name, preview, template):
        """构建单个菜单项卡片 - Fluent 双行卡片布局

        与 _create_menu_item 不同，此方法**只创建卡片但不 pack**，
        由 caller 决定 pack 到哪里（支持多列布局中横向排列）。

        视觉层次：
        - 左侧：数字标记（蓝色圆角方块，突出可点击性）
        - 右侧上行：模板名（大字重字，主要信息）
        - 右侧下行：实时预览（等宽小字灰色，辅助信息）

        Returns:
            item_frame: 未 pack 的卡片框，caller 需自行 pack
        """
        item_frame = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            corner_radius=Sizes.CORNER_RADIUS_CARD,
            height=Sizes.MENU_ITEM_HEIGHT,
            width=Sizes.MENU_CARD_WIDTH,
        )
        item_frame.pack_propagate(False)

        # 左侧数字标记（更粗、更方正的 badge）
        badge = ctk.CTkLabel(
            item_frame,
            text=str(number),
            font=Fonts.BADGE,
            text_color=Colors.ON_ACCENT,
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
            font=Fonts.MENU_ITEM,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
            justify="left",
        )
        name_label.pack(fill="x", anchor="w")

        # 第二行：实时预览（辅助信息，等宽字体）
        preview_label = ctk.CTkLabel(
            text_frame,
            text=preview,
            font=Fonts.PREVIEW_SMALL,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
        )
        preview_label.pack(fill="x", anchor="w", pady=(2, 0))

        # 悬停 & 点击（悬停走渐变动画；点击选中瞬间直接关闭，无需点击态动画）
        def on_enter(e):
            self._animate_hover(item_frame, to_hover=True)

        def on_leave(e):
            self._animate_hover(item_frame, to_hover=False)

        def on_click(e):
            self._select_template(template)

        for widget in [item_frame, badge, text_frame, name_label, preview_label]:
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
            widget.bind('<Button-1>', on_click)

        self._item_frames.append(item_frame)
        return item_frame

    def _position_at_mouse(self):
        """将窗口定位到鼠标位置，考虑屏幕边界（含阴影窗外扩边距）

        阴影窗比主窗大：以"阴影外框"为定位/边界判断的整体，外框左上角
        贴鼠标（即主窗向内偏移最外层边距），边界裁剪统一按外框计算，
        保证阴影窗不会比主窗先被屏幕边界裁掉。
        """
        self.window.update_idletasks()
        x = self.window.winfo_pointerx()
        y = self.window.winfo_pointery()
        w = self.window.winfo_reqwidth()
        h = self.window.winfo_reqheight()
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()

        # 阴影边距按 DPI 比例放大（w 是 CTk 按 DPI 放大后的物理宽，
        # _target_w 是逻辑宽，两者之比即缩放系数；100% 缩放时为 1.0）
        scale = (w / self._target_w) if (self._target_w and w) else 1.0
        margins = [max(1, int(round(m * scale))) for m in self._shadow_margins]

        # 最外层阴影边距（无阴影窗时为 0，行为与旧版一致）
        m = margins[0] if margins else 0

        # 外框（含阴影）左上角
        bx, by = x, y
        if bx + w + 2 * m > screen_w - 10:
            bx = screen_w - w - 2 * m - 10
        if by + h + 2 * m > screen_h - 50:
            by = y - h - 2 * m - 10
        if bx < 10:
            bx = 10
        if by < 10:
            by = 10

        # 主窗 = 外框向内收最外层边距
        main_x, main_y = bx + m, by + m
        self.window.geometry(f"+{main_x}+{main_y}")
        # 兜底：若主窗已被提前 map（阴影窗创建时的 update 泵事件），
        # Tk 挂起的位置请求可能失效，用 SetWindowPos 原子落位（尺寸不变）
        set_window_pos(self.window, main_x, main_y, w, h)

        # 阴影窗：每层以主窗为基准向外扩 margin_i（物理像素）。
        # 走 Win32 SetWindowPos 而非 Tk geometry：实测 overrideredirect 窗
        # 在 map 过渡期 Tk 会丢失挂起的位置请求，SetWindowPos 稳定生效
        for (sw, _), margin in zip(self._shadow_windows, margins):
            set_window_pos(sw, main_x - margin, main_y - margin,
                           w + 2 * margin, h + 2 * margin)

        # 层叠顺序：L1(最外) < L2 < L3 < 主窗
        for sw, _ in self._shadow_windows:
            try:
                sw.lift()
            except Exception:
                pass
        try:
            self.window.lift()
        except Exception:
            pass

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
        """关闭菜单：释放热键独占 + （动效开启时）淡出后销毁，否则立即销毁"""
        if self._closed:
            return
        self._closed = True

        # 先停 hotkey grabber（释放 1-9 / ESC 独占）——必须在淡出动画前，
        # 保证淡出的 80ms 内用户再按数字键/ESC 不受残留独占影响
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

        # 取消未完成的淡入/悬停动画，然后走淡出（或直接销毁）
        self._cancel_all_animations()
        if self.animations:
            self._start_fade_out()
        else:
            self._destroy_all()

    def _destroy_all(self):
        """销毁主窗与全部阴影窗（幂等）"""
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        for sw, _ in self._shadow_windows:
            try:
                sw.destroy()
            except Exception:
                pass
        self._shadow_windows = []
        self._hover_colors.clear()
