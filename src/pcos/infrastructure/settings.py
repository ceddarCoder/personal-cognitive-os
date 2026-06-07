import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8765
    LOG_LEVEL: str = "INFO"
    PCOS_DATA_DIR: Path = Path(os.environ.get("PCOS_DATA_DIR", "E:/pcos_data"))
    
    # New Phase 1 settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LLM_TIMEOUT: float = 30.0
    LLM_FALLBACK_ENABLED: bool = True
    
    class Config:
        extra = "ignore"

settings = Settings()

# Derived paths
# We use __dict__ to bypass pydantic extra fields protection, or we could add them as fields.
# Actually, since extra="ignore", Pydantic ignores them during initialization but complains on assignment.
# Let's bypass setattr:
object.__setattr__(settings, 'CHROMA_DIR', settings.PCOS_DATA_DIR / "chroma")
object.__setattr__(settings, 'EVENT_BUS_LOG', settings.PCOS_DATA_DIR / "event_bus_dead_letters.jsonl")
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)