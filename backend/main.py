from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import health, upload, chat
from services.session_manager import session_manager
from core.logging import logger, log_event, LogCategory

# Create FastAPI app
app = FastAPI(
    title="RAG API", 
    description="API for the RAG backend",
    version="1.0.0")

# Add middleware
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Register routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(chat.router)

@app.on_event("startup")
async def startup_event():
    """Clean up expired sessions and start background tasks."""
    log_event(LogCategory.SYSTEM, "INFO", "Starting up the RAG backend")
    session_manager.cleanup_expired_sessions()
    active_count = len(session_manager.get_all_sessions())
    log_event(LogCategory.SYSTEM, "INFO", f"Active sessions: {active_count}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to the RAG backend",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "upload": "/upload",
            "chat": "/chat"
        }    
    }