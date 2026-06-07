from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from pcos.core.divergence_service import DivergenceService
from pcos.infrastructure.database import Database
import asyncio
import uuid

router = APIRouter()
service = DivergenceService()
db = Database()

class DivergenceFeedback(BaseModel):
    response: str  # "accepted" or "dismissed"

@router.get("")
async def get_divergence_suggestion(current_state: str = "neutral"):
    result = await service.generate_suggestion(current_state)
    return result

@router.get("/queue")
async def get_divergence_queue(status: Optional[str] = "pending"):
    """Get pending or all divergence queue items."""
    def _get():
        cursor = db.conn.execute(
            "SELECT id, suggestion, created_at, status FROM divergence_queue WHERE status = ? ORDER BY created_at DESC",
            (status,)
        )
        return [dict(row) for row in cursor.fetchall()]
    items = await asyncio.to_thread(_get)
    return {"items": items}

@router.post("/queue/{item_id}/feedback")
async def feedback_divergence(item_id: str, feedback: DivergenceFeedback):
    def _update():
        with db._lock:
            db.conn.execute(
                "UPDATE divergence_queue SET status = ?, responded_at = ? WHERE id = ?",
                (feedback.response, datetime.now(), item_id)
            )
            db.conn.commit()
    await asyncio.to_thread(_update)
    return {"status": "ok"}

@router.put("/queue/{item_id}/accept")
async def accept_divergence(item_id: str):
    def _accept():
        with db._lock:
            db.conn.execute(
                "UPDATE divergence_queue SET status = 'accepted', responded_at = ? WHERE id = ?",
                (datetime.now(), item_id)
            )
            db.conn.commit()
    await asyncio.to_thread(_accept)
    return {"status": "ok"}

@router.put("/queue/{item_id}/dismiss")
async def dismiss_divergence(item_id: str):
    def _dismiss():
        with db._lock:
            db.conn.execute(
                "UPDATE divergence_queue SET status = 'dismissed', responded_at = ? WHERE id = ?",
                (datetime.now(), item_id)
            )
            db.conn.commit()
    await asyncio.to_thread(_dismiss)
    return {"status": "ok"}

@router.delete("/queue/{item_id}")
async def delete_divergence(item_id: str):
    """Permanently delete a divergence queue item."""
    def _delete():
        with db._lock:
            db.conn.execute("DELETE FROM divergence_queue WHERE id = ?", (item_id,))
            db.conn.commit()
    await asyncio.to_thread(_delete)
    return {"status": "ok"}