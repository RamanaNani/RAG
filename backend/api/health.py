from fastapi import APIRouter
from models.responses import HealthResponse
from services.session_manager import session_manager

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    active_sessions = len(session_manager.get_all_sessions())
    return HealthResponse(
        status="healthy",
        active_sessions=active_sessions
    )