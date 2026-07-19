#Requires AutoHotkey v2.0

; ============================================================
; 快捷键管理模块
; 负责注册和注销全局快捷键
; ============================================================

/**
 * 注册全局快捷键
 * @param hotkeyStr 快捷键字符串，使用AHK原生格式（如 ^+t 表示 Ctrl+Shift+T）
 * @param callback 回调函数，需接受 ThisHotkey 参数
 * @returns {Boolean} 注册是否成功
 */
RegisterHotkey(hotkeyStr, callback) {
    try {
        Hotkey(hotkeyStr, callback, "On")
        return true
    } catch as e {
        MsgBox(
            "快捷键注册失败！`n`n"
            . "快捷键：" . hotkeyStr . "`n"
            . "错误信息：" . e.Message . "`n`n"
            . "请检查快捷键格式是否正确，或是否与其他程序冲突。",
            "TimestampTool - 快捷键错误",
            "16"
        )
        return false
    }
}

/**
 * 注销全局快捷键
 * @param hotkeyStr 要注销的快捷键字符串
 * @returns {Boolean} 注销是否成功
 */
UnregisterHotkey(hotkeyStr) {
    try {
        Hotkey(hotkeyStr, "Off")
        return true
    } catch as e {
        return false
    }
}
