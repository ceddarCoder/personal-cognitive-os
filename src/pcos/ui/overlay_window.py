"""
PCOS HUD Overlay — QWebEngineView + Python Bridge
Phase A: Foundation
"""
import json
import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QObject, QUrl, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QColor, QRegion
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel

from pcos.infrastructure.database import Database
from pcos.core.capture_service import CaptureService
from pcos.workers.state_monitor import get_state_detector

logger = logging.getLogger("pcos.overlay")


class PCOSAPIBridge(QObject):
    """Python bridge exposed to JavaScript via QWebChannel."""

    close_requested = pyqtSignal()
    chat_response_received = pyqtSignal(str, str)  # session_id, response_json

    def __init__(self):
        super().__init__()
        self.db = Database()

    @pyqtSlot(result=str)
    def get_state(self):
        try:
            state_data = self.db.get_current_state()
            return json.dumps(state_data)
        except Exception as e:
            logger.error(f"get_state error: {e}")
            return json.dumps({"state": "unknown", "confidence": 0, "signals": {}})

    @pyqtSlot(int, result=str)
    def get_recent_notes(self, limit):
        try:
            notes = self.db.get_recent_notes(limit)
            for n in notes:
                if n.get("created_at"):
                    n["created_at"] = str(n["created_at"])
            return json.dumps({"notes": notes})
        except Exception as e:
            logger.error(f"get_recent_notes error: {e}")
            return json.dumps({"notes": []})

    @pyqtSlot(result=str)
    def get_tasks(self):
        try:
            tasks = self.db.get_open_tasks()
            for t in tasks:
                if t.get("created_at"):
                    t["created_at"] = str(t["created_at"])
            return json.dumps({"tasks": tasks})
        except Exception as e:
            logger.error(f"get_tasks error: {e}")
            return json.dumps({"tasks": []})

    @pyqtSlot(result=str)
    def get_divergence_queue(self):
        try:
            items = self.db.get_divergence_queue_items("pending")
            delivered = self.db.get_divergence_queue_items("delivered")
            all_items = items + delivered
            for item in all_items:
                if item.get("created_at"):
                    item["created_at"] = str(item["created_at"])
            return json.dumps({"items": all_items})
        except Exception as e:
            logger.error(f"get_divergence_queue error: {e}")
            return json.dumps({"items": []})

    @pyqtSlot(str, str, result=str)
    def capture(self, content, mode):
        try:
            service = CaptureService()
            detector = get_state_detector()
            state, _, _ = detector.detect()
            note_id = service.process_capture(content, "overlay", state, note_type=mode)
            return json.dumps({"status": "ok", "id": note_id})
        except Exception as e:
            logger.error(f"capture error: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @pyqtSlot(str, result=str)
    def complete_task(self, task_id):
        try:
            self.db.complete_task(task_id)
            return json.dumps({"status": "ok"})
        except Exception as e:
            logger.error(f"complete_task error: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @pyqtSlot(str, result=str)
    def search_notes(self, query):
        try:
            from pcos.core.memory_service import MemoryService
            memory = MemoryService()
            results = memory.search(query, 10)
            return json.dumps({"results": results})
        except Exception as e:
            logger.error(f"search_notes error: {e}")
            return json.dumps({"results": []})

    @pyqtSlot(str, result=str)
    def accept_divergence(self, item_id):
        try:
            from datetime import datetime
            with self.db._lock:
                self.db.conn.execute(
                    "UPDATE divergence_queue SET status = 'accepted', responded_at = ? WHERE id = ?",
                    (datetime.now(), item_id)
                )
                self.db.conn.commit()
            return json.dumps({"status": "ok"})
        except Exception as e:
            logger.error(f"accept_divergence error: {e}")
            return json.dumps({"status": "error"})

    @pyqtSlot(str, result=str)
    def dismiss_divergence(self, item_id):
        try:
            from datetime import datetime
            with self.db._lock:
                self.db.conn.execute(
                    "UPDATE divergence_queue SET status = 'dismissed', responded_at = ? WHERE id = ?",
                    (datetime.now(), item_id)
                )
                self.db.conn.commit()
            return json.dumps({"status": "ok"})
        except Exception as e:
            logger.error(f"dismiss_divergence error: {e}")
            return json.dumps({"status": "error"})

    @pyqtSlot(str, int, result=str)
    def override_state(self, state, minutes):
        try:
            from pathlib import Path
            from pcos.infrastructure.settings import settings
            import json
            from datetime import datetime

            override_file = settings.PCOS_DATA_DIR / "state_override.json"
            expires = datetime.now().timestamp() + (minutes * 60)
            data = {"state": state, "expires": expires}
            override_file.parent.mkdir(parents=True, exist_ok=True)
            with open(override_file, "w") as f:
                json.dump(data, f)
            logger.info(f"State override set to {state} until {datetime.fromtimestamp(expires)}")
            return json.dumps({"status": "ok"})
        except Exception as e:
            logger.error(f"override_state error: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @pyqtSlot(result=str)
    def clear_override(self):
        try:
            from pcos.infrastructure.settings import settings
            override_file = settings.PCOS_DATA_DIR / "state_override.json"
            if override_file.exists():
                override_file.unlink()
            return json.dumps({"status": "cleared"})
        except Exception as e:
            logger.error(f"clear_override error: {e}")
            return json.dumps({"status": "error"})

    @pyqtSlot(str, str)
    def send_chat(self, message, session_id):
        import threading
        import requests
        from pcos.infrastructure.settings import settings

        def _do_chat():
            try:
                url = f"http://{settings.API_HOST}:{settings.API_PORT}/chat"
                resp = requests.post(url, json={"message": message, "session_id": session_id or None}, timeout=60)
                if resp.ok:
                    data = resp.json()
                    self.chat_response_received.emit(data.get("session_id", ""), json.dumps(data))
                else:
                    self.chat_response_received.emit(session_id, json.dumps({"error": resp.text}))
            except Exception as e:
                self.chat_response_received.emit(session_id, json.dumps({"error": str(e)}))

        threading.Thread(target=_do_chat, daemon=True).start()

    @pyqtSlot()
    def close_overlay(self):
        self.close_requested.emit()
    
    @pyqtSlot(str, result=str)
    def delete_divergence(self, item_id):
        try:
            with self.db._lock:
                self.db.conn.execute(
                    "DELETE FROM divergence_queue WHERE id = ?",
                    (item_id,)
                )
                self.db.conn.commit()
            return json.dumps({"status": "ok"})
        except Exception as e:
            logger.error(f"delete_divergence error: {e}")
            return json.dumps({"status": "error", "error": str(e)})


class OverlayWebPage(QWebEnginePage):
    """Custom page with transparent background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor(QColor(0, 0, 0, 0))

    def javaScriptConsoleMessage(self, level, message, line, source):
        logger.debug(f"[JS:{line}] {message}")


class OverlayWindow(QMainWindow):
    """Frameless transparent overlay window with QWebEngineView."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Force the window to accept mouse events (not pass through)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Bridge
        self.bridge = PCOSAPIBridge()
        self.bridge.close_requested.connect(self.hide_overlay)

        # WebChannel
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)

        # WebEngineView
        self.web_view = QWebEngineView(self)
        self.web_view.setGeometry(0, 0, screen.width(), screen.height())
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.web_view.setStyleSheet("background: transparent;")

        page = OverlayWebPage(self.web_view)
        page.setWebChannel(self.channel)
        self.web_view.setPage(page)

        # Load HTML
        html_path = Path(__file__).parent / "overlay.html"
        if html_path.exists():
            self.web_view.load(QUrl.fromLocalFile(str(html_path)))
        else:
            logger.error(f"overlay.html not found at {html_path}")

        self._visible = False

    def toggle(self):
        if self._visible:
            self.hide_overlay()
        else:
            self.show_overlay()

    def show_overlay(self):
        self.showFullScreen()
        # Set an input mask so the entire window receives mouse events
        self.setMask(QRegion(0, 0, self.width(), self.height()))
        self._visible = True
        self.web_view.page().runJavaScript("if(typeof loadInitialData==='function')loadInitialData();")
        logger.info("Overlay shown")

    def hide_overlay(self):
        self.hide()
        self._visible = False
        logger.info("Overlay hidden")