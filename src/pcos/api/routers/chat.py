from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pcos.core.intent_router import IntentRouter
from pcos.core.context_builder import ContextBuilder
from pcos.core.session_manager import SessionManager
from pcos.infrastructure.llm import LLMClient
import asyncio
import time
import logging

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chat")

router = APIRouter()
context_builder = ContextBuilder()
session_manager = SessionManager()
llm = LLMClient()

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@router.post("")
async def chat(request: ChatRequest):
    start = time.time()
    logger.info("---- /chat START ----")

    try:
        logger.info(f"[1] message: {request.message}")

        # Intent classification
        t = time.time()
        intent, confidence = IntentRouter.classify(request.message)
        logger.info(f"[2] intent={intent}, confidence={confidence} ({time.time()-t:.2f}s)")

        # Session handling
        t = time.time()
        session = session_manager.get_or_create(request.session_id)
        session.add_message("user", request.message)
        logger.info(f"[3] session ready ({time.time()-t:.2f}s)")

        # Context building (timeout protected)
        t = time.time()
        try:
            context = await asyncio.wait_for(
                context_builder.build(request.message, session.get_history()),
                timeout=10
            )
        except asyncio.TimeoutError:
            logger.error("[4] context builder TIMEOUT")
            raise HTTPException(status_code=504, detail="Context builder timeout")

        logger.info(f"[4] context built ({time.time()-t:.2f}s)")

        context["intent"] = intent
        context["intent_confidence"] = confidence

        # Prompt creation
        prompt = f"""You are PCOS, a personal cognitive assistant.
Intent: {intent}
User state: {context.get('current_state')}
Recent notes: {context.get('recent_notes', [])[:3]}
User query: {request.message}
Respond helpfully, concisely."""
        logger.info("[5] prompt ready")

        # LLM call (CRITICAL: timeout)
        t = time.time()
        try:
            response = await asyncio.wait_for(
                llm.generate(prompt),
                timeout=60
            )
        except asyncio.TimeoutError:
            logger.error("[6] LLM TIMEOUT")
            raise HTTPException(status_code=504, detail="LLM timeout")

        logger.info(f"[6] LLM response received ({time.time()-t:.2f}s)")

        if not response:
            response = "I need more context to help."

        # Save session
        session.add_message("assistant", response)
        session_manager.update(session)
        logger.info("[7] session updated")

        total = time.time() - start
        logger.info(f"---- DONE in {total:.2f}s ----")

        return {
            "response": response,
            "session_id": session.session_id,
            "intent": intent
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("UNEXPECTED ERROR")
        raise HTTPException(status_code=500, detail=str(e))