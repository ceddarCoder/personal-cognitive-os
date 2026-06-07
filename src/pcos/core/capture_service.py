from pcos.infrastructure.database import Database
from pcos.infrastructure.event_bus import bus

class CaptureService:
    """Central orchestrator for note capture."""
    
    def __init__(self):
        self.db = Database()
    
    def process_capture(self, content: str, source: str = "hotkey", state: str = None, note_type: str = "note") -> str:
        """
        Save note and trigger event bus.
        Returns note_id.
        """
        # Save to database
        note_id = self.db.save_note(content, source, state, note_type=note_type)
        # Publish event for downstream workers (entity extraction, embedding, etc.)
        bus.publish("note.created", {
            "note_id": note_id,
            "content": content,
            "source": source,
            "state": state,
            "type": note_type
        })
        return note_id