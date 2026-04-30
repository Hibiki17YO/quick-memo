import threading
import time
import logging
import urllib.request

import uvicorn
import webview

from db import init_db, get_setting
from app import app
from hotkey import HotkeyListener
from desktop import create_window, WindowAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("memo")

window = None
window_visible = True


def wait_for_server(host="127.0.0.1", port=18080, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/memos")
            return True
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("FastAPI server failed to start")


def toggle_window():
    global window_visible, window
    if window is None:
        return
    try:
        if window_visible:
            window.hide()
        else:
            window.show()
        window_visible = not window_visible
    except Exception as e:
        logger.error(f"Toggle error: {e}")


def quit_app():
    global window
    if window:
        try:
            window.destroy()
        except Exception:
            pass


def main():
    global window

    logger.info("Initializing database...")
    init_db()

    logger.info("Starting FastAPI server on port 18080...")
    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": "127.0.0.1", "port": 18080, "log_level": "warning"},
        daemon=True,
    )
    server_thread.start()

    try:
        wait_for_server()
    except RuntimeError as e:
        logger.error(str(e))
        return

    logger.info("Server ready at http://127.0.0.1:18080")
    logger.info("Management page: http://127.0.0.1:18080")

    logger.info("Registering global hotkeys...")
    hotkey_toggle = get_setting("hotkey_toggle", "ctrl+shift+m")
    hotkey_quit = get_setting("hotkey_quit", "ctrl+shift+q")
    logger.info(f"  Toggle: {hotkey_toggle}  |  Quit: {hotkey_quit}")
    hotkey = HotkeyListener(
        toggle_callback=toggle_window, quit_callback=quit_app,
        hotkey_toggle=hotkey_toggle, hotkey_quit=hotkey_quit,
    )
    hotkey_thread = threading.Thread(target=hotkey.start, daemon=True)
    hotkey_thread.start()

    logger.info("Opening memo window...")
    api = WindowAPI()
    try:
        win_w = int(get_setting("window_width", "440"))
        win_h = int(get_setting("window_height", "460"))
    except ValueError:
        win_w, win_h = 440, 460
    logger.info(f"  Window size: {win_w}x{win_h}")
    window = create_window(api, width=win_w, height=win_h)
    webview.start(debug=False)

    logger.info("Application closed.")


if __name__ == "__main__":
    main()
