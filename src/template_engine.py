"""TimestampTool 时间戳模板引擎"""
from datetime import datetime


class TemplateEngine:
    """时间戳模板格式化引擎
    
    支持的占位符：
        {YYYY} - 四位年份 (如 2026)
        {MM}   - 两位月份 (如 07)
        {DD}   - 两位日期 (如 16)
        {hh}   - 两位小时24制 (如 15)
        {mm}   - 两位分钟 (如 29)
        {ss}   - 两位秒 (如 05)
        ##     - 内容占位符（保留不替换，用户手动填写）
        **     - 内容占位符旧格式（向后兼容；文件名场景会被过滤，不推荐）
    
    为什么默认改为 ##：Windows 文件名不允许 * ? " < > | 反斜杠 正斜杠，
    使用 ## 可以在文件重命名场景下正常粘贴，占位符不被过滤。
    """
    
    # 时间占位符映射
    PLACEHOLDERS = {
        '{YYYY}': '%Y',
        '{MM}': '%m',
        '{DD}': '%d',
        '{hh}': '%H',
        '{mm}': '%M',
        '{ss}': '%S',
    }
    
    # 内容占位符（按优先级排序：优先识别 ##，再识别 ** 兼容）
    CONTENT_PLACEHOLDERS = ('##', '**')
    CONTENT_PLACEHOLDER_DEFAULT = '##'
    
    @classmethod
    def format_template(cls, format_str: str, dt: datetime = None) -> str:
        """将模板字符串中的时间占位符替换为实际时间值
        
        Args:
            format_str: 模板格式字符串，如 "{YYYY}_{MM}_{DD}_##_Sampson"
            dt: 指定时间，默认为当前时间
            
        Returns:
            格式化后的字符串，内容占位符 ## 或 ** 保持不变
        """
        if dt is None:
            dt = datetime.now()
        
        result = format_str
        for placeholder, strftime_code in cls.PLACEHOLDERS.items():
            if placeholder in result:
                result = result.replace(placeholder, dt.strftime(strftime_code))
        
        return result
    
    @classmethod
    def find_content_placeholder(cls, text: str):
        """在文本中定位内容占位符
        
        Returns:
            (placeholder_str, position) 或 None
            优先返回 ## 的位置；找不到再尝试 **
        """
        for ph in cls.CONTENT_PLACEHOLDERS:
            idx = text.find(ph)
            if idx >= 0:
                return (ph, idx)
        return None
    
    @classmethod
    def preview_template(cls, format_str: str) -> str:
        """预览模板效果（使用当前时间）
        
        与 format_template 功能相同，用于设置界面实时预览。
        """
        return cls.format_template(format_str)
    
    @classmethod
    def validate_format(cls, format_str: str) -> tuple:
        """验证模板格式是否有效
        
        Args:
            format_str: 要验证的格式字符串
            
        Returns:
            (is_valid: bool, error_message: str)
        """
        if not format_str or not format_str.strip():
            return False, "格式字符串不能为空"
        
        # 检查是否包含至少一个时间占位符或内容占位符
        has_time = any(p in format_str for p in cls.PLACEHOLDERS)
        has_content = any(p in format_str for p in cls.CONTENT_PLACEHOLDERS)
        
        if not has_time and not has_content:
            return False, "格式中至少需要一个时间占位符或内容占位符(##)"
        
        return True, ""
    
    @classmethod
    def get_placeholder_help(cls) -> str:
        """获取占位符使用说明文本"""
        return (
            "可用占位符：\n"
            "  {YYYY} → 年份 (如 2026)\n"
            "  {MM}   → 月份 (如 07)\n"
            "  {DD}   → 日期 (如 16)\n"
            "  {hh}   → 小时 (如 15)\n"
            "  {mm}   → 分钟 (如 29)\n"
            "  {ss}   → 秒   (如 05)\n"
            "  ##     → 内容占位符（推荐，文件名场景也可用）"
        )
