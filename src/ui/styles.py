"""TimestampTool Win11 风格样式定义"""


# ========== 色彩体系 ==========
class Colors:
    """Windows 11 现代简约配色"""
    BG_PRIMARY = "#F9F9F9"      # 主窗口背景
    BG_CARD = "#FFFFFF"          # 卡片/菜单背景
    BG_HOVER = "#E8E8E8"         # 悬停背景
    BG_ACTIVE = "#DCDCDC"        # 按下状态

    ACCENT = "#0078D4"           # 强调色（Windows蓝）
    ACCENT_HOVER = "#106EBE"     # 强调色悬停

    TEXT_PRIMARY = "#1A1A1A"     # 主文本
    TEXT_SECONDARY = "#666666"   # 辅助文本
    TEXT_HINT = "#999999"        # 提示文本

    BORDER = "#E0E0E0"           # 边框色
    SHADOW = "#00000020"         # 阴影色（带透明度）

    SUCCESS = "#107C10"          # 成功绿
    WARNING = "#FF8C00"          # 警告橙
    ERROR = "#D13438"            # 错误红


# ========== 字体 ==========
class Fonts:
    """字体配置"""
    FAMILY = "Microsoft YaHei UI"
    FAMILY_FALLBACK = ("Microsoft YaHei UI", "Segoe UI", "Arial")

    TITLE = (FAMILY, 14, "bold")
    SUBTITLE = (FAMILY, 12, "bold")
    BODY = (FAMILY, 12)
    SMALL = (FAMILY, 10)
    MONO = ("Consolas", 11)


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
