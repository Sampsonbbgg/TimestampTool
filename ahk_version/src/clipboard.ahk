#Requires AutoHotkey v2.0

; ============================================================
; 剪贴板和文本注入模块
; 负责保存/恢复剪贴板内容，以及通过模拟粘贴注入文本
; ============================================================

; 全局变量：保存的剪贴板内容
global _savedClipboard := ""
global _savedClipboardIsText := true

/**
 * 保存当前剪贴板内容到全局变量
 */
SaveClipboard() {
    global _savedClipboard, _savedClipboardIsText
    try {
        ; 保存剪贴板全部内容（包括非文本格式）
        _savedClipboard := ClipboardAll()
        _savedClipboardIsText := false
    } catch {
        ; 如果ClipboardAll失败，至少保存文本内容
        _savedClipboard := A_Clipboard
        _savedClipboardIsText := true
    }
}

/**
 * 恢复之前保存的剪贴板内容
 */
RestoreClipboard() {
    global _savedClipboard, _savedClipboardIsText
    try {
        if (_savedClipboardIsText) {
            A_Clipboard := _savedClipboard
        } else {
            A_Clipboard := _savedClipboard
        }
    } catch {
        ; 恢复失败时清空剪贴板，避免残留敏感数据
        A_Clipboard := ""
    }
    ; 释放保存的内容
    _savedClipboard := ""
}

/**
 * 注入文本到当前焦点窗口
 * 通过剪贴板+模拟Ctrl+V粘贴实现
 * @param text 要注入的文本内容
 */
InjectText(text) {
    ; 1. 保存旧的剪贴板内容
    SaveClipboard()

    ; 2. 将目标文本写入剪贴板
    A_Clipboard := text

    ; 3. 等待剪贴板就绪
    Sleep(50)

    ; 4. 模拟粘贴操作
    SendInput("^v")

    ; 5. 等待粘贴完成
    Sleep(100)

    ; 6. 恢复旧的剪贴板内容
    RestoreClipboard()

    ; 7. 如果文本包含占位符 **，尝试选中它
    SelectPlaceholder(text)
}

/**
 * 选中注入文本中的占位符 **
 * 如果文本包含 **，则通过模拟按键选中该占位符，方便用户直接输入替换内容
 * @param text 已注入的文本内容
 */
SelectPlaceholder(text) {
    ; 查找 ** 在文本中的位置
    placeholderPos := InStr(text, "**")

    ; 如果没有占位符，直接返回
    if (placeholderPos = 0) {
        return
    }

    ; 计算文本总长度和占位符之后的字符数
    textLen := StrLen(text)
    charsAfterPlaceholder := textLen - placeholderPos - 1  ; ** 长度为2，所以减去 (pos+2-1)=pos+1

    ; 先移动光标到文本起始位置（通过Home键或左移到开头再精确定位）
    ; 方案：从当前光标位置（在文本末尾）左移到占位符末尾，再选中占位符
    ; 当前光标在文本末尾，需要左移 charsAfterPlaceholder 次到达 ** 之后
    if (charsAfterPlaceholder > 0) {
        SendInput("{Left " . charsAfterPlaceholder . "}")
    }

    ; 再用 Shift+Left 选中 ** （2个字符）
    Sleep(30)
    SendInput("+{Left 2}")
}
