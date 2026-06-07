import re
from pcos.infrastructure.event_bus import bus
from pcos.infrastructure.graph import GraphStore
from pcos.infrastructure.database import Database
from loguru import logger

class EntityExtractor:
    def __init__(self):
        self.graph = GraphStore()
        self.db = Database()
        logger.info("EntityExtractor initialized")

    def extract(self, note_id: str, content: str):
        # Existing extraction logic (rule-based)
        patterns = {
            'project': r'#project:(\w+)',
            'person': r'@(\w+)',
            'todo': r'TODO:?\s*(.+?)(?=\n|$)',
            'goal': r'GOAL:?\s*(.+?)(?=\n|$)',
            'tool': r'tool:(\w+)',
            'interest': r'interest:(\w+)'
        }
        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if entity_type in ('todo', 'goal'):
                    continue
                name = match.strip()
                node_id = self.graph.add_node(
                    node_type=entity_type,
                    name=name,
                    confidence=0.7,
                    source="auto_extract"
                )
                user_node = self._get_or_create_user_node()
                self.graph.add_edge(
                    source_id=user_node,
                    target_id=node_id,
                    relation=f"has_{entity_type}",
                    confidence=0.7,
                    source="auto_extract"
                )
        blocking = re.findall(r'(\w+)\s+(?:is blocking|blocks)\s+(\w+)', content, re.IGNORECASE)
        for blocker, blocked in blocking:
            blocker_id = self._get_or_create_concept_node(blocker)
            blocked_id = self._get_or_create_concept_node(blocked)
            if blocker_id and blocked_id:
                self.graph.add_edge(blocker_id, blocked_id, relation="blocks", confidence=0.6, source="auto_extract")

    def _get_or_create_user_node(self) -> str:
        nodes = self.graph.search_nodes("user", node_type="user")
        for n in nodes:
            if n['name'].lower() == "me":
                return n['id']
        return self.graph.add_node("user", "me", confidence=1.0, source="system")

    def _get_or_create_concept_node(self, concept: str) -> str:
        nodes = self.graph.search_nodes(concept, node_type="concept")
        for n in nodes:
            if n['name'].lower() == concept.lower():
                return n['id']
        return self.graph.add_node("concept", concept, confidence=0.5, source="auto_extract")

def start_entity_extractor():
    """Call this from FastAPI lifespan to activate the extractor."""
    extractor = EntityExtractor()
    def on_note_created(data):
        note_id = data['note_id']
        content = data['content']
        extractor.extract(note_id, content)
    bus.subscribe("note.created", on_note_created)
    logger.info("EntityExtractor subscribed to note.created")