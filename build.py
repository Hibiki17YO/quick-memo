"""Build script for Quick Memo — generates .exe via PyInstaller."""
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    # Install PyInstaller if missing
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Clean previous build
    for d in ["build", "dist"]:
        p = ROOT / d
        if p.exists():
            shutil.rmtree(p)
            print(f"Cleaned {d}/")

    spec = ROOT / "quick-memo.spec"
    if not spec.exists():
        print("ERROR: quick-memo.spec not found. Run this from the project root.")
        sys.exit(1)

    print("Building...")
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec),
    ])

    exe = ROOT / "dist" / "QuickMemo.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\nDone! Output: {exe}  ({size_mb:.1f} MB)")
    else:
        print("\nBuild finished. Check dist/ for output.")


if __name__ == "__main__":
    main()
