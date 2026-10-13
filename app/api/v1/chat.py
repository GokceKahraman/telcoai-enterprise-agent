from fastapi import APIRouter, Depends

from app.api.dependencies import get_chat_service
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def post_chat(
    payload: ChatRequest, service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    return service.reply(payload.message, payload.session_id, payload.category, payload.locale)
