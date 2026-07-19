"""TimestampTool 打包脚本

使用 PyInstaller --onefile 模式打包为单个可执行文件，
生成的 TimestampTool.exe 可直接复制给他人使用（免安装、免依赖）。

注意：
- 用户配置 config.json 会写在 exe 同目录（首次运行自动创建）
- 图标资源打包在 exe 内部（运行时解压到临时目录）
"""
import subprocess
import sys
import shutil
from pathlib import Path


def build():
    """执行打包"""
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    dist_dir = project_root / "dist"
    build_dir = project_root / "build_temp"

    # 先杀掉可能在运行的旧进程，避免文件被占用
    print("检查并终止旧的 TimestampTool 进程...")
    subprocess.run(
        ['taskkill', '/F', '/IM', 'TimestampTool.exe'],
        capture_output=True, shell=False
    )

    # 清理旧的构建
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # PyInstaller 参数（--onefile 单文件模式）
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",              # 打包成单个 exe
        "--windowed",             # 无控制台窗口
        "--name", "TimestampTool",
        "--icon", str(project_root / "assets" / "icon.ico"),
        # 数据文件（打包至 exe 内嵌资源，运行时解压到 sys._MEIPASS）
        "--add-data", f"{project_root / 'config' / 'config.json'};config",
        "--add-data", f"{project_root / 'assets' / 'icon.ico'};assets",
        # 隐藏导入
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
        "--hidden-import", "customtkinter",
        # 输出目录
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(build_dir),
        # 禁用 UPX（避免杀毒误报）
        "--noupx",
        # 入口文件
        str(src_dir / "main.py"),
    ]

    print("=" * 50)
    print("  TimestampTool 打包脚本 (single-file exe)")
    print("=" * 50)
    print(f"\n入口文件: {src_dir / 'main.py'}")
    print(f"输出文件: {dist_dir / 'TimestampTool.exe'}")
    print(f"\n正在打包...")

    result = subprocess.run(args, cwd=str(project_root))

    if result.returncode == 0:
        exe_path = dist_dir / "TimestampTool.exe"
        size_mb = exe_path.stat().st_size / 1024 / 1024 if exe_path.exists() else 0
        print(f"\n{'=' * 50}")
        print(f"  打包成功！")
        print(f"  输出: {exe_path}")
        print(f"  体积: {size_mb:.1f} MB")
        print(f"  分发方式: 直接把 TimestampTool.exe 拷给别人即可运行")
        print(f"  配置存储: %APPDATA%\\TimestampTool\\config.json（用户不可见）")
        print(f"  exe 同目录不产生任何配置文件，纯净分发")
        print(f"{'=' * 50}")
    else:
        print(f"\n打包失败，退出码: {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
