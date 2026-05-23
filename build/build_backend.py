"""
Python 后端打包脚本 — PyInstaller

将 FastAPI 后端打包为独立 exe，用户无需安装 Python。
输出: backend/dist/voice-input-backend.exe

用法:
    python build/build_backend.py
"""
import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DIST_DIR = PROJECT_ROOT / "backend" / "dist"


def main():
    print("=" * 50)
    print("  智能语音输入法 — 后端打包")
    print("=" * 50)

    # 检查 PyInstaller
    try:
        import PyInstaller  # noqa
    except ImportError:
        print("安装 PyInstaller...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            cwd=PROJECT_ROOT,
        )

    # 数据库目录（确保包含在打包中）
    db_dir = PROJECT_ROOT / "databases"
    db_dir.mkdir(parents=True, exist_ok=True)

    # PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "voice-input-backend",
        "--onefile",  # 单文件 exe
        "--distpath", str(DIST_DIR),
        "--workpath", str(PROJECT_ROOT / "build" / "_pyinstaller_work"),
        "--specpath", str(PROJECT_ROOT / "build"),
        "--add-data", f"{db_dir}{os.pathsep}databases",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        # 数据库驱动
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic_settings",
        # 服务模块
        "--collect-submodules", "database",
        "--collect-submodules", "services",
        str(BACKEND_DIR / "main.py"),
    ]

    print("\n运行 PyInstaller...")
    subprocess.check_call(cmd, cwd=PROJECT_ROOT, env={
        **os.environ,
        "PYTHONPATH": str(BACKEND_DIR),
    })

    print(f"\n打包完成!")
    print(f"  输出: {DIST_DIR / 'voice-input-backend.exe'}")

    # 验证
    exe_path = DIST_DIR / "voice-input-backend.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"  大小: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
