from pcos.infrastructure.event_bus import bus
from pcos.infrastructure.vector_store import VectorStore
from pcos.infrastructure.database import Database
from loguru import logger

vector_store = VectorStore()
db = Database()

def embed_note(note_id: str, content: str):
    try:
        vector_store.add_note(note_id, content)
        logger.debug(f"Embedded note {note_id[:8]}")
    except Exception as e:
        logger.error(f"Failed to embed note {note_id}: {e}")

def on_note_created(data):
    note_id = data['note_id']
    content = data['content']
    embed_note(note_id, content)

def backfill():
    """Embed all notes that are not yet in the vector store."""
    cursor = db.conn.execute("""
        SELECT n.id, n.content FROM notes n
        LEFT JOIN embeddings e ON n.id = e.note_id
        WHERE e.note_id IS NULL
    """)
    notes = cursor.fetchall()
    for note in notes:
        embed_note(note['id'], note['content'])
    logger.info(f"Backfilled {len(notes)} notes")

def start_worker():
    bus.subscribe("note.created", on_note_created)
    backfill()
    logger.info("Embedding worker started with FAISS")