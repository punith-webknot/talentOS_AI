from fastapi import APIRouter

from Source.app.api.v1.chat import router as chat_router
from Source.app.api.v1.evaluation import router as evaluation_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(chat_router, prefix="/chat", tags=["Chat & Streaming"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["Evaluation"])
