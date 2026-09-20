"""TimestampTool 公共 UI 组件工厂

收敛 settings.py / popup_menu.py 中重复的"搭建样式"代码：
- Card:             语义化卡片容器（BG_CARD + 圆角 + 1px 边框）
- PrimaryButton /   统一尺寸与 hover 令牌的按钮工厂
- SecondaryButton /
- DestructiveButton
- show_alert:       统一模态消息弹窗（原 _show_message / _show_error）
- placeholder_help_text / content_placeholder_note:
                    占位符说明文本的单一来源

所有默认值均取自 ui.styles 令牌；kwargs 一律用 setdefault，
调用方可按需覆盖（不改变行为，只统一默认外观）。
"""
import sys
from pathlib import Path

# 确保 src 目录在导入路径中（与 ui 包内其他模块一致）
sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk
from template_engine import TemplateEngine
from ui.styles import Colors, Fonts, Sizes, Spacing


# ========== 卡片容器 ==========

def Card(parent, **kwargs):
    """语义化卡片容器：BG_CARD 底、卡片圆角、1px BORDER 边框

    对应原先手搭的 CTkFrame(fg_color=BG_CARD, corner_radius=CORNER_RADIUS_CARD,
    border_width=1, border_color=BORDER) 重复组合，允许 kwargs 覆盖。
    """
    kwargs.setdefault("fg_color", Colors.BG_CARD)
    kwargs.setdefault("corner_radius", Sizes.CORNER_RADIUS_CARD)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("border_color", Colors.BORDER)
    return ctk.CTkFrame(parent, **kwargs)


# ========== 按钮工厂 ==========

BUTTON_DEFAULT_WIDTH = 92  # 统一主按钮宽度（原代码 80/92 不一，收敛为 92）


def _make_button(parent, text, command, defaults, kwargs):
    for key, value in defaults.items():
        kwargs.setdefault(key, value)
    kwargs.setdefault("width", BUTTON_DEFAULT_WIDTH)
    kwargs.setdefault("height", Sizes.BUTTON_HEIGHT)
    kwargs.setdefault("corner_radius", Sizes.CORNER_RADIUS_BUTTON)
    kwargs.setdefault("font", Fonts.BODY)
    return ctk.CTkButton(parent, text=text, command=command, **kwargs)


def PrimaryButton(parent, text, command, **kwargs):
    """主操作按钮（ACCENT 底 + 白色文字，如"保存"/"确定"/"添加"）"""
    return _make_button(parent, text, command, {
        "fg_color": Colors.ACCENT,
        "hover_color": Colors.ACCENT_HOVER,
        "text_color": Colors.ON_ACCENT,
    }, kwargs)


def SecondaryButton(parent, text, command, **kwargs):
    """次级按钮（BG_HOVER 底 + 主文本色，即"取消"样式）"""
    return _make_button(parent, text, command, {
        "fg_color": Colors.BG_HOVER,
        "hover_color": Colors.BG_ACTIVE,
        "text_color": Colors.TEXT_PRIMARY,
    }, kwargs)


def DestructiveButton(parent, text, command, **kwargs):
    """危险操作按钮（ERROR 底，如"删除"）"""
    return _make_button(parent, text, command, {
        "fg_color": Colors.ERROR,
        "hover_color": Colors.ERROR_HOVER,
        "text_color": Colors.ON_ACCENT,
    }, kwargs)


# ========== 消息弹窗 ==========

ALERT_MIN_WIDTH = 280  # 弹窗最小宽度（与旧版固定宽度保持一致）


def show_alert(parent, message, title="提示", error=False):
    """统一模态消息弹窗

    Args:
        parent: 父窗口（弹窗 transient 于它并居中于它）
        message: 消息文本，支持多行（\\n 分行，高度自适应）
        title: 窗口标题
        error: True 时正文使用 ERROR 色（原 _show_error 的样式）
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.configure(fg_color=Colors.BG_PRIMARY)
    dialog.attributes('-topmost', True)

    ctk.CTkLabel(
        dialog, text=message, font=Fonts.BODY,
        text_color=(Colors.ERROR if error else Colors.TEXT_PRIMARY),
        justify="left",
    ).pack(expand=True, padx=Spacing.SPACE_XL, pady=(Spacing.SPACE_XL, Spacing.SPACE_MD))

    PrimaryButton(
        dialog, text="确定", command=dialog.destroy,
    ).pack(pady=(0, Spacing.SPACE_LG))

    # 尺寸自适应内容 + 居中于父窗口（先量出内容请求尺寸，再定几何）
    dialog.update_idletasks()
    width = max(ALERT_MIN_WIDTH, dialog.winfo_reqwidth() + Spacing.SPACE_2XL * 2)
    height = dialog.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    dialog.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    return dialog


# ========== 占位符说明（单一来源） ==========

def placeholder_help_text() -> str:
    """占位符完整说明文本——委托给 TemplateEngine.get_placeholder_help()

    TemplateEngine 是占位符语义的权威定义处（PLACEHOLDERS /
    CONTENT_PLACEHOLDERS 都在那里），说明文本亦由它提供，
    UI 侧只做展示，不再各自措辞。
    """
    return TemplateEngine.get_placeholder_help()


def content_placeholder_note(compact=False) -> str:
    """内容占位符 ## 的单句说明（浮窗底部 / 编辑弹窗提示行共用）

    与 placeholder_help_text() 同源措辞：统一为"## 处会被选中供输入"，
    两处显示按需截取——浮窗底部空间紧凑用 compact=True 去掉括号补充，
    编辑弹窗用完整版。
    """
    note = "## 处会被选中供输入"
    if not compact:
        note += "（Windows 文件名场景兼容）"
    return note
