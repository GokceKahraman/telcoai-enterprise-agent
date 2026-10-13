from secrets import compare_digest

from fastapi import Header, HTTPException, Request

from app.services.chat_service import ChatService


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.runtime.service


def require_access(request: Request, authorization: str | None = Header(default=None)) -> None:
    key = request.app.state.settings.api_key
    if key and (
        not authorization or not compare_digest(authorization, f"Bearer {key.get_secret_value()}")
    ):
        raise HTTPException(
            status_code=401,
            detail="API erişim anahtarı gerekli.",
            headers={"WWW-Authenticate": "Bearer"},
        )
