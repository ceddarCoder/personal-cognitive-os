import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import json

from pcos.infrastructure.database import Database
from pcos.infrastructure.settings import settings

router = APIRouter()
db = Database()

# Directory to watch for file imports
WATCH_DIR = settings.PCOS_DATA_DIR / "watch"
WATCH_DIR.mkdir(parents=True, exist_ok=True)

class FileInfo(BaseModel):
    id: str
    name: str
    path: str
    size: int
    modified: str
    indexed: bool
    note_id: Optional[str] = None

@router.get("")
async def list_indexed_files():
    """List all files that have been indexed (stored as notes with source_type='file')."""
    def _query():
        cursor = db.conn.execute("""
            SELECT id, title, file_path, created_at, updated_at 
            FROM notes 
            WHERE source_type = 'file' AND archived = 0
            ORDER BY updated_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    files = await asyncio.to_thread(_query)
    return {"files": files}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file (PDF, MD, etc.) to the watch directory and index it."""
    # Save file to watch directory
    file_path = WATCH_DIR / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create a note for this file
    note_id = str(uuid.uuid4())
    title = file.filename
    
    # Extract text based on file type
    extracted_text = ""
    if file.filename.endswith(".md"):
        extracted_text = content.decode("utf-8")
    elif file.filename.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                extracted_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            extracted_text = f"PDF file: {file.filename} (pdfplumber not installed)"
    else:
        extracted_text = f"File: {file.filename}"
    
    def _insert():
        with db._lock:
            db.conn.execute(
                """INSERT INTO notes 
                   (id, title, content, source_type, file_path, created_at, updated_at)
                   VALUES (?, ?, ?, 'file', ?, ?, ?)""",
                (note_id, title, extracted_text, str(file_path), datetime.now(), datetime.now())
            )
            db.conn.commit()
    await asyncio.to_thread(_insert)
    
    return {"id": note_id, "status": "ok", "path": str(file_path)}

@router.post("/reindex")
async def reindex_files():
    """Scan watch directory and index any new/modified files."""
    from pcos.workers.file_watcher import index_directory
    await asyncio.to_thread(index_directory, WATCH_DIR)
    return {"status": "ok"}

@router.get("/watch-dir")
async def get_watch_dir():
    return {"path": str(WATCH_DIR)}