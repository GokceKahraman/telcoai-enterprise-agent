from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_chat_service
from app.models.schemas import SessionHistory
from app.services.chat_service import ChatService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}", response_model=SessionHistory)
def history(session_id: UUID, service: ChatService = Depends(get_chat_service)) -> SessionHistory:
    return SessionHistory(session_id=session_id, messages=service.store.history(session_id))


@router.delete("/{session_id}", status_code=204)
def delete(session_id: UUID, service: ChatService = Depends(get_chat_service)) -> Response:
    service.store.delete_session(session_id)
    return Response(status_code=204)
