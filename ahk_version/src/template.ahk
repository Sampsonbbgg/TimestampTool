#Requires AutoHotkey v2.0

; ============================================================
; 模板引擎模块
; 负责将模板格式字符串中的时间占位符替换为当前时间
; ============================================================

/**
 * 格式化模板字符串，将时间占位符替换为当前实际时间
 * @param formatStr 模板格式字符串，如 "{YYYY}_{MM}_{DD}_**_Sampson"
 * @returns {String} 替换后的字符串（** 保持不变，作为内容占位符）
 */
FormatTemplate(formatStr) {
    ; 获取当前时间各组件
    nowTime := A_Now

    ; 提取各时间部分
    yearStr := FormatTime(nowTime, "yyyy")
    monthStr := FormatTime(nowTime, "MM")
    dayStr := FormatTime(nowTime, "dd")
    hourStr := FormatTime(nowTime, "HH")
    minuteStr := FormatTime(nowTime, "mm")
    secondStr := FormatTime(nowTime, "ss")

    ; 依次替换所有时间占位符
    result := formatStr
    result := StrReplace(result, "{YYYY}", yearStr)
    result := StrReplace(result, "{MM}", monthStr)
    result := StrReplace(result, "{DD}", dayStr)
    result := StrReplace(result, "{hh}", hourStr)
    result := StrReplace(result, "{mm}", minuteStr)
    result := StrReplace(result, "{ss}", secondStr)

    ; ** 作为内容占位符保持不变，不做处理
    return result
}

/**
 * 预览模板（用于设置界面实时预览）
 * 功能与 FormatTemplate 相同，将时间占位符替换为当前时间
 * @param formatStr 模板格式字符串
 * @returns {String} 预览结果字符串
 */
PreviewTemplate(formatStr) {
    return FormatTemplate(formatStr)
}
