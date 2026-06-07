from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pcos.core.capture_service import CaptureService
from pcos.workers.state_monitor import get_state_detector
from pcos.infrastructure.settings import settings

router = APIRouter()

class CaptureRequest(BaseModel):
    content: str
    source: str = "hotkey"
    state: str = None
    type: str = "note"  # note, task, idea

@router.post("")
async def capture(request: CaptureRequest):
    try:
        import asyncio
        service = CaptureService()
        state = request.state
        if not state:
            detector = get_state_detector()
            state, _, _ = await asyncio.to_thread(detector.detect)
            
        note_id = await asyncio.to_thread(
            service.process_capture, 
            request.content, 
            request.source, 
            state, 
            note_type=request.type
        )
        return {"status": "ok", "id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))