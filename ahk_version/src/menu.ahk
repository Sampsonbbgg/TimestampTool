#Requires AutoHotkey v2.0

; ============================================================
; 弹出浮窗菜单模块
; 在鼠标位置显示模板选择菜单，支持数字键/鼠标选择
; ============================================================

; 全局变量：菜单GUI实例和模板数据
global _menuGui := ""
global _menuTemplates := []
global _menuIsVisible := false

/**
 * 在鼠标位置弹出模板选择菜单
 * @param templates 模板数组（每个元素为 Map，含 "name" 和 "format"）
 */
ShowTemplateMenu(templates) {
    global _menuGui, _menuTemplates, _menuIsVisible

    ; 如果菜单已经打开，先关闭
    if (_menuIsVisible) {
        CloseMenu()
    }

    ; 保存模板数据供回调使用
    _menuTemplates := templates

    ; 如果没有模板，显示提示
    if (templates.Length = 0) {
        TrayTip("没有可用的模板", "请先在配置中添加模板", 2)
        return
    }

    ; 获取鼠标位置
    MouseGetPos(&mouseX, &mouseY)

    ; 创建浮窗 GUI（无标题栏、置顶、工具窗口样式）
    _menuGui := Gui("+AlwaysOnTop -Caption +ToolWindow +Border")
    _menuGui.BackColor := "FFFFFF"
    _menuGui.MarginX := 12
    _menuGui.MarginY := 10

    ; 设置字体
    _menuGui.SetFont("s10", "Microsoft YaHei UI")

    ; 添加标题
    _menuGui.SetFont("s9 cGray")
    _menuGui.Add("Text", "xm ym w400", "选择模板 (数字键快速选择, ESC关闭)")
    _menuGui.SetFont("s10 c000000")

    ; 添加分隔线
    _menuGui.Add("Text", "xm w400 0x10")  ; SS_ETCHEDHORZ

    ; 添加每个模板选项
    for index, template in templates {
        if (index > 9) {
            break  ; 最多支持9个模板（数字键1-9）
        }

        ; 生成实时预览
        preview := FormatTemplate(template["format"])

        ; 格式化显示文本：序号. 模板名称  →  实时预览
        displayText := index . ".  " . template["name"] . "    →    " . preview

        ; 添加可点击的文本控件
        ctrl := _menuGui.Add("Text", "xm w400 h24 +0x200 Section", displayText)

        ; 绑定鼠标点击事件（通过闭包传递索引）
        boundFunc := MenuItemClick.Bind(index)
        ctrl.OnEvent("Click", boundFunc)
    }

    ; 底部间距
    _menuGui.Add("Text", "xm h1", "")

    ; 计算菜单显示位置，确保不超出屏幕边界
    ; 先显示在屏幕外获取尺寸，再调整位置
    _menuGui.Show("x-9999 y-9999 AutoSize")

    ; 获取窗口尺寸
    _menuGui.GetPos(,, &menuW, &menuH)

    ; 获取屏幕工作区大小
    monitorArea := GetMonitorWorkArea(mouseX, mouseY)
    screenW := monitorArea[3]
    screenH := monitorArea[4]
    screenX := monitorArea[1]
    screenY := monitorArea[2]

    ; 计算最终位置（确保不超出屏幕）
    finalX := mouseX + 5
    finalY := mouseY + 5

    if (finalX + menuW > screenX + screenW) {
        finalX := mouseX - menuW - 5
    }
    if (finalY + menuH > screenY + screenH) {
        finalY := mouseY - menuH - 5
    }
    if (finalX < screenX) {
        finalX := screenX
    }
    if (finalY < screenY) {
        finalY := screenY
    }

    ; 移动到正确位置并显示
    _menuGui.Show("x" . finalX . " y" . finalY . " AutoSize")

    _menuIsVisible := true

    ; 注册 ESC 关闭事件
    _menuGui.OnEvent("Escape", (*) => CloseMenu())

    ; 注册失去焦点关闭事件（点击菜单外部）
    SetTimer(CheckMenuFocus, 100)

    ; 注册数字键快速选择（临时热键）
    RegisterMenuHotkeys(templates.Length)
}

/**
 * 获取鼠标所在显示器的工作区域
 * @param x 鼠标X坐标
 * @param y 鼠标Y坐标
 * @returns {Array} [左, 上, 宽, 高]
 */
GetMonitorWorkArea(x, y) {
    ; 遍历所有显示器找到鼠标所在的
    monCount := MonitorGetCount()
    Loop monCount {
        MonitorGetWorkArea(A_Index, &mLeft, &mTop, &mRight, &mBottom)
        if (x >= mLeft && x < mRight && y >= mTop && y < mBottom) {
            return [mLeft, mTop, mRight - mLeft, mBottom - mTop]
        }
    }
    ; 默认返回主显示器
    MonitorGetWorkArea(1, &mLeft, &mTop, &mRight, &mBottom)
    return [mLeft, mTop, mRight - mLeft, mBottom - mTop]
}

/**
 * 菜单项点击回调
 * @param index 点击的模板索引
 */
MenuItemClick(index, ctrl, *) {
    OnTemplateSelected(index)
}

/**
 * 模板选中处理
 * @param index 选中的模板索引（1-based）
 */
OnTemplateSelected(index) {
    global _menuTemplates

    ; 关闭菜单
    CloseMenu()

    ; 验证索引有效性
    if (index < 1 || index > _menuTemplates.Length) {
        return
    }

    ; 获取选中的模板并格式化
    template := _menuTemplates[index]
    formattedText := FormatTemplate(template["format"])

    ; 短暂延迟确保菜单完全关闭后再注入
    Sleep(50)

    ; 注入文本
    InjectText(formattedText)
}

/**
 * 关闭菜单
 */
CloseMenu() {
    global _menuGui, _menuIsVisible

    ; 注销数字键热键
    UnregisterMenuHotkeys()

    ; 停止焦点检测定时器
    SetTimer(CheckMenuFocus, 0)

    ; 销毁 GUI
    if (_menuGui != "") {
        try {
            _menuGui.Destroy()
        }
        _menuGui := ""
    }

    _menuIsVisible := false
}

/**
 * 检测菜单是否失去焦点（定时器回调）
 * 如果用户点击了菜单外部，自动关闭菜单
 */
CheckMenuFocus() {
    global _menuGui, _menuIsVisible

    if (!_menuIsVisible || _menuGui = "") {
        SetTimer(CheckMenuFocus, 0)
        return
    }

    try {
        ; 获取菜单窗口句柄
        menuHwnd := _menuGui.Hwnd

        ; 获取当前活动窗口
        activeHwnd := WinGetID("A")

        ; 如果活动窗口不是菜单窗口，关闭菜单
        if (activeHwnd != menuHwnd) {
            CloseMenu()
        }
    } catch {
        CloseMenu()
    }
}

/**
 * 注册菜单中的数字键快速选择热键
 * @param count 模板数量（最多9个）
 */
RegisterMenuHotkeys(count) {
    maxKeys := Min(count, 9)

    Loop maxKeys {
        BindMenuKey(A_Index)
    }
}

/**
 * 绑定单个数字键热键（通过函数参数捕获正确的索引值）
 * @param num 数字键对应的模板索引
 */
BindMenuKey(num) {
    try {
        fn := (*) => OnTemplateSelected(num)
        Hotkey(String(num), fn, "On")
    }
}

/**
 * 注销菜单中的数字键热键
 */
UnregisterMenuHotkeys() {
    Loop 9 {
        try {
            Hotkey(String(A_Index), "Off")
        }
    }
}
