from fastapi import APIRouter
from pcos.infrastructure.win32.state_detector import StateDetector
import asyncio

router = APIRouter()

@router.get("")
async def get_current_state():
    detector = StateDetector()
    # detect() is synchronous – run in thread
    state, confidence, signals = await asyncio.to_thread(detector.detect)
    return {"state": state, "confidence": confidence, "signals": signals}

@router.get("/history")
async def get_state_history(limit: int = 20):
    from pcos.infrastructure.database import Database
    db = Database()
    def _history():
        cursor = db.conn.execute(
            "SELECT detected_at, state, confidence, reason FROM state_log ORDER BY detected_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    history = await asyncio.to_thread(_history)
    return {"history": history}