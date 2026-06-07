from fastapi import APIRouter
from pcos.core.convergence_service import ConvergenceService
import asyncio

router = APIRouter()
service = ConvergenceService()

@router.get("")
async def get_convergence_suggestion(current_state: str = "neutral"):
    """Get a convergence suggestion based on open tasks."""
    # Run synchronous service method in a thread to avoid blocking the event loop
    result = await service.generate_suggestion(current_state)
    return result