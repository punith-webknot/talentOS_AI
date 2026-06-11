from fastapi import APIRouter

# Import only your actual endpoints
from source.app.api.v1.chat import router as chat_router

api_router = APIRouter(prefix="/api/v1")

# Mount the chat endpoint
api_router.include_router(chat_router, prefix="/chat", tags=["Chat & Streaming"])