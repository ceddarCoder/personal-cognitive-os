import signal
import sys
from PyQt6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon, QMenu, QTextEdit, QVBoxLayout
from PyQt6.QtGui import QIcon, QAction, QKeySequence, QPixmap, QPainter, QColor, QShortcut
from PyQt6.QtCore import Qt, QTimer
import requests
from pcos.infrastructure.win32.hotkey import SimpleHotkey
from pcos.infrastructure.settings import settings

API_BASE = f"http://{settings.API_HOST}:{settings.API_PORT}"

# Global reference for cleanup
_app_instance = None

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global _app_instance
    print("\n[PCOS] Received shutdown signal...")
    if _app_instance:
        _app_instance.quit_app()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def create_tray_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(0, 120, 212))
    painter.setPen(Qt.GlobalColor.white)
    painter.drawRoundedRect(0, 0, 64, 64, 10, 10)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "P")
    painter.end()
    return QIcon(pixmap)

class CaptureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PCOS Quick Capture")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        self.resize(500, 200)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("What's on your mind? (Ctrl+Enter to save)"))
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Task, idea, reminder...")
        layout.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close_dialog)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self.save)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.close_dialog)
    
    def showEvent(self, event):
        self.text_edit.clear()
        self.text_edit.setFocus()
        super().showEvent(event)
    
    def save(self):
        content = self.text_edit.toPlainText().strip()
        if not content:
            self.close_dialog()
            return
        
        self.save_btn.setEnabled(False)
        
        def do_post():
            try:
                response = requests.post(f"{API_BASE}/capture", json={"content": content, "source": "hotkey"})
                if response.status_code == 200:
                    print(f"✓ Saved: {content[:50]}")
                else:
                    print(f"✗ API error: {response.text}")
            except Exception as e:
                print(f"✗ Connection error: {e}")
            finally:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.close_dialog)
        
        import threading
        threading.Thread(target=do_post, daemon=True).start()
    
    def close_dialog(self):
        self.accept()
        self.deleteLater()


from pcos.ui.overlay_window import OverlayWindow

class PCOSApplication(QApplication):
    def __init__(self):
        import sys
        global _app_instance
        super().__init__(sys.argv)
        _app_instance = self
        self.setQuitOnLastWindowClosed(False)
        
        # Tray
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(create_tray_icon())
        self.tray.setToolTip("PCOS")
        self.tray.activated.connect(self.on_tray_click)
        
        menu = QMenu()
        toggle_action = QAction("Toggle Overlay (Ctrl+Alt+O)")
        toggle_action.triggered.connect(self.toggle_overlay)
        menu.addAction(toggle_action)
        capture_action = QAction("Quick Capture (Ctrl+Alt+P)")
        capture_action.triggered.connect(self.show_capture)
        menu.addAction(capture_action)
        menu.addSeparator()
        show_state_action = QAction("Show Current State")
        show_state_action.triggered.connect(self.show_current_state)
        menu.addAction(show_state_action)
        menu.addSeparator()
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        self.tray.show()
        
        # Overlay
        self.overlay = OverlayWindow()
        self.overlay.hide()  # Pre-load it but don't show
        
        # Hotkeys
        self.capture_hotkey = SimpleHotkey(self.show_capture, "ctrl+alt+p")
        self.capture_hotkey.start()
        
        self.overlay_hotkey = SimpleHotkey(self.toggle_overlay, "ctrl+alt+o")
        self.overlay_hotkey.start()
        
        self.capture_dialog = None
        
        # Debug timer to show state is working
        self.debug_timer = QTimer()
        self.debug_timer.timeout.connect(self.debug_state)
        self.debug_timer.start(10000)  # Every 10 seconds
    
    def debug_state(self):
        """Debug: fetch and print current state."""
        try:
            import requests
            response = requests.get(f"{API_BASE}/state", timeout=2)
            if response.ok:
                data = response.json()
                print(f"[DEBUG] Current state: {data.get('state', 'unknown')} (conf: {data.get('confidence', 0):.2f})")
        except Exception as e:
            print(f"[DEBUG] Could not fetch state: {e}")
    
    def show_current_state(self):
        """Show current state in a message box."""
        try:
            import requests
            response = requests.get(f"{API_BASE}/state", timeout=2)
            if response.ok:
                data = response.json()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    None, 
                    "PCOS State", 
                    f"State: {data.get('state', 'unknown')}\nConfidence: {data.get('confidence', 0):.2f}\n\nSignals: {data.get('signals', {})}"
                )
        except Exception as e:
            print(f"Error: {e}")
            
    def toggle_overlay(self):
        self.overlay.toggle()
    
    def show_capture(self):
        dialog = CaptureDialog()
        dialog.destroyed.connect(lambda: setattr(self, "capture_dialog", None))
        self.capture_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
    
    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_overlay()
    
    def quit_app(self):
        print("[PCOS] Shutting down...")
        self.capture_hotkey.stop()
        self.overlay_hotkey.stop()
        self.quit()
    
    def run(self):
        return self.exec()