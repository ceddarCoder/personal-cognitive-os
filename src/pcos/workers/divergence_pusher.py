import asyncio
import threading
from datetime import datetime
from pcos.infrastructure.database import Database
from pcos.infrastructure.win32.state_detector import StateDetector
from pcos.infrastructure.win32.notifier import Notifier
from loguru import logger

detector = StateDetector()
notifier = Notifier()
db = Database()

def is_free() -> bool:
    """Determine if user is free to receive a suggestion."""
    state, confidence, _ = detector.detect()
    # Free if not in deep_work or meeting, idle minutes low
    if state in ["deep_work", "meeting"]:
        return False
    idle = detector.get_idle_minutes()
    if idle > 5:
        return False
    return True

def get_pending_suggestion():
    """Fetch the oldest pending suggestion."""
    with db._lock:
        cursor = db.conn.execute(
            "SELECT id, suggestion FROM divergence_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
        )
        row = cursor.fetchone()
        return (row['id'], row['suggestion']) if row else (None, None)

def mark_delivered(qid):
    with db._lock:
        db.conn.execute("UPDATE divergence_queue SET status = 'delivered', delivered_at = ? WHERE id = ?", (datetime.now(), qid))
        db.conn.commit()

def mark_response(qid, response):
    with db._lock:
        db.conn.execute("UPDATE divergence_queue SET status = ?, responded_at = ? WHERE id = ?", (response, datetime.now(), qid))
        db.conn.commit()
        # Also log to actions table for feedback
        db.log_action(
            suggestion_type="divergence",
            suggested_content="",
            trigger_reason="proactive_push",
            user_state="neutral",
            user_response=response
        )

def callback_accept(qid):
    mark_response(qid, "accepted")
    logger.info(f"Suggestion {qid} accepted")

def callback_dismiss(qid):
    mark_response(qid, "dismissed")
    logger.info(f"Suggestion {qid} dismissed")

async def pusher_loop():
    while True:
        if is_free():
            qid, suggestion = get_pending_suggestion()
            if qid and suggestion:
                # Show toast with buttons
                notifier.notify_with_actions(
                    title="PCOS Divergence",
                    message=suggestion,
                    actions=[
                        ("✅ Accept", lambda: callback_accept(qid)),
                        ("❌ Dismiss", lambda: callback_dismiss(qid))
                    ]
                )
                mark_delivered(qid)
        await asyncio.sleep(300)  # 5 minutes

def start_pusher():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(pusher_loop())