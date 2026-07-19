# 变更日志

本项目所有值得关注的变更都会记录在此文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 约定，
版本号遵循 [SemVer 语义化版本](https://semver.org/lang/zh-CN/) 规范。

## 变更类型说明

- **Added（新增）** —— 新功能
- **Changed（变更）** —— 现有功能的改动
- **Deprecated（废弃）** —— 即将移除的功能
- **Removed（移除）** —— 已移除的功能
- **Fixed（修复）** —— bug 修复
- **Security（安全）** —— 安全相关的变更

---

## [Unreleased]

### Added（新增）
- **浮窗多列布局**：新配置项 `settings.menu_columns`（默认 1）支持每行 1/2/3 张模板卡片
- 设置窗口"偏好设置"新增"浮窗每行显示"下拉选项 + **实时布局预告**（例：`共 5 个模板 → 3 行 × 2 列`）
- 每张卡片固定 `MENU_CARD_WIDTH = 320`px，窗口总宽随列数线性增长，可读性一致

### Changed（变更）
- `_create_menu_item` 重构为 `_build_menu_item`：只创建卡片不 pack，由 caller 决定布局位置（为多列布局做基础）
- `_compute_container_height` 参数从 `n_items` 改为 `n_rows`（多列场景下 rows ≠ items）
- 设置窗口高度 580 → 620，容纳新增的一行控件

### Fixed（修复）
- **浮窗底部第二行提示被裁剪**：`_compute_container_height` 里 `hint_area` 从 55 加到 68（两行 SMALL 字体加上 pack pady 实测约 60），buffer 从 4 加到 10 冗余

---

## [1.0.0] - 2026-07-19

首个正式版本。

### Added（新增）
- 全局快捷键 `Ctrl+Shift+Z` 呼出模板选择浮窗（可自定义）
- Fluent 风格双行卡片式浮窗菜单（模板名 + 实时时间戳预览）
- 支持时间占位符 `{YYYY}/{MM}/{DD}/{hh}/{mm}/{ss}` 和内容占位符 `##`
- 剪贴板注入 + 自动选中 `##` 供用户直接输入内容
- 系统托盘图标（右键菜单：设置 / 关于 / 退出）
- 设置窗口：模板管理（增删改）+ 快捷键配置 + 偏好设置
- **开机自启**：通过注册表 `HKCU\...\Run` 实现，可在偏好设置里开关
- 模板增删改后**立即持久化**，无需点"保存"按钮
- 设置窗口标题显示 `模板管理 (共 N 个)`，实时反映模板数量
- 浮窗底部两行提示：操作说明 + `共 N 个模板 · 选中后自动粘贴，## 处会被选中`
- 单文件 `--onefile` 打包（59 MB），拷贝 `exe` 即可分发运行

### Changed（变更）
- 默认快捷键 `Ctrl+Shift+T` → `Ctrl+Shift+Z`（避免与 IDE "打开最近关闭的标签页" 冲突）
- 内容占位符 `**` → `##`（避免 Windows 文件名非法字符 `*` 被过滤）
- 配置文件位置：`exe 同目录 / config.json` → `%APPDATA%\TimestampTool\config.json`
  - 用户看不到"神秘配置文件"，发 exe 给别人时目录纯净
- 浮窗字体升级到 Fluent 风格双行卡片布局（原单行拥挤 → 现代分层）
- 托盘图标从单一 16×16 蓝底 T 字 → 多尺寸 ICO（16/24/32/48/64/128/256）
  - 蓝色渐变圆角背景 + 白色 T + 右下角小时钟点缀

### Fixed（修复）
- **焦点丢失**：在文件重命名等编辑场景按快捷键，编辑态不再被打断（`WS_EX_NOACTIVATE` + `RegisterHotKey` 独占 1-9 / ESC）
- **占位符被过滤**：`**` 在 Windows 文件名场景会被过滤导致选中位置错乱 → 改用 `##`
- **按钮文字裁剪**：设置窗口和编辑对话框的中文按钮"取消/确定/保存"曾因宽度不足显示不全
- **浮窗菜单显示不全**：`pack_propagate(False)` 锁死了 container 高度，导致模板超过 4 个时被裁 → 根据实际数量动态计算容器高度
- **新模板不生效**：`_persist_now` 中 templates 和 hotkey 保存耦合在同一 try/except，一步出错导致 templates 未 save → 拆分为独立步骤
- **打包内嵌配置**：迁移旧 `**` 模板到 `##`（自动升级），旧 `ctrl+shift+t` 到 `ctrl+shift+z`

### Removed（移除）
- `ahk_version/`：早期 AutoHotkey v2 版本已归档，Python 版本为唯一维护分支

---

<!-- 
更新此文件时的规范：
1. 每次发布前，把 [Unreleased] 部分的条目移到新的版本节
2. 新版本节格式：## [X.Y.Z] - YYYY-MM-DD
3. 分类顺序：Added → Changed → Deprecated → Removed → Fixed → Security
4. 每条改动一行，用简洁的祈使语气（不要"我"）
-->
