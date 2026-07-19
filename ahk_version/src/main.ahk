#Requires AutoHotkey v2.0
#SingleInstance Force

; ============================================================
; TimestampTool - 时间戳快捷输入工具
; 版本：v20260716
; 功能：通过快捷键快速输入带时间戳的文件名/文本
; ============================================================

; 导入功能模块
#Include "config.ahk"
#Include "template.ahk"
#Include "hotkey.ahk"
#Include "menu.ahk"
#Include "clipboard.ahk"
#Include "settings.ahk"

; 后台常驻运行
Persistent()

; ============================================================
; 全局变量
; ============================================================
global AppVersion := "TimestampTool v20260716"
global AppConfig := Map()

; ============================================================
; 应用初始化
; ============================================================
InitApp()

/**
 * 应用初始化函数
 * 加载配置、设置托盘菜单、注册快捷键
 */
InitApp() {
    ; 加载配置文件
    global AppConfig := LoadConfig()

    ; 设置系统托盘
    SetupTray()

    ; 注册快捷键
    RegisterHotkeys()

    ; 显示启动提示
    TrayTip(AppVersion, "时间戳工具已启动，按 Ctrl+Shift+T 使用", 1)
}

/**
 * 设置系统托盘图标和右键菜单
 */
SetupTray() {
    ; 设置托盘图标提示文本
    A_IconTip := AppVersion

    ; 自定义托盘右键菜单
    trayMenu := A_TrayMenu
    trayMenu.Delete()  ; 清除默认菜单项

    trayMenu.Add("设置(&S)", MenuSettings)
    trayMenu.Add("关于(&A)", MenuAbout)
    trayMenu.Add()  ; 分隔线
    trayMenu.Add("退出(&X)", MenuExit)

    ; 设置默认菜单项（双击托盘图标触发）
    trayMenu.Default := "设置(&S)"
}

/**
 * 注册全局快捷键
 */
RegisterHotkeys() {
    ; 从配置获取快捷键，默认 Ctrl+Shift+T
    hotkeyStr := AppConfig["hotkey"]

    ; 使用 hotkey.ahk 模块注册快捷键
    if !RegisterHotkey(hotkeyStr, OnHotkeyPressed) {
        ; 如果配置的快捷键无效，使用默认快捷键
        RegisterHotkey("^+t", OnHotkeyPressed)
    }
}

/**
 * 快捷键触发回调
 * 加载最新模板配置并弹出模板选择菜单
 */
OnHotkeyPressed(thisHotkey) {
    ; 重新加载配置以获取最新模板
    global AppConfig := LoadConfig()

    ; 弹出模板选择菜单
    ShowTemplateMenu(AppConfig["templates"])
}

; ============================================================
; 菜单回调函数
; ============================================================

/**
 * "设置"菜单项回调
 */
MenuSettings(itemName, itemPos, myMenu) {
    ShowSettings()
}

/**
 * "关于"菜单项回调
 */
MenuAbout(itemName, itemPos, myMenu) {
    ShowAboutDialog()
}

/**
 * "退出"菜单项回调
 */
MenuExit(itemName, itemPos, myMenu) {
    ExitApp()
}
