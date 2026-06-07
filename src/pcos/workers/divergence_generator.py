# src/pcos/workers/divergence_generator.py
import time
import asyncio
from datetime import datetime
from pcos.infrastructure.win32.state_detector import StateDetector
from pcos.core.divergence_service import DivergenceService
from pcos.infrastructure.database import Database
from loguru import logger

def generate_divergence():
    """Generate a divergence suggestion if conditions are met."""
    detector = StateDetector()
    state, confidence, _ = detector.detect()
    
    # Only generate in states suitable for exploration
    if state not in ['distracted', 'free', 'neutral']:
        logger.debug(f"Divergence not generated: state={state} (confidence={confidence})")
        return
    
    db = Database()
    last_ts = db.get_last_divergence_time()
    if last_ts and (time.time() - last_ts.timestamp()) < 45 * 60:
        logger.debug("Divergence cooldown active (45 min)")
        return
    
    # Generate suggestion using the service (async, run in a new loop)
    service = DivergenceService()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    suggestion = loop.run_until_complete(service.generate_suggestion(state))
    
    if suggestion and suggestion.get("prompt"):
        db.insert_divergence(suggestion['prompt'], "pending")
        logger.info(f"Generated divergence suggestion: {suggestion['prompt'][:50]}...")
    else:
        logger.warning("Divergence generation returned no prompt")

def start_generator():
    """Start the background divergence generator thread."""
    logger.info("Divergence generator started (smart polling, every 10 minutes)")
    while True:
        generate_divergence()
        time.sleep(2 * 60 * 60)  # 10 minutes