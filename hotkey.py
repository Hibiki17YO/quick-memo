import keyboard
import logging

logger = logging.getLogger(__name__)


class HotkeyListener:
    def __init__(self, toggle_callback, quit_callback=None,
                 hotkey_toggle="ctrl+shift+m", hotkey_quit="ctrl+shift+q"):
        self.toggle_callback = toggle_callback
        self.quit_callback = quit_callback
        self.hotkey_toggle = hotkey_toggle
        self.hotkey_quit = hotkey_quit

    def start(self):
        keyboard.add_hotkey(self.hotkey_toggle, self._on_toggle, suppress=False)
        logger.info(f"Hotkey: {self.hotkey_toggle} (toggle window)")

        if self.quit_callback:
            keyboard.add_hotkey(self.hotkey_quit, self._on_quit, suppress=False)
            logger.info(f"Hotkey: {self.hotkey_quit} (quit app)")

        keyboard.wait()

    def _on_toggle(self):
        try:
            self.toggle_callback()
        except Exception as e:
            logger.error(f"Toggle error: {e}")

    def _on_quit(self):
        try:
            if self.quit_callback:
                self.quit_callback()
        except Exception as e:
            logger.error(f"Quit error: {e}")

    def stop(self):
        keyboard.unhook_all()
