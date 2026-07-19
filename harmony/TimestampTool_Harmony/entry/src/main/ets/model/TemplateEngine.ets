/**
 * TimestampTool 模板引擎 - 鸿蒙版
 *
 * 将模板中的时间占位符替换为实际时间值，保留 ## 内容占位符供用户填写。
 * 占位符说明：
 *   {YYYY} 四位年份  {MM} 两位月  {DD} 两位日
 *   {hh} 两位时(24h)  {mm} 两位分  {ss} 两位秒
 *   ## 内容占位符（保留不替换，注入后会被选中供用户直接输入）
 */

export interface TemplateItem {
  name: string;
  format: string;
}

export class TemplateEngine {
  // 内容占位符（优先识别 ##，兼容旧版 **）
  static readonly CONTENT_PLACEHOLDERS: string[] = ['##', '**'];

  /**
   * 格式化模板：替换时间占位符，保留内容占位符
   */
  static formatTemplate(formatStr: string, dt?: Date): string {
    const now = dt ?? new Date();
    let result = formatStr;

    result = result.replace(/\{YYYY\}/g, String(now.getFullYear()));
    result = result.replace(/\{MM\}/g, TemplateEngine.pad2(now.getMonth() + 1));
    result = result.replace(/\{DD\}/g, TemplateEngine.pad2(now.getDate()));
    result = result.replace(/\{hh\}/g, TemplateEngine.pad2(now.getHours()));
    result = result.replace(/\{mm\}/g, TemplateEngine.pad2(now.getMinutes()));
    result = result.replace(/\{ss\}/g, TemplateEngine.pad2(now.getSeconds()));

    return result;
  }

  /**
   * 预览模板效果（使用当前时间）
   */
  static previewTemplate(formatStr: string): string {
    return TemplateEngine.formatTemplate(formatStr);
  }

  /**
   * 在文本中定位内容占位符
   * @returns [占位符字符串, 位置索引] 或 undefined
   */
  static findContentPlaceholder(text: string): [string, number] | undefined {
    for (const ph of TemplateEngine.CONTENT_PLACEHOLDERS) {
      const idx = text.indexOf(ph);
      if (idx >= 0) {
        return [ph, idx];
      }
    }
    return undefined;
  }

  /**
   * 验证模板格式是否有效
   */
  static validateFormat(formatStr: string): { valid: boolean; error: string } {
    if (!formatStr || !formatStr.trim()) {
      return { valid: false, error: '格式字符串不能为空' };
    }

    const hasTime = /\{(YYYY|MM|DD|hh|mm|ss)\}/.test(formatStr);
    const hasContent = TemplateEngine.CONTENT_PLACEHOLDERS.some(ph => formatStr.includes(ph));

    if (!hasTime && !hasContent) {
      return { valid: false, error: '格式中至少需要一个时间占位符或内容占位符(##)' };
    }

    return { valid: true, error: '' };
  }

  /**
   * 获取默认模板列表
   */
  static getDefaultTemplates(): TemplateItem[] {
    return [
      { name: '日期_内容_署名', format: '{YYYY}_{MM}_{DD}_##_Sampson' },
      { name: '内容_日期时间', format: '##_{YYYY}{MM}{DD}_{hh}{mm}' },
      { name: '日期时间_内容', format: '{YYYY}{MM}{DD}{hh}{mm}_##' },
    ];
  }

  private static pad2(n: number): string {
    return n < 10 ? '0' + n : String(n);
  }
}
