#Requires AutoHotkey v2.0

; ============================================================
; 设置窗口模块
; 提供模板管理界面、快捷键设置、关于对话框
; ============================================================

; 模块级变量
global settingsGui := ""
global settingsLV := ""
global settingsHotkey := ""
global settingsTemplates := []
global settingsHotkeyStr := ""
global editGui := ""
global editNameCtrl := ""
global editFormatCtrl := ""
global editPreviewCtrl := ""
global editMode := ""        ; "add" 或 "edit"
global editRowIndex := 0
global previewTimer := 0

; ============================================================
; 对外接口
; ============================================================

/**
 * 显示主设置窗口（供 main.ahk 托盘菜单调用）
 */
ShowSettings() {
    global settingsGui, settingsLV, settingsHotkey
    global settingsTemplates, settingsHotkeyStr

    ; 如果窗口已存在，激活它
    if (settingsGui != "") {
        try {
            settingsGui.Show()
            return
        } catch {
            settingsGui := ""
        }
    }

    ; 从当前配置加载数据副本
    config := LoadConfig()
    settingsTemplates := []
    for index, tmpl in config["templates"] {
        t := Map()
        t["name"] := tmpl["name"]
        t["format"] := tmpl["format"]
        settingsTemplates.Push(t)
    }
    settingsHotkeyStr := config["hotkey"]

    ; 创建主设置窗口
    settingsGui := Gui("+MinimizeBox", "TimestampTool 设置")
    settingsGui.OnEvent("Close", OnSettingsClose)
    settingsGui.SetFont("s9", "Microsoft YaHei UI")

    ; ---- 模板列表分组 ----
    settingsGui.Add("GroupBox", "x10 y10 w480 h240", "模板列表")

    ; ListView 控件
    settingsLV := settingsGui.Add("ListView", "x20 y30 w370 h210 Grid", ["序号", "名称", "格式", "预览"])
    settingsLV.ModifyCol(1, 40)   ; 序号列宽
    settingsLV.ModifyCol(2, 100)  ; 名称列宽
    settingsLV.ModifyCol(3, 120)  ; 格式列宽
    settingsLV.ModifyCol(4, 100)  ; 预览列宽

    ; 填充列表数据
    RefreshTemplateList()

    ; 右侧操作按钮
    btnAdd := settingsGui.Add("Button", "x400 y35 w80 h28", "添加(&A)")
    btnAdd.OnEvent("Click", OnBtnAdd)

    btnEdit := settingsGui.Add("Button", "x400 y70 w80 h28", "编辑(&E)")
    btnEdit.OnEvent("Click", OnBtnEdit)

    btnDelete := settingsGui.Add("Button", "x400 y105 w80 h28", "删除(&D)")
    btnDelete.OnEvent("Click", OnBtnDelete)

    btnUp := settingsGui.Add("Button", "x400 y150 w80 h28", "上移(&U)")
    btnUp.OnEvent("Click", OnBtnMoveUp)

    btnDown := settingsGui.Add("Button", "x400 y185 w80 h28", "下移(&W)")
    btnDown.OnEvent("Click", OnBtnMoveDown)

    ; ---- 快捷键设置分组 ----
    settingsGui.Add("GroupBox", "x10 y260 w480 h60", "快捷键设置")
    settingsGui.Add("Text", "x20 y283 w80 h22 +0x200", "触发快捷键：")
    settingsHotkey := settingsGui.Add("Hotkey", "x105 y282 w150 h22")
    settingsHotkey.Value := settingsHotkeyStr
    settingsGui.Add("Text", "x265 y283 w220 h22 +0x200", "（默认：Ctrl+Shift+T）")

    ; ---- 底部按钮 ----
    btnSave := settingsGui.Add("Button", "x130 y335 w90 h30", "保存(&S)")
    btnSave.OnEvent("Click", OnBtnSave)

    btnCancel := settingsGui.Add("Button", "x235 y335 w90 h30", "取消(&C)")
    btnCancel.OnEvent("Click", OnBtnCancel)

    btnReset := settingsGui.Add("Button", "x340 y335 w90 h30", "重置默认(&R)")
    btnReset.OnEvent("Click", OnBtnReset)

    ; 显示窗口居中
    settingsGui.Show("w500 h380")

    ; 启动预览刷新定时器（每秒刷新列表中的预览列）
    SetTimer(UpdateListPreview, 1000)
}

/**
 * 显示关于对话框
 */
ShowAboutDialog() {
    aboutText := "TimestampTool v20260716`n`n"
        . "快捷时间戳输入工具`n`n"
        . "作者：Sampson`n`n"
        . "功能说明：`n"
        . "通过快捷键快速输入带时间戳的文件名或文本，`n"
        . "支持自定义模板格式，满足多种场景需求。`n`n"
        . "可用占位符：`n"
        . "{YYYY} 四位年份  {MM} 月份  {DD} 日期`n"
        . "{hh} 小时  {mm} 分钟  {ss} 秒`n"
        . "** 内容占位符（用户输入替换）"
    MsgBox(aboutText, "关于 - TimestampTool", "64")
}

; ============================================================
; 列表操作
; ============================================================

/**
 * 刷新模板列表（重新填充 ListView 数据）
 */
RefreshTemplateList() {
    global settingsLV, settingsTemplates
    settingsLV.Delete()
    for index, tmpl in settingsTemplates {
        preview := PreviewTemplate(tmpl["format"])
        settingsLV.Add("", index, tmpl["name"], tmpl["format"], preview)
    }
}

/**
 * 定时刷新 ListView 预览列（每秒更新一次）
 */
UpdateListPreview() {
    global settingsLV, settingsTemplates, settingsGui
    ; 如果窗口已关闭，停止定时器
    if (settingsGui = "") {
        SetTimer(UpdateListPreview, 0)
        return
    }
    try {
        for index, tmpl in settingsTemplates {
            preview := PreviewTemplate(tmpl["format"])
            settingsLV.Modify(index, "", index, tmpl["name"], tmpl["format"], preview)
        }
    } catch {
        ; 窗口可能已销毁，停止定时器
        SetTimer(UpdateListPreview, 0)
    }
}

; ============================================================
; 按钮回调
; ============================================================

/**
 * "添加"按钮 - 打开空白模板编辑对话框
 */
OnBtnAdd(*) {
    global editMode, editRowIndex
    editMode := "add"
    editRowIndex := 0
    ShowEditDialog("", "")
}

/**
 * "编辑"按钮 - 打开填入选中项的模板编辑对话框
 */
OnBtnEdit(*) {
    global settingsLV, settingsTemplates, editMode, editRowIndex
    row := settingsLV.GetNext(0, "Focused")
    if (row = 0) {
        MsgBox("请先选择要编辑的模板。", "提示", "48")
        return
    }
    editMode := "edit"
    editRowIndex := row
    tmpl := settingsTemplates[row]
    ShowEditDialog(tmpl["name"], tmpl["format"])
}

/**
 * "删除"按钮 - 确认后删除选中模板
 */
OnBtnDelete(*) {
    global settingsLV, settingsTemplates
    row := settingsLV.GetNext(0, "Focused")
    if (row = 0) {
        MsgBox("请先选择要删除的模板。", "提示", "48")
        return
    }
    templateName := settingsTemplates[row]["name"]
    result := MsgBox("确认删除模板「" . templateName . "」？", "确认删除", "YesNo Icon!")
    if (result = "Yes") {
        settingsTemplates.RemoveAt(row)
        RefreshTemplateList()
    }
}

/**
 * "上移"按钮 - 将选中项上移一位
 */
OnBtnMoveUp(*) {
    global settingsLV, settingsTemplates
    row := settingsLV.GetNext(0, "Focused")
    if (row <= 1) {
        return  ; 已在顶部或未选中
    }
    ; 交换当前行与上一行
    temp := settingsTemplates[row - 1]
    settingsTemplates[row - 1] := settingsTemplates[row]
    settingsTemplates[row] := temp
    RefreshTemplateList()
    ; 重新选中移动后的行
    settingsLV.Modify(row - 1, "Focus Select")
}

/**
 * "下移"按钮 - 将选中项下移一位
 */
OnBtnMoveDown(*) {
    global settingsLV, settingsTemplates
    row := settingsLV.GetNext(0, "Focused")
    if (row = 0 || row >= settingsTemplates.Length) {
        return  ; 已在底部或未选中
    }
    ; 交换当前行与下一行
    temp := settingsTemplates[row + 1]
    settingsTemplates[row + 1] := settingsTemplates[row]
    settingsTemplates[row] := temp
    RefreshTemplateList()
    ; 重新选中移动后的行
    settingsLV.Modify(row + 1, "Focus Select")
}

/**
 * "保存"按钮 - 保存所有修改到INI并关闭窗口
 */
OnBtnSave(*) {
    global settingsTemplates, settingsHotkey, settingsGui

    ; 获取快捷键值
    hotkeyVal := settingsHotkey.Value
    if (hotkeyVal = "") {
        hotkeyVal := "^+t"  ; 如果为空，使用默认值
    }

    ; 验证：至少需要一个模板
    if (settingsTemplates.Length = 0) {
        MsgBox("至少需要保留一个模板。", "验证失败", "48")
        return
    }

    ; 保存配置
    SaveConfig(settingsTemplates, hotkeyVal)

    ; 重新加载全局配置
    global AppConfig := LoadConfig()

    ; 重新注册快捷键
    try {
        Hotkey(hotkeyVal, OnHotkeyPressed)
    } catch {
        ; 忽略快捷键注册失败
    }

    ; 关闭窗口
    CloseSettingsGui()
    TrayTip("设置已保存", "配置已更新并生效。", 1)
}

/**
 * "取消"按钮 - 放弃修改关闭窗口
 */
OnBtnCancel(*) {
    CloseSettingsGui()
}

/**
 * "重置默认"按钮 - 恢复内置默认模板
 */
OnBtnReset(*) {
    global settingsTemplates, settingsHotkey
    result := MsgBox("确认恢复为默认模板设置？`n当前修改将丢失。", "确认重置", "YesNo Icon!")
    if (result = "Yes") {
        settingsTemplates := GetDefaultTemplates()
        settingsHotkey.Value := "^+t"
        RefreshTemplateList()
    }
}

/**
 * 窗口关闭事件
 */
OnSettingsClose(*) {
    CloseSettingsGui()
}

/**
 * 关闭设置窗口并清理资源
 */
CloseSettingsGui() {
    global settingsGui
    SetTimer(UpdateListPreview, 0)  ; 停止预览定时器
    if (settingsGui != "") {
        settingsGui.Destroy()
        settingsGui := ""
    }
}

; ============================================================
; 模板编辑对话框
; ============================================================

/**
 * 显示模板编辑对话框
 * @param name 模板名称（编辑模式填入，添加模式为空）
 * @param format 格式字符串（编辑模式填入，添加模式为空）
 */
ShowEditDialog(name, format) {
    global editGui, editNameCtrl, editFormatCtrl, editPreviewCtrl
    global settingsGui

    ; 确定对话框标题
    title := (editMode = "add") ? "添加模板" : "编辑模板"

    ; 创建模态子窗口
    editGui := Gui("+Owner" . settingsGui.Hwnd . " +ToolWindow", title)
    editGui.OnEvent("Close", OnEditClose)
    editGui.SetFont("s9", "Microsoft YaHei UI")

    ; 模板名称
    editGui.Add("Text", "x15 y15 w70 h22 +0x200", "模板名称：")
    editNameCtrl := editGui.Add("Edit", "x90 y14 w250 h22", name)

    ; 格式字符串
    editGui.Add("Text", "x15 y48 w70 h22 +0x200", "格式字符串：")
    editFormatCtrl := editGui.Add("Edit", "x90 y47 w250 h22", format)
    editFormatCtrl.OnEvent("Change", OnFormatChange)

    ; 格式说明
    helpText := "可用占位符：{YYYY} 年  {MM} 月  {DD} 日  {hh} 时  {mm} 分  {ss} 秒  ** 内容"
    editGui.Add("Text", "x15 y78 w330 h20 cGray", helpText)

    ; 实时预览
    editGui.Add("Text", "x15 y106 w70 h22 +0x200", "实时预览：")
    editPreviewCtrl := editGui.Add("Edit", "x90 y105 w250 h22 ReadOnly")

    ; 立即更新一次预览
    UpdateEditPreview()

    ; 按钮
    btnOK := editGui.Add("Button", "x90 y142 w90 h28 Default", "确定(&O)")
    btnOK.OnEvent("Click", OnEditOK)

    btnEditCancel := editGui.Add("Button", "x200 y142 w90 h28", "取消(&C)")
    btnEditCancel.OnEvent("Click", OnEditCancel)

    ; 显示对话框
    editGui.Show("w360 h185")

    ; 启动编辑预览定时器
    SetTimer(UpdateEditPreview, 1000)
}

/**
 * 格式输入框内容变化时立即更新预览
 */
OnFormatChange(*) {
    UpdateEditPreview()
}

/**
 * 更新编辑对话框中的实时预览
 */
UpdateEditPreview() {
    global editFormatCtrl, editPreviewCtrl, editGui
    if (editGui = "") {
        SetTimer(UpdateEditPreview, 0)
        return
    }
    try {
        formatStr := editFormatCtrl.Value
        if (formatStr != "") {
            editPreviewCtrl.Value := PreviewTemplate(formatStr)
        } else {
            editPreviewCtrl.Value := ""
        }
    } catch {
        SetTimer(UpdateEditPreview, 0)
    }
}

/**
 * 编辑对话框"确定"按钮
 */
OnEditOK(*) {
    global editNameCtrl, editFormatCtrl, editMode, editRowIndex
    global settingsTemplates

    ; 获取输入值
    nameVal := Trim(editNameCtrl.Value)
    formatVal := Trim(editFormatCtrl.Value)

    ; 验证
    if (nameVal = "") {
        MsgBox("模板名称不能为空。", "验证失败", "48")
        return
    }
    if (formatVal = "") {
        MsgBox("格式字符串不能为空。", "验证失败", "48")
        return
    }

    ; 创建模板对象
    tmpl := Map()
    tmpl["name"] := nameVal
    tmpl["format"] := formatVal

    if (editMode = "add") {
        settingsTemplates.Push(tmpl)
    } else if (editMode = "edit" && editRowIndex > 0) {
        settingsTemplates[editRowIndex] := tmpl
    }

    ; 刷新列表
    RefreshTemplateList()

    ; 关闭编辑对话框
    CloseEditDialog()
}

/**
 * 编辑对话框"取消"按钮
 */
OnEditCancel(*) {
    CloseEditDialog()
}

/**
 * 编辑对话框关闭事件
 */
OnEditClose(*) {
    CloseEditDialog()
}

/**
 * 关闭编辑对话框并清理
 */
CloseEditDialog() {
    global editGui
    SetTimer(UpdateEditPreview, 0)
    if (editGui != "") {
        editGui.Destroy()
        editGui := ""
    }
}
