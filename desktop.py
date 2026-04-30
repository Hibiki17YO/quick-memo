import ctypes
import logging
import webbrowser

import webview

logger = logging.getLogger(__name__)

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19


def _get_form():
    """Reach into pywebview WinForms internals to get the .NET Form object."""
    try:
        from webview.platforms.winforms import BrowserView
        if BrowserView.instances:
            return next(iter(BrowserView.instances.values()))
    except Exception as e:
        logger.error(f"_get_form failed: {e}")
    return None


def _form_hwnd(form) -> int:
    if not form:
        return 0
    try:
        return int(form.Handle.ToInt64())
    except Exception:
        try:
            return int(form.Handle)
        except Exception:
            return 0


def _invoke_on_ui(form, fn):
    """Run fn on the WinForms UI thread."""
    if not form:
        return
    try:
        from System import Action
        if form.InvokeRequired:
            form.Invoke(Action(fn))
        else:
            fn()
    except Exception as e:
        logger.error(f"invoke_on_ui failed: {e}")


def _set_on_top_via_form(on: bool):
    form = _get_form()
    if not form:
        logger.warning("No form found for on_top toggle")
        return False

    def apply():
        try:
            form.TopMost = bool(on)
        except Exception as e:
            logger.error(f"set TopMost failed: {e}")

    _invoke_on_ui(form, apply)
    logger.info(f"TopMost set to {on}")
    return True


def _set_dark_titlebar(dark: bool):
    form = _get_form()
    hwnd = _form_hwnd(form)
    if not hwnd:
        return
    val = ctypes.c_int(1 if dark else 0)
    for attr in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD):
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)
            )
        except Exception:
            pass


class WindowAPI:
    """JS-callable API. Underscore-prefixed attrs are skipped by pywebview's
    auto-injection scan."""

    def __init__(self):
        self._window = None
        self._is_maximized = False
        self._is_on_top = True

    def _attach(self, window):
        self._window = window

    def minimize(self):
        if self._window:
            self._window.minimize()
        return True

    def toggle_maximize(self):
        if not self._window:
            return False
        if self._is_maximized:
            self._window.restore()
            self._is_maximized = False
        else:
            self._window.maximize()
            self._is_maximized = True
        return self._is_maximized

    def hide_window(self):
        if self._window:
            self._window.hide()
        return True

    def toggle_on_top(self):
        new_state = not self._is_on_top
        if _set_on_top_via_form(new_state):
            self._is_on_top = new_state
        return self._is_on_top

    def open_management_page(self):
        try:
            webbrowser.open("http://127.0.0.1:18080")
        except Exception as e:
            logger.error(f"open management page failed: {e}")
            return False
        return True

    def set_dark_titlebar(self, dark: bool):
        _set_dark_titlebar(bool(dark))
        return True

    def get_state(self):
        return {
            "is_on_top": self._is_on_top,
            "is_maximized": self._is_maximized,
        }


def create_window(api: WindowAPI, url: str = "http://127.0.0.1:18080/api/editor-html",
                  width: int = 440, height: int = 460):
    window = webview.create_window(
        title="Quick Memo",
        url=url,
        width=max(width, 380),
        height=max(height, 320),
        on_top=True,
        background_color="#fafafa",
        min_size=(380, 320),
        js_api=api,
    )
    api._attach(window)
    return window
