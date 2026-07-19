"""TimestampTool 设置窗口 - 模板管理界面

Win11 现代简约风格设置窗口，提供模板增删改、快捷键配置、重置等功能。
"""
import sys
from pathlib import Path

# 确保 src 目录在导入路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk
from template_engine import TemplateEngine
from paths import resource_path
from ui.styles import Colors, Fonts, Sizes
import autostart


class SettingsWindow:
    """设置窗口 - 模板管理界面"""

    def __init__(self, config_manager, on_save_callback=None):
        """
        Args:
            config_manager: ConfigManager 实例
            on_save_callback: 保存后的回调（用于通知主程序重注册热键等）
        """
        self.config = config_manager
        self.on_save_callback = on_save_callback
        self.window = None
        self._selected_index = -1
        self._card_frames = []
        self._preview_labels = []
        self._update_timer = None
        # 工作副本（编辑时不直接修改配置）
        self._templates = []
        self._hotkey = ""

    def show(self):
        """显示设置窗口（防止重复创建）"""
        if self.window is not None and self.window.winfo_exists():
            self.window.focus_force()
            return

        # 加载配置工作副本
        self._templates = [t.copy() for t in self.config.templates]
        self._hotkey = self.config.hotkey

        self._create_window()

    def _create_window(self):
        """创建设置窗口"""
        self.window = ctk.CTkToplevel()
        self.window.title("TimestampTool 设置")
        self.window.geometry("620x620")
        self.window.resizable(False, False)
        self.window.configure(fg_color=Colors.BG_PRIMARY)
        self.window.attributes('-topmost', True)

        # 在短暂延迟后取消置顶，使窗口正常交互
        self.window.after(200, lambda: self.window.attributes('-topmost', False))

        # 图标（如果存在）
        icon_path = resource_path("assets/icon.ico")
        if icon_path.exists():
            try:
                self.window.after(50, lambda: self.window.iconbitmap(str(icon_path)))
            except Exception:
                pass

        # 主内容区
        main_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # ===== 模板管理区域 =====
        self._create_template_section(main_frame)

        # ===== 快捷键设置区域 =====
        self._create_hotkey_section(main_frame)

        # ===== 偏好设置区域（开机自启等） =====
        self._create_preference_section(main_frame)

        # ===== 底部按钮区域 =====
        self._create_bottom_buttons(main_frame)

        # 启动预览更新定时器
        self._start_preview_timer()

        # 窗口关闭时清理
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_template_section(self, parent):
        """创建模板管理区域"""
        # 区域标题
        section_frame = ctk.CTkFrame(
            parent, fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_RADIUS_CARD,
            border_width=1, border_color=Colors.BORDER
        )
        section_frame.pack(fill="both", expand=True, pady=(0, 12))

        # 标题标签（含数量提示，实时反映当前模板数量）
        self._section_title_label = ctk.CTkLabel(
            section_frame, text=self._get_section_title(),
            font=Fonts.SUBTITLE, text_color=Colors.TEXT_PRIMARY, anchor="w"
        )
        self._section_title_label.pack(fill="x", padx=16, pady=(12, 8))

        # 可滚动模板列表
        self._scroll_frame = ctk.CTkScrollableFrame(
            section_frame, fg_color="transparent", height=200
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # 渲染模板卡片
        self._render_template_cards()

        # 按钮区域
        btn_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            btn_frame, text="+ 添加", width=80,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
            font=Fonts.BODY, command=self._on_add
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="✎ 编辑", width=80,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
            font=Fonts.BODY, command=self._on_edit
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="🗑 删除", width=80,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.ERROR, hover_color="#B02A2D",
            font=Fonts.BODY, command=self._on_delete
        ).pack(side="left")

    def _create_hotkey_section(self, parent):
        """创建快捷键设置区域"""
        section_frame = ctk.CTkFrame(
            parent, fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_RADIUS_CARD,
            border_width=1, border_color=Colors.BORDER
        )
        section_frame.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(section_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            inner, text="快捷键设置", font=Fonts.SUBTITLE,
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            inner, text="触发快捷键:", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 8))

        self._hotkey_entry = ctk.CTkEntry(
            inner, width=180, height=Sizes.BUTTON_HEIGHT,
            font=Fonts.MONO, corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            border_color=Colors.BORDER
        )
        self._hotkey_entry.pack(side="left")
        self._hotkey_entry.insert(0, self._hotkey)

    def _create_preference_section(self, parent):
        """创建偏好设置区域（开机自启 + 浮窗列数等）"""
        section_frame = ctk.CTkFrame(
            parent, fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_RADIUS_CARD,
            border_width=1, border_color=Colors.BORDER
        )
        section_frame.pack(fill="x", pady=(0, 12))

        # ==== 行 1: 标题 + 开机自启开关 ====
        row1 = ctk.CTkFrame(section_frame, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            row1, text="偏好设置", font=Fonts.SUBTITLE,
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            row1, text="开机自动启动:", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 8))

        actual_enabled = autostart.is_enabled()
        self._autostart_var = ctk.BooleanVar(value=actual_enabled)
        self._autostart_switch = ctk.CTkSwitch(
            row1,
            text="",
            variable=self._autostart_var,
            command=self._on_autostart_toggle,
            onvalue=True, offvalue=False,
            progress_color=Colors.ACCENT,
            button_color="#FFFFFF",
            button_hover_color="#F0F0F0",
            width=48,
        )
        self._autostart_switch.pack(side="left", padx=(0, 8))

        self._autostart_status = ctk.CTkLabel(
            row1,
            text=("已启用" if actual_enabled else "未启用"),
            font=Fonts.SMALL,
            text_color=(Colors.SUCCESS if actual_enabled else Colors.TEXT_HINT),
        )
        self._autostart_status.pack(side="left")

        # ==== 行 2: 浮窗每行显示 N 个 + 布局预告 ====
        row2 = ctk.CTkFrame(section_frame, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(4, 12))

        # 缩进对齐（跟"开机自动启动"标签左侧起点保持一致）
        ctk.CTkLabel(row2, text="", width=64).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            row2, text="浮窗每行显示:", font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 8))

        current_cols = self.config.menu_columns
        self._menu_columns_var = ctk.StringVar(value=str(current_cols))
        self._menu_columns_option = ctk.CTkOptionMenu(
            row2,
            values=["1", "2", "3"],
            variable=self._menu_columns_var,
            command=self._on_menu_columns_change,
            width=64, height=28,
            font=Fonts.BODY,
            fg_color=Colors.ACCENT,
            button_color=Colors.ACCENT_HOVER,
        )
        self._menu_columns_option.pack(side="left", padx=(0, 8))

        # 单位标签
        ctk.CTkLabel(
            row2, text="个/行", font=Fonts.SMALL,
            text_color=Colors.TEXT_HINT
        ).pack(side="left", padx=(0, 16))

        # 布局预告文字（实时更新）
        self._layout_preview_label = ctk.CTkLabel(
            row2, text=self._get_layout_preview_text(current_cols),
            font=Fonts.SMALL,
            text_color=Colors.ACCENT,
        )
        self._layout_preview_label.pack(side="left")

    def _get_layout_preview_text(self, columns: int) -> str:
        """生成布局预告文字：'共 N 个模板 → M 行 × K 列'"""
        n_templates = min(len(self._templates) if self._templates else 0, 9)
        if n_templates == 0:
            return "预告：暂无模板"
        cols = max(1, min(3, int(columns)))
        rows = (n_templates + cols - 1) // cols  # 向上取整
        return f"预告：共 {n_templates} 个模板 → {rows} 行 × {cols} 列"

    def _on_menu_columns_change(self, value: str):
        """浮窗列数下拉切换回调"""
        try:
            new_cols = int(value)
        except (ValueError, TypeError):
            return

        # 立即持久化
        self.config.menu_columns = new_cols
        try:
            self.config.save()
        except Exception:
            pass

        # 更新预告文字
        if hasattr(self, '_layout_preview_label') and self._layout_preview_label:
            try:
                self._layout_preview_label.configure(
                    text=self._get_layout_preview_text(new_cols)
                )
            except Exception:
                pass

    def _on_autostart_toggle(self):
        """开机自启开关切换回调"""
        desired = bool(self._autostart_var.get())
        ok = autostart.sync(desired)

        if not ok:
            # 操作失败，回滚 UI 状态
            self._autostart_var.set(not desired)
            self._autostart_status.configure(
                text="操作失败", text_color=Colors.ERROR
            )
            self._show_message("开机自启操作失败\n请检查权限或杀毒软件设置")
            return

        # 立即持久化到 config（下次打开设置窗口时保持一致）
        self.config.autostart = desired
        try:
            self.config.save()
        except Exception:
            pass

        # 更新状态文字
        self._autostart_status.configure(
            text=("已启用" if desired else "未启用"),
            text_color=(Colors.SUCCESS if desired else Colors.TEXT_HINT),
        )

    def _create_bottom_buttons(self, parent):
        """创建底部按钮区域"""
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x")

        # 左侧 - 重置默认
        ctk.CTkButton(
            btn_frame, text="重置默认", width=100,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.WARNING, hover_color="#E07800",
            font=Fonts.BODY, command=self._on_reset
        ).pack(side="left")

        # 右侧 - 保存 & 取消
        ctk.CTkButton(
            btn_frame, text="保存", width=92,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
            font=Fonts.BODY, command=self._on_save
        ).pack(side="right")

        ctk.CTkButton(
            btn_frame, text="取消", width=92,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.BG_HOVER, hover_color=Colors.BG_ACTIVE,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.BODY, command=self._on_close
        ).pack(side="right", padx=(0, 8))

    # ===== 模板卡片渲染 =====

    def _get_section_title(self) -> str:
        """标题栏文字：模板管理 (共 N 个)"""
        n = len(self._templates) if self._templates else 0
        return f"模板管理 (共 {n} 个)"

    def _render_template_cards(self):
        """渲染/刷新模板卡片列表"""
        # 清空现有卡片
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._card_frames = []
        self._preview_labels = []
        self._selected_index = -1

        for idx, tmpl in enumerate(self._templates):
            self._create_card(idx, tmpl)

        # 同步更新标题栏的数量显示
        if hasattr(self, '_section_title_label') and self._section_title_label:
            try:
                self._section_title_label.configure(text=self._get_section_title())
            except Exception:
                pass

        # 同步更新布局预告（模板数变了，预告的 M 行也要重算）
        if hasattr(self, '_layout_preview_label') and self._layout_preview_label:
            try:
                cur_cols = int(self._menu_columns_var.get()) if hasattr(self, '_menu_columns_var') else 1
                self._layout_preview_label.configure(
                    text=self._get_layout_preview_text(cur_cols)
                )
            except Exception:
                pass

    def _create_card(self, idx, tmpl):
        """创建单个模板卡片"""
        card = ctk.CTkFrame(
            self._scroll_frame, fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_RADIUS_CARD,
            border_width=1, border_color=Colors.BORDER, height=52
        )
        card.pack(fill="x", pady=3)
        card.pack_propagate(False)

        # 名称标签
        name_label = ctk.CTkLabel(
            card, text=tmpl['name'], font=Fonts.BODY,
            text_color=Colors.TEXT_PRIMARY, anchor="w", width=120
        )
        name_label.pack(side="left", padx=(12, 8), pady=8)

        # 格式标签
        fmt_label = ctk.CTkLabel(
            card, text=tmpl['format'], font=Fonts.MONO,
            text_color=Colors.TEXT_SECONDARY, anchor="w", width=180
        )
        fmt_label.pack(side="left", padx=(0, 8), pady=8)

        # 实时预览
        preview_text = TemplateEngine.preview_template(tmpl['format'])
        preview_label = ctk.CTkLabel(
            card, text=preview_text, font=("Consolas", 10),
            text_color=Colors.ACCENT, anchor="e"
        )
        preview_label.pack(side="right", padx=12, pady=8)

        # 绑定点击事件选中卡片
        def on_click(e, i=idx):
            self._select_card(i)

        for widget in [card, name_label, fmt_label, preview_label]:
            widget.bind('<Button-1>', on_click)
            widget.bind('<Double-Button-1>', lambda e, i=idx: self._on_edit())

        self._card_frames.append(card)
        self._preview_labels.append((preview_label, tmpl['format']))

    def _select_card(self, idx):
        """选中指定索引的卡片"""
        # 先取消之前选中的高亮
        if 0 <= self._selected_index < len(self._card_frames):
            self._card_frames[self._selected_index].configure(
                border_color=Colors.BORDER
            )

        self._selected_index = idx

        # 高亮当前选中
        if 0 <= idx < len(self._card_frames):
            self._card_frames[idx].configure(border_color=Colors.ACCENT)

    # ===== 预览定时器 =====

    def _start_preview_timer(self):
        """启动每秒更新预览的定时器"""
        self._update_previews()

    def _update_previews(self):
        """更新所有卡片的实时预览文本"""
        if self.window is None or not self.window.winfo_exists():
            return

        for label, fmt in self._preview_labels:
            try:
                preview = TemplateEngine.preview_template(fmt)
                label.configure(text=preview)
            except Exception:
                pass

        self._update_timer = self.window.after(1000, self._update_previews)

    # ===== 按钮回调 =====

    def _persist_now(self):
        """立即把工作副本写入配置文件并通知主程序热更新

        拆分为两步——templates 保存和 hotkey 保存独立，避免耦合失败：
        - Step 1（关键路径）：把 templates 写入 config.json；失败会弹窗
        - Step 2（附加）：同步 hotkey；失败静默
        - Step 3：通知主程序热更新（重注册热键）

        为什么拆开：过去把两步塞到一个 try 里，一旦 hotkey 读取抛错
        （比如 CTkEntry 状态异常），templates 也不会 save，用户就会遇到
        "添加了模板但下次弹窗看不到"的现象。
        """
        # ---- Step 1: 保存模板（关键路径，用 list copy 避免引用共享）----
        try:
            self.config.templates = list(self._templates)
            self.config.save()
        except Exception as e:
            # 保存失败时用可见的弹窗通知，避免用户以为已保存
            try:
                self._show_message(f"模板保存失败：\n{e}")
            except Exception:
                pass
            return  # 关键路径失败，后续不再继续

        # ---- Step 2: 同步 hotkey（附加，失败不影响 templates 已保存）----
        try:
            entry = getattr(self, '_hotkey_entry', None)
            if entry:
                hotkey_value = entry.get().strip()
                if hotkey_value and hotkey_value != self.config.hotkey:
                    self.config.hotkey = hotkey_value
                    self.config.save()
        except Exception:
            pass

        # ---- Step 3: 通知主程序热更新 ----
        try:
            if self.on_save_callback:
                self.on_save_callback()
        except Exception:
            pass

    def _on_add(self):
        """添加模板"""
        dialog = EditTemplateDialog(self.window, title="添加模板")
        dialog.show()
        if dialog.result:
            self._templates.append(dialog.result)
            self._render_template_cards()
            self._persist_now()

    def _on_edit(self):
        """编辑选中的模板"""
        if self._selected_index < 0:
            self._show_message("请先选择一个模板")
            return

        tmpl = self._templates[self._selected_index]
        dialog = EditTemplateDialog(
            self.window, title="编辑模板",
            initial_name=tmpl['name'], initial_format=tmpl['format']
        )
        dialog.show()
        if dialog.result:
            self._templates[self._selected_index] = dialog.result
            self._render_template_cards()
            self._persist_now()

    def _on_delete(self):
        """删除选中的模板"""
        if self._selected_index < 0:
            self._show_message("请先选择一个模板")
            return

        if len(self._templates) <= 1:
            self._show_message("至少需要保留一个模板")
            return

        del self._templates[self._selected_index]
        self._render_template_cards()
        self._persist_now()

    def _on_reset(self):
        """重置为默认配置"""
        from config import ConfigManager
        self._templates = [t.copy() for t in ConfigManager.DEFAULT_CONFIG['templates']]
        self._hotkey = ConfigManager.DEFAULT_CONFIG['settings']['hotkey']
        self._hotkey_entry.delete(0, "end")
        self._hotkey_entry.insert(0, self._hotkey)
        self._render_template_cards()
        self._persist_now()

    def _on_save(self):
        """保存配置"""
        # 读取快捷键
        hotkey_value = self._hotkey_entry.get().strip()
        if not hotkey_value:
            self._show_message("快捷键不能为空")
            return

        # 更新配置
        self.config.templates = self._templates
        self.config.hotkey = hotkey_value
        self.config.save()

        # 执行保存回调
        if self.on_save_callback:
            self.on_save_callback()

        self._on_close()

    def _on_close(self):
        """关闭窗口并清理定时器"""
        if self._update_timer and self.window:
            self.window.after_cancel(self._update_timer)
            self._update_timer = None

        if self.window:
            self.window.destroy()
            self.window = None

    def _show_message(self, msg):
        """显示简单提示消息"""
        if self.window:
            dialog = ctk.CTkToplevel(self.window)
            dialog.title("提示")
            dialog.geometry("280x120")
            dialog.resizable(False, False)
            dialog.transient(self.window)
            dialog.grab_set()
            dialog.configure(fg_color=Colors.BG_PRIMARY)
            dialog.attributes('-topmost', True)

            ctk.CTkLabel(
                dialog, text=msg, font=Fonts.BODY,
                text_color=Colors.TEXT_PRIMARY
            ).pack(expand=True, pady=(20, 10))

            ctk.CTkButton(
                dialog, text="确定", width=80,
                height=Sizes.BUTTON_HEIGHT,
                corner_radius=Sizes.CORNER_RADIUS_BUTTON,
                fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
                font=Fonts.BODY, command=dialog.destroy
            ).pack(pady=(0, 16))


class EditTemplateDialog:
    """模板编辑对话框（模态）"""

    def __init__(self, master, title="编辑模板", initial_name="", initial_format=""):
        """
        Args:
            master: 父窗口
            title: 对话框标题
            initial_name: 初始模板名称
            initial_format: 初始格式字符串
        """
        self.master = master
        self.title_text = title
        self.initial_name = initial_name
        self.initial_format = initial_format
        self.result = None  # 返回结果 {"name": ..., "format": ...} 或 None
        self._dialog = None
        self._preview_timer = None

    def show(self):
        """显示模态对话框（阻塞直到关闭）"""
        self._create_dialog()
        # 等待对话框关闭
        self.master.wait_window(self._dialog)

    def _create_dialog(self):
        """创建编辑对话框"""
        self._dialog = ctk.CTkToplevel(self.master)
        self._dialog.title(self.title_text)
        self._dialog.geometry("440x470")
        self._dialog.resizable(False, False)
        self._dialog.transient(self.master)
        self._dialog.grab_set()
        self._dialog.configure(fg_color=Colors.BG_PRIMARY)
        self._dialog.attributes('-topmost', True)

        main = ctk.CTkFrame(self._dialog, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=20)

        # 模板名称
        ctk.CTkLabel(
            main, text="模板名称:", font=Fonts.BODY,
            text_color=Colors.TEXT_PRIMARY, anchor="w"
        ).pack(fill="x", pady=(0, 4))

        self._name_entry = ctk.CTkEntry(
            main, height=34, font=Fonts.BODY,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            border_color=Colors.BORDER
        )
        self._name_entry.pack(fill="x", pady=(0, 12))
        if self.initial_name:
            self._name_entry.insert(0, self.initial_name)

        # 格式字符串
        ctk.CTkLabel(
            main, text="格式字符串:", font=Fonts.BODY,
            text_color=Colors.TEXT_PRIMARY, anchor="w"
        ).pack(fill="x", pady=(0, 4))

        self._format_entry = ctk.CTkEntry(
            main, height=34, font=Fonts.MONO,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            border_color=Colors.BORDER
        )
        self._format_entry.pack(fill="x", pady=(0, 12))
        if self.initial_format:
            self._format_entry.insert(0, self.initial_format)

        # 绑定输入事件 - 实时更新预览
        self._format_entry.bind('<KeyRelease>', lambda e: self._refresh_preview())

        # 实时预览区域
        preview_frame = ctk.CTkFrame(
            main, fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_RADIUS_CARD,
            border_width=1, border_color=Colors.BORDER
        )
        preview_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            preview_frame, text="实时预览", font=Fonts.SMALL,
            text_color=Colors.TEXT_HINT, anchor="w"
        ).pack(fill="x", padx=12, pady=(8, 2))

        self._preview_label = ctk.CTkLabel(
            preview_frame, text="", font=("Consolas", 12),
            text_color=Colors.ACCENT, anchor="w"
        )
        self._preview_label.pack(fill="x", padx=12, pady=(0, 10))

        # 初始预览
        self._refresh_preview()

        # 占位符说明
        help_text = (
            "{YYYY}年  {MM}月  {DD}日  "
            "{hh}时  {mm}分  {ss}秒  ##内容"
        )
        ctk.CTkLabel(
            main, text="可用占位符:", font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY, anchor="w"
        ).pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(
            main, text=help_text, font=Fonts.SMALL,
            text_color=Colors.TEXT_HINT, anchor="w"
        ).pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            main,
            text="提示: 用 ## 作为内容占位符（Windows 文件名场景兼容）",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_HINT, anchor="w"
        ).pack(fill="x", pady=(0, 16))

        # 按钮区域
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame, text="确定", width=92,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
            font=Fonts.BODY, command=self._on_confirm
        ).pack(side="right")

        ctk.CTkButton(
            btn_frame, text="取消", width=92,
            height=Sizes.BUTTON_HEIGHT,
            corner_radius=Sizes.CORNER_RADIUS_BUTTON,
            fg_color=Colors.BG_HOVER, hover_color=Colors.BG_ACTIVE,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.BODY, command=self._on_cancel
        ).pack(side="right", padx=(0, 8))

        # 启动定时刷新预览
        self._start_preview_timer()

        # 关闭事件
        self._dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _refresh_preview(self):
        """刷新预览文本"""
        fmt = self._format_entry.get()
        if fmt.strip():
            preview = TemplateEngine.preview_template(fmt)
            self._preview_label.configure(text=preview)
        else:
            self._preview_label.configure(text="（请输入格式字符串）")

    def _start_preview_timer(self):
        """每秒刷新预览（时间变化）"""
        if self._dialog and self._dialog.winfo_exists():
            self._refresh_preview()
            self._preview_timer = self._dialog.after(1000, self._start_preview_timer)

    def _on_confirm(self):
        """确定按钮 - 验证并返回结果"""
        name = self._name_entry.get().strip()
        fmt = self._format_entry.get().strip()

        if not name:
            self._show_error("模板名称不能为空")
            return
        if not fmt:
            self._show_error("格式字符串不能为空")
            return

        # 验证格式
        is_valid, err_msg = TemplateEngine.validate_format(fmt)
        if not is_valid:
            self._show_error(err_msg)
            return

        self.result = {"name": name, "format": fmt}
        self._close()

    def _on_cancel(self):
        """取消"""
        self.result = None
        self._close()

    def _close(self):
        """关闭对话框"""
        if self._preview_timer and self._dialog:
            self._dialog.after_cancel(self._preview_timer)
            self._preview_timer = None
        if self._dialog:
            self._dialog.grab_release()
            self._dialog.destroy()
            self._dialog = None

    def _show_error(self, msg):
        """在对话框内显示错误提示"""
        if self._dialog:
            error_win = ctk.CTkToplevel(self._dialog)
            error_win.title("错误")
            error_win.geometry("250x100")
            error_win.resizable(False, False)
            error_win.transient(self._dialog)
            error_win.grab_set()
            error_win.configure(fg_color=Colors.BG_PRIMARY)
            error_win.attributes('-topmost', True)

            ctk.CTkLabel(
                error_win, text=msg, font=Fonts.BODY,
                text_color=Colors.ERROR
            ).pack(expand=True, pady=(16, 8))

            ctk.CTkButton(
                error_win, text="确定", width=80,
                height=Sizes.BUTTON_HEIGHT,
                corner_radius=Sizes.CORNER_RADIUS_BUTTON,
                fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
                font=Fonts.BODY, command=error_win.destroy
            ).pack(pady=(0, 12))


def show_about_dialog(master):
    """显示关于对话框

    Args:
        master: 父窗口
    """
    dialog = ctk.CTkToplevel(master)
    dialog.title("关于")
    dialog.geometry("320x240")
    dialog.resizable(False, False)
    dialog.configure(fg_color=Colors.BG_PRIMARY)
    dialog.attributes('-topmost', True)

    if master:
        dialog.transient(master)

    # 软件名
    ctk.CTkLabel(
        dialog, text="TimestampTool", font=Fonts.TITLE,
        text_color=Colors.TEXT_PRIMARY
    ).pack(pady=(28, 4))

    # 版本号（从 __version__.py 统一读取）
    from __version__ import version_string, __author__
    ctk.CTkLabel(
        dialog, text=version_string(), font=Fonts.BODY,
        text_color=Colors.TEXT_SECONDARY
    ).pack(pady=(0, 12))

    # 功能说明
    desc = "快捷时间戳输入工具\n一键插入格式化时间戳到任意位置"
    ctk.CTkLabel(
        dialog, text=desc, font=Fonts.BODY,
        text_color=Colors.TEXT_SECONDARY, justify="center"
    ).pack(pady=(0, 8))

    # 作者
    ctk.CTkLabel(
        dialog, text=f"Author: {__author__}", font=Fonts.SMALL,
        text_color=Colors.TEXT_HINT
    ).pack(pady=(0, 16))

    # 关闭按钮
    ctk.CTkButton(
        dialog, text="确定", width=92,
        height=Sizes.BUTTON_HEIGHT,
        corner_radius=Sizes.CORNER_RADIUS_BUTTON,
        fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
        font=Fonts.BODY, command=dialog.destroy
    ).pack()
