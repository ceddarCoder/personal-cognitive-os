import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pcos.infrastructure.database import Database
from pcos.infrastructure.graph import GraphStore
from pcos.core.memory_service import MemoryService
from pcos.infrastructure.win32.state_detector import StateDetector
import logging

logger = logging.getLogger(__name__)

class ContextBuilder:
    def __init__(self):
        self.db = Database()
        self.graph = GraphStore()
        self.memory = MemoryService()
        self.state_detector = StateDetector()
    
    async def build(self, query: str, session_history: List[dict] = None) -> Dict[str, Any]:
        """Return context package for LLM."""
        # Current state
        state, confidence, signals = await asyncio.to_thread(self.state_detector.detect)
        
        # Recent notes (last day)
        recent = await asyncio.to_thread(self.db.get_recent_notes, limit=5)
        
        # Semantic search for related notes (fallback to keyword if vector missing)
        related = await asyncio.to_thread(self.memory.search, query, limit=3)
        
        # Graph context: find nodes matching query
        graph_nodes = await asyncio.to_thread(self.graph.search_nodes, query, limit=5)
        
        # Open tasks (notes with TODO, etc.)
        def get_open_tasks():
            cursor = self.db.conn.execute("""
                SELECT content FROM notes 
                WHERE content LIKE '%TODO%' OR content LIKE '%todo%' OR content LIKE '%TASK%'
                ORDER BY created_at DESC LIMIT 5
            """)
            return [row['content'] for row in cursor.fetchall()]
            
        open_tasks = await asyncio.to_thread(get_open_tasks)
        
        # Session history (last 3 exchanges)
        history = session_history[-3:] if session_history else []
        
        return {
            "current_state": state,
            "state_confidence": confidence,
            "signals": signals,
            "recent_notes": recent,
            "related_notes": related,
            "graph_context": graph_nodes,
            "open_tasks": open_tasks,
            "session_history": history,
            "query": query,
        }