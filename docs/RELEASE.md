# 发布流程 (Release Workflow)

本文档描述 TimestampTool **每次发布新版本时的标准流程**。

## AI 协作约定（重要）

**AI 助手协作时必须遵守以下规则**：

1. **不由用户主动提出发布**——用户不需要自己想着"我该发布新版本了"
2. **AI 在必要时主动询问**——每次实质性代码改动完成、打包成功后，AI 应**主动使用询问工具**（如 `AskUserQuestion`）确认用户是否要执行以下动作：
   - **[1] 仅本地提交**：`git commit -m "<type>: <描述>"` 保存到本地版本历史
   - **[2] 发布新版本**：`python scripts/release.py patch/minor/major` 一键完成 bump 版本号 + 更新 CHANGELOG + 归档 exe + git tag
   - **[3] 推送到 GitHub**：`git push && git push --tags` 同步到远程仓库
   - **[4] 暂不发布**：只把改动放在工作区，稍后再决定
3. **AI 默认不执行 commit / tag / push**——这些是重要动作，必须用户明确确认
4. **涵盖所有触发场景**：修 bug、加功能、UI 改造、任何触发 `build.py` 打包的操作之后

**这条约定的动机**：用户希望"发布"这个动作由 AI 触发，避免自己需要频繁记住"这次要不要发布""版本号该 bump 哪一位""要不要写 changelog"等琐事——把开发工程细节交给 AI，用户只做"是/否"决策。

---

## 核心原则

1. **每次发布 = 一个 SemVer 版本号 + 一个 Git tag + 一份 CHANGELOG 条目 + 一个归档 exe**
2. **版本号只在 `src/__version__.py` 一处修改**，其他地方都从这里读取
3. **发布前必须更新 `CHANGELOG.md`**，让用户和未来的自己知道改了什么

## 版本号选择（SemVer 决策树）

假设当前版本是 `1.2.3`，下个版本号取决于本次改动：

```
本次改动是……                     →  下一版本号
─────────────────────────────────────────────────
只修 bug，不加新功能                →  1.2.4  (PATCH)
新增功能，向后兼容                   →  1.3.0  (MINOR)  
破坏性变更（配置格式不兼容等）        →  2.0.0  (MAJOR)
```

## 标准发布流程（一键脚本方式）

一条命令搞定：

```powershell
python scripts/release.py patch   # 1.0.0 → 1.0.1
python scripts/release.py minor   # 1.0.0 → 1.1.0
python scripts/release.py major   # 1.0.0 → 2.0.0
python scripts/release.py 1.5.2   # 直接指定版本号
```

脚本会自动完成：

1. 检查工作区是否干净（未提交的改动会终止）
2. Bump `src/__version__.py` 的版本号和构建日期
3. 打开 `CHANGELOG.md` 让你编辑本次变更（把 `[Unreleased]` 内容整理到新版本节）
4. 执行 `python build.py` 打包
5. 复制 `dist/TimestampTool.exe` 到 `releases/v{VERSION}/TimestampTool.exe`
6. `git add . && git commit -m "chore: release v{VERSION}"`
7. `git tag v{VERSION}`
8. 提示你手动执行 `git push && git push --tags` 推送到 GitHub

## 手动发布流程（不用脚本时的备份方案）

按顺序：

### 1. 决定版本号
根据本次改动类型（PATCH / MINOR / MAJOR）决定新版本号。

### 2. 修改版本号
```python
# src/__version__.py
__version__ = "1.1.0"      # ← 修改这里
__build_date__ = "2026-08-15"  # ← 也改这里
```

### 3. 更新 CHANGELOG.md
把 `[Unreleased]` 部分的内容移到新版本节：

```markdown
## [Unreleased]

_（正在开发中的功能）_

---

## [1.1.0] - 2026-08-15

### Added
- 新功能 A

### Fixed
- 修复 bug B
```

### 4. 打包
```powershell
python build.py
```

### 5. 归档 exe
```powershell
$v = "v1.1.0"
New-Item -ItemType Directory -Path "releases\$v" -Force
Copy-Item "dist\TimestampTool.exe" "releases\$v\TimestampTool.exe"
```

### 6. Git 提交 + 打 Tag
```powershell
git add .
git commit -m "chore: release v1.1.0"
git tag v1.1.0
```

### 7. 推送到 GitHub
```powershell
git push
git push --tags
```

### 8. 在 GitHub 创建 Release（可选）
访问 `https://github.com/<username>/<repo>/releases/new`：
- Tag：选择 `v1.1.0`
- Title：`v1.1.0 - 简短标题`
- Description：从 CHANGELOG.md 复制本版本条目
- Assets：上传 `releases/v1.1.0/TimestampTool.exe`

## Git 提交规范（Conventional Commits）

每次 `git commit` 用统一前缀，方便未来生成 changelog 和检索历史：

| 前缀 | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(hotkey): 添加自定义快捷键设置` |
| `fix` | bug 修复 | `fix(popup): 修复第 5 个模板被裁剪` |
| `docs` | 文档变更 | `docs(readme): 补充快速上手指南` |
| `style` | 代码格式（不影响功能） | `style: 统一缩进为 4 空格` |
| `refactor` | 重构（不新增功能，不修 bug） | `refactor(config): 提取路径工具到 paths.py` |
| `perf` | 性能优化 | `perf(popup): 减少 update_idletasks 调用` |
| `test` | 测试相关 | `test: 添加模板引擎单元测试` |
| `chore` | 杂项（打包、版本号、依赖等） | `chore: release v1.2.0` |
| `build` | 构建系统变更 | `build: PyInstaller 迁移到 6.19` |

**格式**：`<type>(<scope>): <subject>`，`scope` 可省略。

## 分支策略（个人开发者简化版）

- `main` 分支 = 稳定发布线，每个 tag 对应一个可用版本
- 大功能可以开 `feature/xxx` 分支单独开发，完成后合回 main
- 紧急修复可以直接在 main 上改（个人项目不需要 PR 流程）

## 回滚到历史版本

```powershell
# 列出所有历史版本
git tag -l

# 临时查看 v1.0.0 时的代码
git checkout v1.0.0

# 回到最新
git checkout main

# 从历史版本创建修复分支（罕见）
git checkout -b hotfix/v1.0.1 v1.0.0
```

## 快速参考

| 场景 | 命令 |
|------|------|
| 日常开发提交 | `git commit -m "feat: 添加 XXX"` |
| 一键发布新版本 | `python scripts/release.py patch` |
| 推送到 GitHub | `git push && git push --tags` |
| 查看变更历史 | `git log --oneline` |
| 查看某版本改动 | `git show v1.0.0` |
| 对比两版本 | `git diff v1.0.0 v1.1.0` |
