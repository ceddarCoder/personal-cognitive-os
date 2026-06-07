import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pcos.infrastructure.database import Database
import uuid

router = APIRouter()
db = Database()

class ScheduleBlockCreate(BaseModel):
    start_time: str  # ISO format
    end_time: str
    block_type: str  # deep_work, meeting, free, task_review, diverge
    title: Optional[str] = None
    metadata: Optional[dict] = None

class ScheduleBlockUpdate(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    block_type: Optional[str] = None
    title: Optional[str] = None
    metadata: Optional[dict] = None

@router.post("")
async def create_block(block: ScheduleBlockCreate):
    block_id = str(uuid.uuid4())
    start = datetime.fromisoformat(block.start_time)
    end = datetime.fromisoformat(block.end_time)
    metadata_json = json.dumps(block.metadata or {})

    def _insert():
        with db._lock:
            db.conn.execute(
                """INSERT INTO schedule_blocks 
                   (id, start_time, end_time, block_type, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (block_id, start, end, block.block_type, metadata_json)
            )
            db.conn.commit()
    await asyncio.to_thread(_insert)
    return {"id": block_id, "status": "ok"}

@router.get("")
async def list_blocks(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    block_type: Optional[str] = None,
    limit: int = 100
):
    """List schedule blocks within a date range."""
    def _query():
        query = "SELECT * FROM schedule_blocks WHERE 1=1"
        params = []
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date)
        if end_date:
            query += " AND end_time <= ?"
            params.append(end_date)
        if block_type:
            query += " AND block_type = ?"
            params.append(block_type)
        query += " ORDER BY start_time ASC LIMIT ?"
        params.append(limit)
        cursor = db.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    blocks = await asyncio.to_thread(_query)
    return {"blocks": blocks}

@router.get("/week")
async def get_week_schedule(date: Optional[str] = None):
    """Get schedule for a week (default current week)."""
    if date:
        base = datetime.fromisoformat(date)
    else:
        base = datetime.now()
    # Find Monday of that week
    start_of_week = base - timedelta(days=base.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0)
    end_of_week = start_of_week + timedelta(days=7)
    
    def _query():
        cursor = db.conn.execute(
            "SELECT * FROM schedule_blocks WHERE start_time >= ? AND end_time <= ? ORDER BY start_time",
            (start_of_week, end_of_week)
        )
        return [dict(row) for row in cursor.fetchall()]
    blocks = await asyncio.to_thread(_query)
    # Group by day
    days = {}
    for block in blocks:
        day = block['start_time'][:10]  # YYYY-MM-DD
        if day not in days:
            days[day] = []
        days[day].append(block)
    return {"week_start": start_of_week.isoformat(), "days": days}

@router.put("/{block_id}")
async def update_block(block_id: str, update: ScheduleBlockUpdate):
    def _update():
        with db._lock:
            fields = []
            params = []
            if update.start_time is not None:
                fields.append("start_time = ?")
                params.append(datetime.fromisoformat(update.start_time))
            if update.end_time is not None:
                fields.append("end_time = ?")
                params.append(datetime.fromisoformat(update.end_time))
            if update.block_type is not None:
                fields.append("block_type = ?")
                params.append(update.block_type)
            if update.title is not None:
                fields.append("title = ?")
                params.append(update.title)
            if update.metadata is not None:
                fields.append("metadata = ?")
                params.append(json.dumps(update.metadata))
            params.append(block_id)
            if fields:
                sql = f"UPDATE schedule_blocks SET {', '.join(fields)} WHERE id = ?"
                db.conn.execute(sql, params)
                db.conn.commit()
    await asyncio.to_thread(_update)
    return {"status": "ok"}

@router.delete("/{block_id}")
async def delete_block(block_id: str):
    def _delete():
        with db._lock:
            db.conn.execute("DELETE FROM schedule_blocks WHERE id = ?", (block_id,))
            db.conn.commit()
    await asyncio.to_thread(_delete)
    return {"status": "ok"}