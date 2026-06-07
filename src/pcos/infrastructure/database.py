import sqlite3
import uuid
import threading
from pathlib import Path
from datetime import datetime  # Add this import
from pcos.infrastructure.settings import settings

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance
    
    def _init_db(self):
        self.data_dir = settings.PCOS_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "pcos.db"
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.initialize()
    
    def initialize(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                state_at_capture TEXT
            );
            
            CREATE TABLE IF NOT EXISTS state_log (
                id TEXT PRIMARY KEY,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                state TEXT,
                confidence REAL,
                reason TEXT,
                signals_json TEXT
            );
            
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY,
                note_id TEXT,
                suggestion_type TEXT,
                suggested_at DATETIME,
                suggested_content TEXT,
                trigger_reason TEXT,
                user_state_at_time TEXT,
                user_response TEXT,
                responded_at DATETIME
            );
            
            -- NEW: Graph nodes
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                confidence REAL DEFAULT 1.0,
                source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- NEW: Graph edges
            CREATE TABLE IF NOT EXISTS graph_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES graph_nodes(id),
                FOREIGN KEY (target_id) REFERENCES graph_nodes(id)
            );
            
            -- NEW: Embeddings mapping (links note_id to ChromaDB ID)
            CREATE TABLE IF NOT EXISTS embeddings (
                note_id TEXT PRIMARY KEY,
                chroma_id TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes(id)
            );
            
            -- NEW: Inferred schedule blocks
            CREATE TABLE IF NOT EXISTS schedule_blocks (
                id TEXT PRIMARY KEY,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                block_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source TEXT,
                metadata TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
                                
            CREATE TABLE IF NOT EXISTS divergence_queue (
                id TEXT PRIMARY KEY,
                suggestion TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                state TEXT,
                context TEXT,
                status TEXT DEFAULT 'pending', -- pending, delivered, accepted, dismissed, expired
                delivered_at DATETIME,
                responded_at DATETIME
            );
            
            -- Indexes for graph performance
            CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_relation ON graph_edges(relation);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph_nodes(type);
            CREATE INDEX IF NOT EXISTS idx_schedule_time ON schedule_blocks(start_time, end_time);
        ''')
        self.conn.commit()
        
        # Migrations: add type/task columns if missing
        for sql in [
            "ALTER TABLE notes ADD COLUMN type TEXT DEFAULT 'note'",
            "ALTER TABLE notes ADD COLUMN completed_at DATETIME",
            "ALTER TABLE notes ADD COLUMN priority TEXT DEFAULT 'low'",
            "ALTER TABLE embeddings ADD COLUMN deleted INTEGER DEFAULT 0",
            "ALTER TABLE notes ADD COLUMN title TEXT",
            "ALTER TABLE notes ADD COLUMN tags TEXT",
            "ALTER TABLE notes ADD COLUMN due_date DATE",
            "ALTER TABLE notes ADD COLUMN file_path TEXT",
            "ALTER TABLE notes ADD COLUMN source_type TEXT DEFAULT 'capture'",
            "ALTER TABLE notes ADD COLUMN archived INTEGER DEFAULT 0",
            "ALTER TABLE notes ADD COLUMN status TEXT DEFAULT 'open'",
            "ALTER TABLE notes ADD COLUMN due_date DATE",
        ]:
            try:
                self.conn.execute(sql)
                self.conn.commit()
            except Exception:
                pass  # Column already exists

        columns_to_add = [
            ("type", "TEXT DEFAULT 'note'"),
            ("completed_at", "DATETIME"),
            ("priority", "TEXT DEFAULT 'low'"),
            ("title", "TEXT"),
            ("tags", "TEXT"),
            ("due_date", "DATE"),
            ("file_path", "TEXT"),
            ("source_type", "TEXT DEFAULT 'capture'"),
            ("archived", "INTEGER DEFAULT 0"),
            ("updated_at", "DATETIME"),   # also add updated_at for tracking edits
        ]
        for col_name, col_def in columns_to_add:
            try:
                self.conn.execute(f"ALTER TABLE notes ADD COLUMN {col_name} {col_def}")
                self.conn.commit()
            except sqlite3.OperationalError:
                # Column already exists – ignore
                pass
    
    def save_note(self, content, source="hotkey", state=None, note_type="note", priority="low"):
        note_id = str(uuid.uuid4())
        with self._lock:
            self.conn.execute(
                "INSERT INTO notes (id, content, source, state_at_capture, type, priority) VALUES (?,?,?,?,?,?)",
                (note_id, content, source, state, note_type, priority)
            )
            self.conn.commit()
        return note_id
    
    def log_action(self, suggestion_type, suggested_content, trigger_reason, user_state, note_id=None, user_response=None):
        """Log user actions for feedback learning."""
        action_id = str(uuid.uuid4())
        try:
            with self._lock:
                self.conn.execute(
                    """INSERT INTO actions 
                    (id, note_id, suggestion_type, suggested_at, suggested_content, trigger_reason, user_state_at_time, user_response)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (action_id, note_id, suggestion_type, datetime.now(), suggested_content, trigger_reason, user_state, user_response)
                )
                self.conn.commit()
        except Exception as e:
            print(f"Failed to log action: {e}")
    
    def log_state(self, state, confidence, reason, signals_json):
        """Log a detected state to the state_log table (thread-safe)."""
        state_id = str(uuid.uuid4())
        try:
            with self._lock:
                self.conn.execute(
                    "INSERT INTO state_log (id, detected_at, state, confidence, reason, signals_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (state_id, datetime.now(), state, confidence, reason, signals_json)
                )
                self.conn.commit()
        except Exception as e:
            print(f"Failed to log state: {e}")
            
    # ---- New helper methods ----
    def get_recent_notes(self, limit=10):
        with self._lock:
            cursor = self.conn.execute(
                "SELECT id, content, created_at, source, state_at_capture FROM notes ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_current_state(self):
        """Get the most recently detected state."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT state, confidence, signals_json FROM state_log ORDER BY detected_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                import json
                signals = {}
                try:
                    signals = json.loads(row['signals_json'])
                except Exception:
                    pass
                return {"state": row['state'], "confidence": row['confidence'], "signals": signals}
            return {"state": "neutral", "confidence": 0, "signals": {}}
    
    def get_notes_without_embeddings(self):
        with self._lock:
            cursor = self.conn.execute('''
                SELECT n.id, n.content FROM notes n
                LEFT JOIN embeddings e ON n.id = e.note_id
                WHERE e.note_id IS NULL
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_note_by_id(self, note_id):
        with self._lock:
            cursor = self.conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_open_tasks(self):
        """Get tasks that are not yet completed."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT id, content, created_at, priority FROM notes WHERE type = 'task' AND completed_at IS NULL ORDER BY created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def complete_task(self, task_id):
        """Mark a task as completed."""
        with self._lock:
            self.conn.execute(
                "UPDATE notes SET completed_at = ? WHERE id = ?",
                (datetime.now(), task_id)
            )
            self.conn.commit()
    def get_tasks_by_status(self, status):
        with self._lock:
            cursor = self.conn.execute(
                "SELECT * FROM notes WHERE type = 'task' AND status = ? ORDER BY due_date ASC",
                (status,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_task_status(self, task_id, status):
        with self._lock:
            self.conn.execute("UPDATE notes SET status = ?, updated_at = ? WHERE id = ?", (status, datetime.now(), task_id))
            self.conn.commit()
    
    def get_divergence_queue_items(self, status='pending'):
        """Get divergence queue items by status."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT id, suggestion, created_at, state, context, status FROM divergence_queue WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_last_divergence_time(self):
        """Return timestamp of the most recent divergence insertion, or 0 if none."""
        cursor = self.conn.execute(
            "SELECT MAX(created_at) as last FROM divergence_queue"
        )
        row = cursor.fetchone()
        if row and row['last']:
            try:
                # SQLite datetime strings usually look like "2026-05-05 14:00:00.123456"
                if isinstance(row['last'], str):
                    return datetime.fromisoformat(row['last'])
                return row['last']
            except Exception:
                pass
        return 0

    def insert_divergence(self, suggestion: str, status: str = "pending"):
        import uuid
        qid = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO divergence_queue (id, suggestion, status, created_at) VALUES (?, ?, ?, ?)",
            (qid, suggestion, status, datetime.now())
        )
        self.conn.commit()
        return qid