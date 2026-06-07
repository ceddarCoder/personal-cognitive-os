import keyboard
from PyQt6.QtCore import QTimer

class SimpleHotkey:
    def __init__(self, callback, hotkey_string="ctrl+alt+p"):
        self.hotkey_string = hotkey_string
        self.callback = callback
        self._running = False

    def start(self):
        self._running = True
        keyboard.add_hotkey(self.hotkey_string, self._on_hotkey, suppress=False)

    def _on_hotkey(self):
        if self._running and self.callback:
            # Simple: use QTimer to run callback in main thread
            QTimer.singleShot(0, self.callback)

    def stop(self):
        self._running = False
        keyboard.remove_hotkey(self.hotkey_string)