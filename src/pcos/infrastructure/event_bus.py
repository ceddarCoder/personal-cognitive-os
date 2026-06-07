import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Any
from loguru import logger
from pcos.infrastructure.settings import settings

class EventBus:
    """Simple in-process event bus with async/thread-safe dispatch."""
    _instance = None
    _listeners: Dict[str, List[Callable]] = {}
    _dead_letter_path = settings.EVENT_BUS_LOG
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self._listeners = {}
        self._dead_letter_path.parent.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="EventBus")
    
    def subscribe(self, event: str, callback: Callable):
        """Subscribe a callback to an event. Callback can be sync or async."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
        logger.debug(f"Subscribed to {event}")
    
    def unsubscribe(self, event: str, callback: Callable):
        if event in self._listeners:
            self._listeners[event].remove(callback)
    
    def publish(self, event: str, data: dict):
        """Publish an event to all subscribers. Runs in background threads."""
        if event not in self._listeners:
            return
        for cb in self._listeners[event]:
            # Run each callback in the thread pool to avoid blocking and thread bloat
            self._executor.submit(self._dispatch, cb, event, data)
    
    def _dispatch(self, cb: Callable, event: str, data: dict):
        try:
            if asyncio.iscoroutinefunction(cb):
                # Run async callback in its own event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(cb(data))
                loop.close()
            else:
                cb(data)
        except Exception as e:
            self._log_dead_letter(event, data, str(e))
            logger.error(f"Event handler failed for {event}: {e}")
    
    def _log_dead_letter(self, event: str, data: dict, error: str):
        """Log failed events for later inspection."""
        entry = {
            "event": event,
            "data": data,
            "error": error,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        with open(self._dead_letter_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

# Singleton instance
bus = EventBus()
