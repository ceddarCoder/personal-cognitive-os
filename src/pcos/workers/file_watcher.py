from datetime import datetime
import os
import time
import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pcos.infrastructure.database import Database
from pcos.infrastructure.event_bus import bus
from loguru import logger

class FileIndexer(FileSystemEventHandler):
    def __init__(self):
        self.db = Database()
    
    def on_created(self, event):
        if not event.is_directory:
            self.index_file(event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory:
            self.index_file(event.src_path)
    
    def index_file(self, file_path):
        path = Path(file_path)
        if path.suffix.lower() not in ['.md', '.pdf', '.txt']:
            return
        
        # Check if already indexed
        cursor = self.db.conn.execute(
            "SELECT id FROM notes WHERE file_path = ?", (str(path),)
        )
        existing = cursor.fetchone()
        
        # Extract title and content
        content = ""
        title = path.stem
        if path.suffix.lower() == '.md':
            content = path.read_text(encoding='utf-8')
        elif path.suffix.lower() == '.pdf':
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    content = "\n".join(page.extract_text() or "" for page in pdf.pages)
            except ImportError:
                content = f"PDF file: {path.name}"
        else:
            content = path.read_text(encoding='utf-8')
        
        if existing:
            # Update existing note
            self.db.conn.execute(
                "UPDATE notes SET content = ?, updated_at = ? WHERE file_path = ?",
                (content, datetime.now(), str(path))
            )
        else:
            # Create new note
            import uuid
            note_id = str(uuid.uuid4())
            self.db.conn.execute(
                """INSERT INTO notes 
                   (id, title, content, source_type, file_path, created_at, updated_at)
                   VALUES (?, ?, ?, 'file', ?, ?, ?)""",
                (note_id, title, content, str(path), datetime.now(), datetime.now())
            )
        self.db.conn.commit()
        bus.publish("note.created", {"note_id": note_id, "content": content})
        logger.info(f"Indexed file: {path}")

def index_directory(directory: Path):
    """Manually index all files in the given directory."""
    handler = FileIndexer()
    for file_path in directory.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.md', '.pdf', '.txt']:
            handler.index_file(str(file_path))
    logger.info(f"Manual indexing completed for {directory}")

def start_watchdog(watch_path: Path):
    event_handler = FileIndexer()
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=True)
    observer.start()
    logger.info(f"File watcher started on {watch_path}")
    return observer