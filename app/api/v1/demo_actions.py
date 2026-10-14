"""Explicit mock-only actions. FAQ chat never accesses account records."""

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import (
    DemoBillRequest,
    DemoBillsResponse,
    DemoConfirmRequest,
    DemoDraft,
    DemoPrepareRequest,
    DemoTicket,
    DemoTicketLookup,
)
from app.services.demo_actions import (
    DemoAccessDenied,
    DemoActionService,
    DemoConflict,
    DemoNotFound,
    DemoTimeout,
)

router = APIRouter(prefix="/demo", tags=["synthetic support journey"])


def service(request: Request) -> DemoActionService:
    actions = request.app.state.runtime.demo_actions
    if actions is None:
        raise HTTPException(404, "Örnek işlem akışı kapalı.")
    return actions


def handle_error(exc: Exception) -> None:
    if isinstance(exc, DemoAccessDenied):
        raise HTTPException(403, "Örnek hesap erişimi reddedildi.") from exc
    if isinstance(exc, DemoNotFound):
        raise HTTPException(404, "Örnek kayıt bulunamadı.") from exc
    if isinstance(exc, DemoConflict):
        raise HTTPException(409, "İşlem süresi doldu veya farklı anahtarla tekrarlandı.") from exc
    if isinstance(exc, DemoTimeout):
        raise HTTPException(504, "Örnek veri kaynağı zamanında yanıt vermedi.") from exc
    raise exc


@router.post("/bills", response_model=DemoBillsResponse)
def bills(payload: DemoBillRequest, request: Request) -> DemoBillsResponse:
    try:
        found = service(request).list_bills(
            payload.account_id, payload.access_code.get_secret_value()
        )
        return DemoBillsResponse(account_id=payload.account_id, bills=found)
    except (DemoAccessDenied, DemoNotFound, DemoTimeout) as exc:
        handle_error(exc)


@router.post("/tickets/prepare", response_model=DemoDraft)
def prepare(payload: DemoPrepareRequest, request: Request) -> DemoDraft:
    try:
        return DemoDraft.model_validate(
            service(request).prepare(
                payload.account_id,
                payload.access_code.get_secret_value(),
                payload.bill_id,
                payload.issue,
            )
        )
    except (DemoAccessDenied, DemoNotFound, DemoTimeout) as exc:
        handle_error(exc)


@router.post("/tickets/confirm", response_model=DemoTicket)
def confirm(payload: DemoConfirmRequest, request: Request) -> DemoTicket:
    try:
        return DemoTicket.model_validate(
            service(request).confirm(
                payload.account_id,
                payload.access_code.get_secret_value(),
                str(payload.draft_id),
                str(payload.idempotency_key),
            )
        )
    except (DemoAccessDenied, DemoNotFound, DemoConflict, DemoTimeout) as exc:
        handle_error(exc)


@router.post("/tickets/lookup", response_model=DemoTicket)
def lookup(payload: DemoTicketLookup, request: Request) -> DemoTicket:
    try:
        return DemoTicket.model_validate(
            service(request).get_ticket(
                payload.account_id,
                payload.access_code.get_secret_value(),
                payload.ticket_id,
            )
        )
    except (DemoAccessDenied, DemoNotFound, DemoTimeout) as exc:
        handle_error(exc)
