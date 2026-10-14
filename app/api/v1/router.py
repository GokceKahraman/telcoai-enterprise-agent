from fastapi import APIRouter, Depends, Request

from app import __version__
from app.api.dependencies import require_access
from app.api.v1.chat import router as chat_router
from app.api.v1.demo_actions import router as demo_router
from app.api.v1.sessions import router as session_router

api_v1_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_access)])
api_v1_router.include_router(chat_router)
api_v1_router.include_router(demo_router)
api_v1_router.include_router(session_router)


@api_v1_router.get("/status", tags=["operations"])
def status(request: Request) -> dict:
    runtime = request.app.state.runtime
    settings = runtime.settings
    return {
        "mode": "demo" if settings.retrieval_strategy == "keyword" else "enterprise",
        "retrieval": settings.retrieval_strategy,
        "generation": settings.generation_backend,
        "storage": settings.storage_backend,
        "pii": settings.privacy_mode,
        "orchestration": "langgraph",
        "reranker": settings.reranker_model if settings.reranker_enabled else "disabled",
        "knowledge_entries": len(runtime.knowledge_base.entries),
        "version": __version__,
    }
