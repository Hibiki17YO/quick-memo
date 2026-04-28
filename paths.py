"""Path resolution for both dev and PyInstaller bundle."""
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def bundle_dir() -> Path:
    """Where bundled resources (static, templates) live."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def app_dir() -> Path:
    """Where the exe/script lives (for DB, uploads — persists across runs)."""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent
