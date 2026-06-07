from pcos.infrastructure.database import Database
from pcos.infrastructure.llm import LLMClient

class DivergenceService:
    def __init__(self):
        self.db = Database()
        self.llm = LLMClient()
    
    def get_recent_notes(self, limit: int = 5) -> list:
        cursor = self.db.conn.execute(
            "SELECT content, created_at FROM notes ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    async def generate_suggestion(self, current_state: str = "neutral") -> dict | None:
        """Generate a divergence suggestion based on recent notes."""
        notes = self.get_recent_notes()
        if len(notes) < 2:
            return {
                "type": "divergence",
                "prompt": "Capture at least 2 notes to enable divergence suggestions.",
                "context_notes": []
            }
        
        prompt = await self.llm.generate_divergence_prompt(notes, current_state)
        if not prompt:
            # Fallback prompt (LLM unavailable)
            prompt = f"Your last note: '{notes[0]['content'][:60]}...' How does this connect to something you thought about earlier?"
        
        return {
            "type": "divergence",
            "prompt": prompt,
            "context_notes": [n['content'][:100] for n in notes[:3]]
        }