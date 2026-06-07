from pcos.infrastructure.database import Database
from pcos.infrastructure.llm import LLMClient
import asyncio

class ConvergenceService:
    def __init__(self):
        self.db = Database()
        self.llm = LLMClient()
    
    def get_open_tasks(self) -> list:
        """Get notes that are likely tasks."""
        cursor = self.db.conn.execute("""
            SELECT content FROM notes 
            WHERE content LIKE '%todo%' 
               OR content LIKE '%need to%'
               OR content LIKE '%should%'
               OR content LIKE '%ACTION%'
               OR content LIKE '%task%'
            ORDER BY created_at DESC LIMIT 5
        """)
        return [row['content'] for row in cursor.fetchall()]
    
    async def generate_suggestion(self, current_state: str = "neutral") -> dict | None:
        """Generate a convergence suggestion based on open tasks."""
        # Run synchronous DB query in thread to avoid blocking the event loop
        tasks = await asyncio.to_thread(self.get_open_tasks)
        
        if not tasks:
            return {
                "type": "convergence",
                "prompt": "No open tasks found. Capture tasks with words like 'todo', 'need to', or 'should'.",
                "context_tasks": []
            }
        
        prompt = await self.llm.generate_convergence_prompt(tasks, current_state)
        if not prompt:
            # Fallback prompt
            prompt = f"ACTION: Look at '{tasks[0][:50]}...' and do the smallest possible step right now."
        
        return {
            "type": "convergence",
            "prompt": prompt,
            "context_tasks": tasks[:3]
        }