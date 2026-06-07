from pcos.infrastructure.database import Database
from pcos.infrastructure.graph import GraphStore
from pcos.infrastructure.vector_store import VectorStore

class MemoryService:
    def __init__(self):
        self.db = Database()
        self.vector_store = VectorStore()
        self.graph = GraphStore()

    def search(self, query: str, limit: int = 10):
        semantic_results = self.vector_store.search(query, limit)
        if semantic_results:
            notes = []
            for res in semantic_results:
                note = self.db.get_note_by_id(res['id'])
                if note:
                    note['score'] = 1.0 - res['distance']
                    notes.append(note)
            return notes
        else:
            # fallback keyword search
            cursor = self.db.conn.execute(
                "SELECT * FROM notes WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit)
            )
            return [dict(row) for row in cursor.fetchall()]