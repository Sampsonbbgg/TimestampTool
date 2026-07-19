#Requires AutoHotkey v2.0

; ============================================================
; 配置管理模块
; 负责读取和保存 INI 配置文件（模板列表和快捷键设置）
; ============================================================

; 配置文件路径（相对于脚本目录的上级 config 文件夹）
global ConfigFilePath := A_ScriptDir . "\..\config\templates.ini"

/**
 * 加载配置文件
 * 读取 INI 文件中的模板和快捷键设置
 * @returns {Map} 包含 "templates"（数组）和 "hotkey"（字符串）的 Map
 */
LoadConfig() {
    config := Map()
    config["templates"] := []
    config["hotkey"] := "^+t"  ; 默认快捷键 Ctrl+Shift+T

    ; 如果配置文件不存在，使用默认模板并创建配置文件
    if !FileExist(ConfigFilePath) {
        config["templates"] := GetDefaultTemplates()
        SaveConfig(config["templates"], config["hotkey"])
        return config
    }

    ; 读取快捷键设置
    try {
        hotkeyVal := IniRead(ConfigFilePath, "Settings", "Hotkey", "^+t")
        config["hotkey"] := hotkeyVal
    } catch {
        config["hotkey"] := "^+t"
    }

    ; 读取模板列表
    templates := []
    templateIndex := 1

    Loop {
        section := "Template" . templateIndex

        ; 尝试读取模板名称，如果读取不到则结束循环
        try {
            nameVal := IniRead(ConfigFilePath, section, "Name", "")
        } catch {
            break
        }

        ; 如果名称为空，说明该模板节不存在，结束循环
        if (nameVal = "") {
            break
        }

        ; 读取模板格式
        try {
            formatVal := IniRead(ConfigFilePath, section, "Format", "")
        } catch {
            formatVal := ""
        }

        ; 如果格式不为空，添加到模板数组
        if (formatVal != "") {
            template := Map()
            template["name"] := nameVal
            template["format"] := formatVal
            templates.Push(template)
        }

        templateIndex++
    }

    ; 如果没有读取到任何模板，使用默认模板
    if (templates.Length = 0) {
        templates := GetDefaultTemplates()
        SaveConfig(templates, config["hotkey"])
    }

    config["templates"] := templates
    return config
}

/**
 * 保存配置到 INI 文件
 * @param templates 模板数组（每个元素为 Map，含 "name" 和 "format"）
 * @param hotkey 快捷键字符串
 */
SaveConfig(templates, hotkey) {
    ; 确保配置目录存在
    configDir := A_ScriptDir . "\..\config"
    if !DirExist(configDir) {
        DirCreate(configDir)
    }

    ; 如果配置文件已存在，先删除以重新写入
    if FileExist(ConfigFilePath) {
        FileDelete(ConfigFilePath)
    }

    ; 写入快捷键设置
    IniWrite(hotkey, ConfigFilePath, "Settings", "Hotkey")

    ; 写入各模板
    for index, template in templates {
        section := "Template" . index
        IniWrite(template["name"], ConfigFilePath, section, "Name")
        IniWrite(template["format"], ConfigFilePath, section, "Format")
    }
}

/**
 * 获取默认模板列表
 * 当配置文件不存在或损坏时使用
 * @returns {Array} 包含3个默认模板的数组
 */
GetDefaultTemplates() {
    templates := []

    ; 模板1：日期_内容_署名
    t1 := Map()
    t1["name"] := "日期_内容_署名"
    t1["format"] := "{YYYY}_{MM}_{DD}_**_Sampson"
    templates.Push(t1)

    ; 模板2：内容_日期时间
    t2 := Map()
    t2["name"] := "内容_日期时间"
    t2["format"] := "**_{YYYY}{MM}{DD}_{hh}{mm}"
    templates.Push(t2)

    ; 模板3：日期时间_内容
    t3 := Map()
    t3["name"] := "日期时间_内容"
    t3["format"] := "{YYYY}{MM}{DD}{hh}{mm}_**"
    templates.Push(t3)

    return templates
}
