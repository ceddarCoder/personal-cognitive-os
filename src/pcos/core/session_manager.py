import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from pcos.infrastructure.settings import settings

class ChatSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict] = []
        self.created_at = datetime.now()
        self.last_active = datetime.now()
    
    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_active = datetime.now()
    
    def get_history(self, max_turns: int = 10) -> List[Dict]:
        return self.messages[-max_turns:]

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.persist_path = settings.PCOS_DATA_DIR / "sessions"
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self._load_all()
    
    def _load_all(self):
        for f in self.persist_path.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                session = ChatSession(data["session_id"])
                session.messages = data["messages"]
                session.created_at = datetime.fromisoformat(data["created_at"])
                session.last_active = datetime.fromisoformat(data["last_active"])
                self.sessions[session.session_id] = session
            except Exception:
                pass
    
    def _persist(self, session: ChatSession):
        path = self.persist_path / f"{session.session_id}.json"
        path.write_text(json.dumps({
            "session_id": session.session_id,
            "messages": session.messages,
            "created_at": session.created_at.isoformat(),
            "last_active": session.last_active.isoformat(),
        }))
    
    def get_or_create(self, session_id: str = None) -> ChatSession:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        new_id = session_id or str(uuid.uuid4())
        session = ChatSession(new_id)
        self.sessions[new_id] = session
        self._persist(session)
        return session
    
    def update(self, session: ChatSession):
        self._persist(session)
    
    def cleanup(self, max_idle_minutes: int = 120):
        """Remove sessions idle longer than max_idle_minutes."""
        now = datetime.now()
        to_remove = []
        for sid, s in self.sessions.items():
            if (now - s.last_active).total_seconds() > max_idle_minutes * 60:
                to_remove.append(sid)
        for sid in to_remove:
            del self.sessions[sid]
            (self.persist_path / f"{sid}.json").unlink(missing_ok=True)