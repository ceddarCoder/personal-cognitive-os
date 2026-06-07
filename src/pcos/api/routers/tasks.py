import json
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pcos.infrastructure.database import Database
import uuid

router = APIRouter()
db = Database()

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # high, medium, low
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    source: str = "webapp"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None  # open, in_progress, review, done

@router.post("")
async def create_task(task: TaskCreate):
    """Create a new task (stored as a note with type='task')."""
    task_id = str(uuid.uuid4())
    content = task.description or ""
    tags_json = json.dumps(task.tags or [])
    due_date = datetime.fromisoformat(task.due_date) if task.due_date else None

    def _insert():
        with db._lock:
            db.conn.execute(
                """INSERT INTO notes 
                   (id, title, content, type, priority, due_date, tags, source, created_at, updated_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, task.title, content, "task", task.priority, due_date, 
                 tags_json, task.source, datetime.now(), datetime.now(), "open")
            )
            db.conn.commit()
    await asyncio.to_thread(_insert)
    return {"id": task_id, "status": "ok"}

@router.get("")
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List tasks with optional filters."""
    def _query():
        query = "SELECT id, title, content, priority, due_date, tags, status, created_at, updated_at FROM notes WHERE type = 'task' AND archived = 0"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        query += " ORDER BY due_date IS NULL, due_date ASC, priority DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = db.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    tasks = await asyncio.to_thread(_query)
    return {"tasks": tasks, "total": len(tasks)}

@router.get("/{task_id}")
async def get_task(task_id: str):
    def _get():
        cursor = db.conn.execute(
            "SELECT * FROM notes WHERE id = ? AND type = 'task'", (task_id,)
        )
        return dict(cursor.fetchone()) if cursor.fetchone() else None
    task = await asyncio.to_thread(_get)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}")
async def update_task(task_id: str, update: TaskUpdate):
    """Update task fields."""
    def _update():
        with db._lock:
            fields = []
            params = []
            if update.title is not None:
                fields.append("title = ?")
                params.append(update.title)
            if update.description is not None:
                fields.append("content = ?")
                params.append(update.description)
            if update.priority is not None:
                fields.append("priority = ?")
                params.append(update.priority)
            if update.due_date is not None:
                fields.append("due_date = ?")
                params.append(datetime.fromisoformat(update.due_date) if update.due_date else None)
            if update.tags is not None:
                fields.append("tags = ?")
                params.append(json.dumps(update.tags))
            if update.status is not None:
                fields.append("status = ?")
                params.append(update.status)
                if update.status == "done":
                    fields.append("completed_at = ?")
                    params.append(datetime.now())
            fields.append("updated_at = ?")
            params.append(datetime.now())
            params.append(task_id)
            if fields:
                sql = f"UPDATE notes SET {', '.join(fields)} WHERE id = ?"
                db.conn.execute(sql, params)
                db.conn.commit()
    await asyncio.to_thread(_update)
    return {"status": "ok"}

@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Soft delete (archive) a task."""
    def _delete():
        with db._lock:
            db.conn.execute(
                "UPDATE notes SET archived = 1, updated_at = ? WHERE id = ?",
                (datetime.now(), task_id)
            )
            db.conn.commit()
    await asyncio.to_thread(_delete)
    return {"status": "ok"}