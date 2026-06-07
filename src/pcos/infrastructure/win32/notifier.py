from windows_toasts import Toast, WindowsToaster, ToastButton
from datetime import datetime
from pcos.infrastructure.database import Database
import threading
import uuid

class Notifier:
    def __init__(self):
        self.toaster = WindowsToaster('PCOS')
        self.db = Database()
        self.last_notification_time = {}
        self.min_interval_minutes = 15
        self.callbacks = {}  # store callbacks for button IDs

    def can_notify(self, key):
        """Check if enough time has passed since last notification for this key."""
        last = self.last_notification_time.get(key, 0)
        now = datetime.now().timestamp()
        if now - last < self.min_interval_minutes * 60:
            return False
        self.last_notification_time[key] = now
        return True

    def show(self, title: str, message: str, duration: str = "short"):
        """Simple show method for basic notifications."""
        toast = Toast()
        toast.text_fields = [title, message]
        self.toaster.show_toast(toast)

    def notify_with_actions(self, title: str, message: str, actions: list):
        """
        Show an interactive toast with action buttons.
        actions: list of (button_text, callback_function)
        """
        toast = Toast()
        toast.text_fields = [title, message]
        for btn_text, callback in actions:
            button_id = str(uuid.uuid4())
            self.callbacks[button_id] = callback
            button = ToastButton(btn_text)
            # Store button_id in the button's tag or use a closure
            # windows_toasts requires a callable with no args, so we capture the ID
            button.on_activated = lambda id=button_id: self._trigger_callback(id)
            toast.AddAction(button)
        self.toaster.show_toast(toast)

    def _trigger_callback(self, button_id: str):
        """Run the callback associated with a button in a separate thread."""
        cb = self.callbacks.get(button_id)
        if cb:
            threading.Thread(target=cb, daemon=True).start()
        # Optionally clean up after a delay
        threading.Timer(60.0, lambda: self.callbacks.pop(button_id, None)).start()

    def notify_state(self, state, confidence, prompt=None):
        """Show state-based notification."""
        if confidence < 0.6:
            return
        if not self.can_notify(f"state_{state}"):
            return
        
        if not prompt:
            # Default prompts
            prompts = {
                "distracted": "You've been browsing or idle. Time to refocus?",
                "wind_down": "Wind down time. Capture one win from today.",
                "morning_focus": "Good morning! What's the most important task today?",
                "post_lunch_dip": "Post-lunch energy dip. Start with a 5-minute task."
            }
            prompt = prompts.get(state, f"State detected: {state}")
        
        toast = Toast()
        toast.text_fields = [f"PCOS – {state.replace('_', ' ').title()}", prompt]
        self.toaster.show_toast(toast)
        
        # Log action
        try:
            self.db.log_action(
                suggestion_type="state_prompt",
                suggested_content=prompt,
                trigger_reason=f"state_{state}",
                user_state=state
            )
        except AttributeError:
            pass

    def notify_deviation(self, deviation):
        """Notify when actual state deviates from expected."""
        if not self.can_notify("deviation"):
            return
        toast = Toast()
        toast.text_fields = ["PCOS – Schedule Deviation", f"{deviation.get('message', 'State deviation detected')}"]
        self.toaster.show_toast(toast)