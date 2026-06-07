from typing import Tuple, Optional
import re

class IntentRouter:
    """Hearst, YEAH style"""
    
    INTENT_PATTERNS = {
        "task_query": [
            r"what should i (do|work on|focus on)",
            r"what('s| is) (next|my priority)",
            r"tell me what to do",
            r"what are my tasks",
            r"show me (my |)tasks",
            r"what('s| is) (blocking|stopping) me",
        ],
        "knowledge_query": [
            r"how (do|can|to|should) i",
            r"what is (a|an)?",
            r"explain",
            r"help (with|me)",
            r"how to (fix|solve|debug|implement)",
        ],
        "action": [
            r"remind me (to|that)",
            r"create (a |)(note|task)",
            r"set (a|) (reminder|timer|alarm)",
            r"open (url|website|app)",
            r"search (for|)",
        ],
        "capture": [
            r"^(note|remember|save this|log|record)",
        ],
        "reflection": [
            r"how did (i|we) (perform|do)",
            r"(this|last) week",
            r"patterns",
            r"summary",
            r"review my (day|week|month)",
        ],
        "meta": [
            r"(status|settings|configure|graph)",
        ],
    }
    
    @classmethod
    def classify(cls, message: str) -> Tuple[str, float]:
        """Returns (intent, confidence). Defaults to 'chat' if no match."""
        message_lower = message.lower().strip()
        for intent, patterns in cls.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return intent, 0.85
        return "chat", 0.6  # General chat fallback