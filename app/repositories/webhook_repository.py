from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.webhook import PaymentWebhookEvent


class WebhookRepository:
    @staticmethod
    def get_by_event_id(db: Session, event_id: str) -> PaymentWebhookEvent | None:
        return db.scalar(
            select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_id == event_id)
        )

    @staticmethod
    def create_event(
        db: Session,
        event_id: str,
        event_type: str,
        payment_id: str,
        payload: str,
        processed_at: datetime | None = None,
    ) -> PaymentWebhookEvent:
        event = PaymentWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payment_id=payment_id,
            payload=payload,
            processed_at=processed_at or datetime.now(UTC),
        )
        db.add(event)
        db.flush()
        db.refresh(event)
        return event
