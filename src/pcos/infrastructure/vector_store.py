import faiss
import numpy as np
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
from pcos.infrastructure.settings import settings
from pcos.infrastructure.database import Database
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.settings = settings
        self.db = Database()
        self.index_path = self.settings.PCOS_DATA_DIR / "faiss.index"
        self.metadata_path = self.settings.PCOS_DATA_DIR / "faiss_meta.pkl"
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self._load_index()

    def _load_index(self):
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
            logger.info(f"Loaded index with {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatL2(384)
            self.metadata = {}
            logger.info("Created new FAISS index")

    def _save_index(self):
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

    def add_note(self, note_id: str, content: str, metadata: dict = None):
        embedding = self.model.encode(content).astype(np.float32)
        self.index.add(embedding.reshape(1, -1))
        pos = self.index.ntotal - 1
        self.metadata[pos] = {"id": note_id, "content": content, "extra": metadata or {}}
        self._save_index()
        self.db.conn.execute(
            "INSERT OR REPLACE INTO embeddings (note_id, chroma_id, deleted) VALUES (?, ?, 0)",
            (note_id, str(pos))
        )
        self.db.conn.commit()
        logger.info(f"Added vector for note {note_id[:8]} at position {pos}")

    def search(self, query: str, limit: int = 5):
        if self.index.ntotal == 0:
            return []
        query_embedding = self.model.encode(query).astype(np.float32).reshape(1, -1)
        distances, indices = self.index.search(query_embedding, limit * 2)  # fetch extras to skip deleted
        results = []
        for idx in indices[0]:
            if idx == -1:
                continue
            meta = self.metadata.get(int(idx))
            if not meta:
                continue
            note_id = meta['id']
            cursor = self.db.conn.execute("SELECT deleted FROM embeddings WHERE note_id = ?", (note_id,))
            row = cursor.fetchone()
            if row and row['deleted']:
                continue
            results.append({
                'id': note_id,
                'content': meta['content'],
                'metadata': meta['extra'],
                'distance': float(distances[0][list(indices[0]).index(idx)])
            })
            if len(results) >= limit:
                break
        return results

    def soft_delete(self, note_id: str):
        """Mark note as deleted in the database (no index rebuild)."""
        self.db.conn.execute("UPDATE embeddings SET deleted = 1 WHERE note_id = ?", (note_id,))
        self.db.conn.commit()
        logger.info(f"Soft-deleted note {note_id[:8]}")

    def hard_delete(self, note_id: str):
        """Physically remove vector by rebuilding the index."""
        self.soft_delete(note_id)
        self.rebuild_index()

    def rebuild_index(self):
        """Rebuild FAISS index from all non-deleted notes."""
        logger.info("Rebuilding FAISS index (hard delete in progress)...")
        cursor = self.db.conn.execute("""
            SELECT n.id, n.content
            FROM notes n
            JOIN embeddings e ON n.id = e.note_id
            WHERE e.deleted = 0
        """)
        active_notes = cursor.fetchall()
        if not active_notes:
            self.index = faiss.IndexFlatL2(384)
            self.metadata = {}
            self._save_index()
            logger.info("Index rebuilt empty")
            return

        new_index = faiss.IndexFlatL2(384)
        new_metadata = {}
        embeddings = []
        for note in active_notes:
            emb = self.model.encode(note['content']).astype(np.float32)
            embeddings.append(emb)
            new_metadata[len(new_metadata)] = {"id": note['id'], "content": note['content'], "extra": {}}
        if embeddings:
            vectors = np.vstack(embeddings)
            new_index.add(vectors)

        self.index = new_index
        self.metadata = new_metadata
        self._save_index()
        # update chroma_id to new positions
        for pos, note in enumerate(active_notes):
            self.db.conn.execute("UPDATE embeddings SET chroma_id = ? WHERE note_id = ?", (str(pos), note['id']))
        self.db.conn.commit()
        logger.info(f"Index rebuilt with {len(active_notes)} vectors")

    def delete_note(self, note_id: str):
        """Public method: hard delete."""
        self.hard_delete(note_id)

    def count(self):
        return self.index.ntotal