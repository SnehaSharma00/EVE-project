from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.webhook import WebhookEventCreate, WebhookEventResponse
from app.services.webhook_service import webhook_service

router = APIRouter(prefix="/payments/webhook", tags=["Webhooks"])


@router.post(
    "",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Process payment status webhook",
    description=(
        "Receives payment status updates from external payment gateway. "
        "Guaranteed to be strictly idempotent using unique event_id constraint."
    ),
)
def handle_payment_webhook(
    event_in: WebhookEventCreate,
    db: Session = Depends(get_db),
) -> WebhookEventResponse:
    return webhook_service.process_webhook(db=db, event_in=event_in)
