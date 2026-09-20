"""TimestampTool 样式令牌系统（Win11 明暗双主题）

设计原则：
- 所有颜色令牌为 CustomTkinter 元组形式 ("#浅色值", "#深色值")，
  控件按当前 appearance mode 自动取值，功能代码无需感知主题。
- 语义命名（BG_PRIMARY / ACCENT / TEXT_PRIMARY ...），改主题只改这里。
- 若需把令牌用于非 CustomTkinter 场景（原生 tkinter / Win32），
  用 Colors.resolve(token) 按当前主题取单一色值。
"""
import customtkinter as ctk


# ========== 色彩体系 ==========
class Colors:
    """语义化颜色令牌（light, dark）双值"""

    # -- 背景 --
    BG_PRIMARY = ("#F9F9F9", "#202020")      # 主窗口背景
    BG_CARD = ("#FFFFFF", "#2B2B2B")         # 卡片/菜单背景
    BG_HOVER = ("#E8E8E8", "#3A3A3A")        # 悬停背景
    BG_ACTIVE = ("#DCDCDC", "#454545")       # 按下状态

    # -- 强调色 --
    ACCENT = ("#0078D4", "#60CDFF")          # 强调色（Win11 light/dark 蓝）
    ACCENT_HOVER = ("#106EBE", "#4CC2FF")    # 强调色悬停
    ON_ACCENT = ("#FFFFFF", "#FFFFFF")       # 强调色上的文字

    # -- 文本 --
    TEXT_PRIMARY = ("#1A1A1A", "#FFFFFF")    # 主文本
    TEXT_SECONDARY = ("#666666", "#C8C8C8")  # 辅助文本（可操作性提示亦用此）
    TEXT_HINT = ("#8A8A8A", "#A0A0A0")       # 提示文本（仅装饰/次要信息）

    # -- 边框 --
    BORDER = ("#E0E0E0", "#3D3D3D")          # 边框色

    # -- 模拟阴影（逐层加深，暗色主题下取比 BG 更深的值） --
    SHADOW_L1 = ("#00000014", "#171717")     # 第 1 层（最外）
    SHADOW_L2 = ("#00000020", "#131313")     # 第 2 层
    SHADOW_L3 = ("#0000002C", "#0F0F0F")     # 第 3 层（最内，最深）

    # -- 功能色 --
    SUCCESS = ("#107C10", "#6CCB5F")         # 成功绿
    WARNING = ("#FF8C00", "#FCE100")         # 警告橙
    WARNING_HOVER = ("#E07800", "#E8CE00")   # 警告悬停
    ERROR = ("#D13438", "#FF99A4")           # 错误红
    ERROR_HOVER = ("#B02A2D", "#D97F89")     # 错误悬停

    # -- 开关按钮 --
    SWITCH_BUTTON = ("#FFFFFF", "#FFFFFF")           # 开关钮
    SWITCH_BUTTON_HOVER = ("#F0F0F0", "#C8C8C8")     # 开关钮悬停

    @staticmethod
    def resolve(token):
        """把 (light, dark) 令牌解析为当前 appearance mode 下的单一色值

        用于不支持主题元组的场景（原生 tkinter 控件、Win32 GDI 调用等）。
        非元组（已是单值）原样返回。
        """
        if not isinstance(token, tuple) or len(token) != 2:
            return token
        mode = str(ctk.get_appearance_mode()).lower()
        if mode in ("system", "auto"):
            # system/auto：按 Windows 注册表推断当前是否为深色
            is_dark = Colors._os_prefers_dark()
        else:
            is_dark = "dark" in mode
        return token[1] if is_dark else token[0]

    @staticmethod
    def _os_prefers_dark() -> bool:
        """读取 Windows 注册表判断系统是否处于深色模式"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            with key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return not bool(value)
        except Exception:
            return False


# ========== 字体 ==========
class Fonts:
    """字体配置（语义化条目）"""
    FAMILY = "Microsoft YaHei UI"
    FAMILY_FALLBACK = ("Microsoft YaHei UI", "Segoe UI", "Arial")

    TITLE = (FAMILY, 14, "bold")
    SUBTITLE = (FAMILY, 12, "bold")
    BODY = (FAMILY, 12)
    SMALL = (FAMILY, 10)
    MONO = ("Consolas", 11)

    # 菜单卡片内的模板名 / 数字徽标
    MENU_ITEM = (FAMILY, 13, "bold")
    BADGE = (FAMILY, 13, "bold")
    # 预览文字（小号 / 大号）
    PREVIEW_SMALL = ("Consolas", 10)
    PREVIEW_BIG = ("Consolas", 12)


# ========== 尺寸 ==========
class Sizes:
    """间距和圆角"""
    CORNER_RADIUS_CARD = 8
    CORNER_RADIUS_BUTTON = 6
    CORNER_RADIUS_MENU = 12

    PADDING_SMALL = 6
    PADDING_MEDIUM = 10
    PADDING_LARGE = 16

    MENU_ITEM_HEIGHT = 58
    MENU_MAX_WIDTH = 420
    MENU_PADDING = 8

    # 数字标记方块尺寸
    MENU_BADGE_SIZE = 28

    # 多列布局：每张卡片固定宽度，窗口总宽 = padding*2 + card_width*columns + gap*(columns-1)
    MENU_CARD_WIDTH = 320
    MENU_CARD_GAP = 8
    MENU_HORIZONTAL_PADDING = 8

    BUTTON_HEIGHT = 36
    BUTTON_WIDTH = 80

    # 浮窗阴影：逐层外扩阴影窗的边距（最外层 MENU_SHADOW_MARGIN，向内逐层递减 STEP）
    MENU_SHADOW_MARGIN = 12
    MENU_SHADOW_MARGIN_STEP = 4


# ========== 间距（8pt 网格） ==========
class Spacing:
    """8pt 网格间距体系（SPACE_XS 为半档例外，用于最紧凑处）"""
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 12
    SPACE_LG = 16
    SPACE_XL = 24
    SPACE_2XL = 32


# ========== 动效 ==========
class Motion:
    """动画时长与步进参数（本阶段仅定义，后续任务使用）"""
    MENU_FADE_IN_MS = 120      # 菜单淡入时长
    MENU_FADE_OUT_MS = 80      # 菜单淡出时长
    HOVER_FADE_MS = 60         # 悬停渐变时长
    FADE_STEPS = 3             # 渐变步数
    SHADOW_LAYERS = 3          # 模拟阴影层数
