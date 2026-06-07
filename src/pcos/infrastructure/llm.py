import os
from pathlib import Path
from openai import AsyncOpenAI  # Changed: AsyncOpenAI instead of OpenAI
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get("NVIDIA_API_KEY")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model = os.environ.get("LLM_MODEL", "meta/llama3-70b-instruct")  # Changed to faster model
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            self.client = AsyncOpenAI(  # Changed: AsyncOpenAI
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=120.0 #Add timeout
            )
            print(f"[LLM] Async NVIDIA NIM enabled with model: {self.model}")
        else:
            print(f"[LLM] No NVIDIA API key found. Looked in: {env_path}")
    
    async def generate(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7) -> str | None:
        """Async generate - doesn't block the server."""
        if not self.enabled:
            return None
        try:
            completion = await self.client.chat.completions.create(  # Changed: await
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=0.95,
                max_tokens=max_tokens,
                extra_body={"chat_template_kwargs": {"thinking": False}}
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return None
    
    async def generate_divergence_prompt(self, recent_notes: list, current_state: str) -> str | None:
        """Async divergence prompt."""
        if not recent_notes or len(recent_notes) < 2:
            return None
        
        notes_text = "\n".join([f"- {n['content'][:200]}" for n in recent_notes[:5]])
        prompt = f"""You are PCOS, a cognitive assistant. The user is in {current_state} state.

Recent notes:
{notes_text}

Generate ONE creative, divergent prompt that:
- Connects two seemingly unrelated notes
- Asks an open-ended question about a pattern
- Is surprising but useful
- Under 20 words

Respond with ONLY the prompt, no explanation."""
        
        return await self.generate(prompt, max_tokens=60, temperature=0.8)  # Changed: await
    
    async def generate_convergence_prompt(self, open_tasks: list, current_state: str) -> str | None:
        """Async convergence prompt."""
        if not open_tasks:
            return None
        
        tasks_text = "\n".join([f"- {task[:100]}" for task in open_tasks[:3]])
        prompt = f"""You are PCOS, a cognitive assistant. The user is in {current_state} state.

Open tasks/notes:
{tasks_text}

Generate ONE concrete action prompt that:
- Starts with a verb (Write, Call, Open, Delete, Defer, Reply)
- Is completable in under 5 minutes
- References a specific open task
- Under 15 words

Respond with ONLY the prompt, no explanation."""
        
        return await self.generate(prompt, max_tokens=50, temperature=0.6)  # Changed: await