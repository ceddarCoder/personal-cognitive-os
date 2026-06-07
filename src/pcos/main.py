import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
import sys
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pcos.api.server import start_api_server
from pcos.ui.tray import PCOSApplication
from pcos.infrastructure.settings import settings
from pcos.workers.state_monitor import start_state_monitor

def main():
    # Start API in background thread
    api_thread = threading.Thread(target=start_api_server, daemon=True, name="PCOS-API")
    api_thread.start()
    
    # Start state monitor in background thread
    start_state_monitor()
    
    print(f"[PCOS] API: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"[PCOS] Data: {settings.PCOS_DATA_DIR}")
    print("[PCOS] State monitor running (checks every 30 seconds)")
    print("[PCOS] Tray icon running. Press Ctrl+Alt+P to capture.")
    
    # Start Qt app (blocks until exit)
    app = PCOSApplication()
    sys.exit(app.run())

if __name__ == "__main__":
    main()