import json
from pathlib import Path
from pcos.infrastructure.database import Database
from pcos.infrastructure.event_bus import bus
from loguru import logger

class BootstrapService:
    """Import ChatGPT JSON export into notes and trigger graph building."""
    
    BOOTSTRAP_FLAG = "bootstrapped.flag"
    
    def __init__(self):
        self.db = Database()
        self.data_dir = self.db.data_dir
    
    def is_bootstrapped(self) -> bool:
        return (self.data_dir / self.BOOTSTRAP_FLAG).exists()
    
    def mark_bootstrapped(self):
        (self.data_dir / self.BOOTSTRAP_FLAG).touch()
    
    def run(self, json_path: Path = None):
        """Run bootstrap. If json_path not given, look for default."""
        if self.is_bootstrapped():
            logger.info("Bootstrap already run; skipping.")
            return
        if json_path is None:
            json_path = self.data_dir / "chatgpt_export.json"
        if not json_path.exists():
            logger.warning(f"No ChatGPT export found at {json_path}. Starting with empty graph.")
            self.mark_bootstrapped()
            return
        
        logger.info(f"Bootstrapping from {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Expected format: list of {"role": "user"|"assistant", "content": ...}
        # Or a conversation structure. We'll handle common patterns.
        notes_added = 0
        if isinstance(data, list):
            for msg in data:
                if msg.get('role') == 'user' and msg.get('content'):
                    content = msg['content']
                    # Truncate long messages? Keep as is.
                    note_id = self.db.save_note(content, source="chatgpt_bootstrap")
                    # Trigger event bus for entity extraction
                    bus.publish("note.created", {
                        "note_id": note_id,
                        "content": content,
                        "source": "chatgpt_bootstrap"
                    })
                    notes_added += 1
        else:
            logger.error("Unexpected JSON format. Expected list of messages.")
        
        logger.info(f"Bootstrapped {notes_added} notes.")
        self.mark_bootstrapped()
