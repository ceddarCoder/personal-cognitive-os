import asyncio
import json
import re
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from pcos.infrastructure.database import Database
import uuid

router = APIRouter()
db = Database()

class NoteCreate(BaseModel):
    title: Optional[str] = None
    content: str
    tags: Optional[List[str]] = None
    type: str = "note"  # note, task, idea, file
    priority: str = "low"
    due_date: Optional[str] = None
    source: str = "webapp"

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    archived: Optional[bool] = None

def extract_backlinks(content: str) -> List[str]:
    """Find wikilinks [[link]] in markdown content."""
    return re.findall(r'\[\[(.*?)\]\]', content)

@router.post("")
async def create_note(note: NoteCreate):
    """Create a new note."""
    note_id = str(uuid.uuid4())
    title = note.title or note.content[:50] if note.content else "Untitled"
    tags_json = json.dumps(note.tags or [])
    due_date = datetime.fromisoformat(note.due_date) if note.due_date else None

    def _insert():
        with db._lock:
            db.conn.execute(
                """INSERT INTO notes 
                   (id, title, content, tags, type, priority, due_date, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (note_id, title, note.content, tags_json, note.type, 
                 note.priority, due_date, note.source, datetime.now(), datetime.now())
            )
            db.conn.commit()
    await asyncio.to_thread(_insert)
    
    # Optionally, trigger backlink indexing in a background task
    backlinks = extract_backlinks(note.content)
    if backlinks:
        # Store backlinks in a separate table? For now, just log.
        # We'll implement a proper backlink table later if needed.
        pass
    
    return {"id": note_id, "status": "ok"}

from fastapi import Query
import asyncio

@router.get("/search")
async def search_notes(q: str = Query(..., min_length=1), limit: int = 10):
    from pcos.core.memory_service import MemoryService
    memory = MemoryService()
    results = await asyncio.to_thread(memory.search, q, limit)
    return {"query": q, "results": results}


@router.get("")
async def list_notes(
    limit: int = 50,
    offset: int = 0,
    tag: Optional[str] = None,
    type: Optional[str] = None,
    archived: bool = False
):
    """List notes with optional tag and type filters."""
    def _query():
        query = "SELECT id, title, content, tags, type, priority, due_date, created_at, updated_at FROM notes WHERE archived = ?"
        params = [1 if archived else 0]
        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        if type:
            query += " AND type = ?"
            params.append(type)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = db.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    notes = await asyncio.to_thread(_query)
    return {"notes": notes, "total": len(notes)}

@router.get("/{note_id}")
async def get_note(note_id: str):
    def _get():
        cursor = db.conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    note = await asyncio.to_thread(_get)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    # Extract backlinks from content
    if note.get("content"):
        note["backlinks"] = extract_backlinks(note["content"])
    return note

@router.put("/{note_id}")
async def update_note(note_id: str, update: NoteUpdate):
    """Update a note (partial update)."""
    def _update():
        with db._lock:
            # Build dynamic SET clause
            fields = []
            params = []
            if update.title is not None:
                fields.append("title = ?")
                params.append(update.title)
            if update.content is not None:
                fields.append("content = ?")
                params.append(update.content)
            if update.tags is not None:
                fields.append("tags = ?")
                params.append(json.dumps(update.tags))
            if update.type is not None:
                fields.append("type = ?")
                params.append(update.type)
            if update.priority is not None:
                fields.append("priority = ?")
                params.append(update.priority)
            if update.due_date is not None:
                fields.append("due_date = ?")
                params.append(datetime.fromisoformat(update.due_date) if update.due_date else None)
            if update.archived is not None:
                fields.append("archived = ?")
                params.append(1 if update.archived else 0)
            fields.append("updated_at = ?")
            params.append(datetime.now())
            params.append(note_id)
            if fields:
                sql = f"UPDATE notes SET {', '.join(fields)} WHERE id = ?"
                db.conn.execute(sql, params)
                db.conn.commit()
    await asyncio.to_thread(_update)
    return {"status": "ok"}

@router.delete("/{note_id}")
async def delete_note(note_id: str, hard: bool = False):
    """Delete note. If hard=True, permanently delete; else archive."""
    def _delete():
        with db._lock:
            if hard:
                db.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
                # Also delete from embeddings table
                db.conn.execute("DELETE FROM embeddings WHERE note_id = ?", (note_id,))
            else:
                db.conn.execute("UPDATE notes SET archived = 1, updated_at = ? WHERE id = ?", (datetime.now(), note_id))
            db.conn.commit()
    await asyncio.to_thread(_delete)
    return {"status": "ok"}

@router.get("/{note_id}/backlinks")
async def get_backlinks(note_id: str):
    """Find notes that link to this note via wikilink."""
    def _query():
        # First get the note's title (if any)
        cursor = db.conn.execute("SELECT title FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row or not row['title']:
            return []
        title = row['title']
        # Search for [[title]] in other notes' content
        cursor = db.conn.execute(
            "SELECT id, title, content FROM notes WHERE content LIKE ? AND id != ?",
            (f'%[[{title}]]%', note_id)
        )
        return [dict(row) for row in cursor.fetchall()]
    backlinks = await asyncio.to_thread(_query)
    return {"backlinks": backlinks}