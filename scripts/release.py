"""一键发布脚本 - TimestampTool Release Automation

用法：
    python scripts/release.py patch     # 1.0.0 → 1.0.1
    python scripts/release.py minor     # 1.0.0 → 1.1.0
    python scripts/release.py major     # 1.0.0 → 2.0.0
    python scripts/release.py 1.5.2     # 直接指定版本号
    python scripts/release.py --dry-run patch   # 预演，不实际执行

流程：
    1. 检查 git 工作区是否干净（有未提交改动就终止）
    2. Bump src/__version__.py 的版本号和构建日期
    3. 打开 CHANGELOG.md 让你编辑本次变更
    4. python build.py 打包
    5. 复制 dist/TimestampTool.exe 到 releases/v{VERSION}/
    6. git add . && git commit -m "chore: release v{VERSION}"
    7. git tag v{VERSION}
    8. 提示手动 git push --tags
"""
from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "src" / "__version__.py"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
BUILD_SCRIPT = PROJECT_ROOT / "build.py"
DIST_EXE = PROJECT_ROOT / "dist" / "TimestampTool.exe"
RELEASES_DIR = PROJECT_ROOT / "releases"


# ============ 颜色输出 ============
class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def info(msg: str) -> None:
    print(f"{C.BLUE}[INFO]{C.END} {msg}")


def ok(msg: str) -> None:
    print(f"{C.GREEN}[OK]{C.END} {msg}")


def warn(msg: str) -> None:
    print(f"{C.YELLOW}[WARN]{C.END} {msg}")


def err(msg: str) -> None:
    print(f"{C.RED}[ERR]{C.END} {msg}")


# ============ 版本号读写 ============

def read_current_version() -> str:
    """从 src/__version__.py 读取当前版本号"""
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError(f"无法从 {VERSION_FILE} 解析版本号")
    return match.group(1)


def write_version(new_version: str, new_date: str) -> None:
    """把新版本号和构建日期写回 src/__version__.py"""
    content = VERSION_FILE.read_text(encoding="utf-8")
    content = re.sub(
        r'^__version__\s*=\s*"[^"]+"',
        f'__version__ = "{new_version}"',
        content, count=1, flags=re.MULTILINE,
    )
    content = re.sub(
        r'^__build_date__\s*=\s*"[^"]+"',
        f'__build_date__ = "{new_date}"',
        content, count=1, flags=re.MULTILINE,
    )
    VERSION_FILE.write_text(content, encoding="utf-8")


def bump_version(current: str, bump_type: str) -> str:
    """根据 bump 类型计算新版本号

    - patch: 1.2.3 → 1.2.4
    - minor: 1.2.3 → 1.3.0
    - major: 1.2.3 → 2.0.0
    - 或者直接是 X.Y.Z 格式的完整版本号
    """
    # 完整版本号直接返回
    if re.match(r"^\d+\.\d+\.\d+$", bump_type):
        return bump_type

    parts = current.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"当前版本号 {current} 不符合 SemVer 格式")
    major, minor, patch = map(int, parts)

    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"未知的 bump 类型: {bump_type}")
    return f"{major}.{minor}.{patch}"


# ============ Git 操作 ============

def run(cmd: list[str], check: bool = True, capture: bool = False):
    """执行 shell 命令"""
    if capture:
        result = subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8"
        )
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if check and result.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd)}")
    return result


def git_is_clean() -> bool:
    """检查 git 工作区是否干净（没有未提交改动）"""
    result = run(["git", "status", "--porcelain"], capture=True)
    return not result.stdout.strip()


def git_is_repo() -> bool:
    """检查当前目录是否是 git 仓库"""
    try:
        run(["git", "rev-parse", "--git-dir"], capture=True, check=True)
        return True
    except (RuntimeError, FileNotFoundError):
        return False


# ============ CHANGELOG ============

def check_changelog_has_unreleased() -> bool:
    """检查 CHANGELOG.md 的 [Unreleased] 节是否有实质内容"""
    content = CHANGELOG_FILE.read_text(encoding="utf-8")
    match = re.search(
        r"##\s*\[Unreleased\](.*?)(?=^##\s*\[)",
        content, re.DOTALL | re.MULTILINE,
    )
    if not match:
        return False
    body = match.group(1).strip()
    # 去掉占位说明和分隔线
    body_lines = [
        l for l in body.split("\n")
        if l.strip() and not l.strip().startswith("_") and l.strip() != "---"
    ]
    return len(body_lines) > 0


def promote_unreleased_to_version(new_version: str, new_date: str) -> None:
    """把 CHANGELOG.md 里 [Unreleased] 的内容移动到新版本节"""
    content = CHANGELOG_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(##\s*\[Unreleased\]\s*\n)(.*?)(\n---\n\n)",
        re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        warn("CHANGELOG.md 找不到 [Unreleased] 节，跳过自动提升")
        return

    unreleased_body = match.group(2).strip()
    if not unreleased_body or unreleased_body.startswith("_"):
        warn("CHANGELOG.md 的 [Unreleased] 节为空，跳过自动提升")
        return

    new_section = (
        f"## [Unreleased]\n\n"
        f"_（正在开发中的功能，发布前会分配版本号并移到下方）_\n\n"
        f"---\n\n"
        f"## [{new_version}] - {new_date}\n\n"
        f"{unreleased_body}\n\n"
        f"---\n\n"
    )
    content = pattern.sub(new_section, content, count=1)
    CHANGELOG_FILE.write_text(content, encoding="utf-8")
    ok(f"已把 [Unreleased] 内容移动到 [{new_version}] 节")


# ============ 主流程 ============

def main() -> int:
    parser = argparse.ArgumentParser(description="TimestampTool 一键发布脚本")
    parser.add_argument(
        "bump",
        help="版本号 bump 类型：patch / minor / major，或直接指定 X.Y.Z",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="预演模式：只显示会执行的操作，不实际改动",
    )
    parser.add_argument(
        "--skip-build", action="store_true",
        help="跳过打包步骤（用于测试脚本本身）",
    )
    parser.add_argument(
        "--allow-dirty", action="store_true",
        help="允许工作区有未提交改动（不推荐）",
    )
    args = parser.parse_args()

    # ---- 前置检查 ----
    if not git_is_repo():
        err("当前目录不是 Git 仓库，请先 git init")
        return 1

    if not args.allow_dirty and not git_is_clean():
        err("工作区有未提交的改动，请先 commit 或 stash")
        info("如需忽略此检查（不推荐），加 --allow-dirty")
        run(["git", "status", "--short"])
        return 1

    # ---- 计算新版本号 ----
    current = read_current_version()
    new_version = bump_version(current, args.bump)
    new_date = date.today().isoformat()  # YYYY-MM-DD

    print()
    print(f"{C.BOLD}=== TimestampTool Release ==={C.END}")
    print(f"当前版本: {C.YELLOW}{current}{C.END}")
    print(f"新 版 本: {C.GREEN}{new_version}{C.END}  ({new_date})")
    print()

    if args.dry_run:
        info("[DRY-RUN] 预演模式，以下步骤仅打印不执行：")
        print(f"  1. 更新 src/__version__.py → {new_version}")
        print(f"  2. 将 CHANGELOG [Unreleased] 移到 [{new_version}]")
        print(f"  3. python build.py")
        print(f"  4. 复制 dist/TimestampTool.exe → releases/v{new_version}/")
        print(f"  5. git commit -am 'chore: release v{new_version}'")
        print(f"  6. git tag v{new_version}")
        return 0

    # ---- 步骤 1: bump 版本号 ----
    info(f"步骤 1: 更新 src/__version__.py → {new_version}")
    write_version(new_version, new_date)
    ok("版本号已更新")

    # ---- 步骤 2: CHANGELOG ----
    info("步骤 2: 处理 CHANGELOG.md")
    if check_changelog_has_unreleased():
        promote_unreleased_to_version(new_version, new_date)
    else:
        warn("CHANGELOG.md [Unreleased] 节为空")
        answer = input(
            f"{C.YELLOW}是否继续发布？(y/N): {C.END}"
        ).strip().lower()
        if answer != "y":
            info("已取消发布，回滚版本号...")
            write_version(current, new_date)  # 回滚
            return 1

    # ---- 步骤 3: 打包 ----
    if args.skip_build:
        warn("跳过打包步骤（--skip-build）")
    else:
        info("步骤 3: 执行 python build.py")
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            err("打包失败，请检查错误信息")
            return 1
        if not DIST_EXE.exists():
            err(f"打包成功但找不到产物 {DIST_EXE}")
            return 1
        ok(f"打包成功: {DIST_EXE}")

    # ---- 步骤 4: 归档 exe ----
    info(f"步骤 4: 归档 exe 到 releases/v{new_version}/")
    archive_dir = RELEASES_DIR / f"v{new_version}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    if DIST_EXE.exists():
        target = archive_dir / "TimestampTool.exe"
        shutil.copy2(DIST_EXE, target)
        size_mb = target.stat().st_size / 1024 / 1024
        ok(f"已归档: {target} ({size_mb:.1f} MB)")

    # ---- 步骤 5: Git 提交 ----
    info("步骤 5: git add + commit")
    run(["git", "add", "."])
    run(["git", "commit", "-m", f"chore: release v{new_version}"])
    ok("已提交")

    # ---- 步骤 6: 打 Tag ----
    info(f"步骤 6: git tag v{new_version}")
    run(["git", "tag", "-a", f"v{new_version}", "-m", f"Release v{new_version}"])
    ok("已打 tag")

    # ---- 完成提示 ----
    print()
    print(f"{C.GREEN}{C.BOLD}[SUCCESS] 发布完成！{C.END}")
    print()
    print(f"下一步（推送到 GitHub）：")
    print(f"  {C.BOLD}git push && git push --tags{C.END}")
    print()
    print(f"归档位置：{archive_dir}")
    print(f"CHANGELOG：查看 [{new_version}] 节确认变更记录")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        err("\n用户中断")
        sys.exit(130)
    except Exception as e:
        err(f"发布失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
