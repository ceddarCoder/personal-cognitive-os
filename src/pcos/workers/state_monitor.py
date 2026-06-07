import threading
import time
import json
from datetime import datetime
import uuid
from pcos.infrastructure.win32.state_detector import StateDetector
from pcos.infrastructure.database import Database
from pcos.infrastructure.win32.notifier import Notifier

_state_detector = None
_notifier = None
_running = False

def get_state_detector() -> StateDetector:
    """Get the shared StateDetector instance (created on first call or by start_state_monitor)."""
    global _state_detector
    if _state_detector is None:
        _state_detector = StateDetector()
    return _state_detector

def log_state_callback(state, confidence, reason, signals):
    """Callback to log state to database."""
    try:
        db = Database()
        db.log_state(state, confidence, reason, json.dumps(signals))
    except Exception as e:
        print(f"Failed to log state: {e}")

def start_state_monitor():
    """Start the state monitoring background thread."""
    global _state_detector, _notifier, _running
    _state_detector = get_state_detector()
    _notifier = Notifier()
    _running = True
    
    def monitor_loop():
        last_state = None
        while _running:
            try:
                state, confidence, signals = _state_detector.detect(log_callback=log_state_callback)
                
                # Send notification on state changes or specific states
                if confidence > 0.6:
                    prompts = {
                        "distracted": "You've been idle or browsing distractions. Time to refocus?",
                        "wind_down": "Wind down time. Capture one win from today.",
                        "morning_focus": "Good morning! What's the most important task today?",
                        "post_lunch_dip": "Post-lunch energy dip. Start with a small 5-minute task."
                    }
                    
                    # Notify on state change to distracted or wind_down
                    if state in prompts and state != last_state:
                        if _notifier.can_notify(f"state_{state}"):
                            _notifier.show("PCOS", prompts[state])
                    
                    # Also notify if distracted persists for 3 consecutive detections
                    if state == "distracted" and state == last_state:
                        # Count consecutive distracted states
                        if not hasattr(monitor_loop, 'distracted_count'):
                            monitor_loop.distracted_count = 0
                        monitor_loop.distracted_count += 1
                        if monitor_loop.distracted_count >= 3 and _notifier.can_notify("distracted_persistent"):
                            _notifier.show("PCOS", "Still distracted? Take a deep breath and pick one task.")
                            monitor_loop.distracted_count = 0
                    else:
                        monitor_loop.distracted_count = 0
                
                last_state = state
                
            except Exception as e:
                print(f"State monitor error: {e}")
            
            time.sleep(30)  # Check every 30 seconds
    
    thread = threading.Thread(target=monitor_loop, daemon=True, name="StateMonitor")
    thread.start()
    print("[PCOS] State monitor started with hysteresis and browser classification")

def stop_state_monitor():
    global _running
    _running = False