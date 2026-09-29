import json
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.db.models.enums import BookingStatus, PaymentStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.webhook_repository import WebhookRepository
from app.schemas.webhook import WebhookEventCreate, WebhookEventResponse
from app.services.booking_service import booking_service


class WebhookService:
    def __init__(
        self,
        webhook_repo: type[WebhookRepository] = WebhookRepository,
        payment_repo: type[PaymentRepository] = PaymentRepository,
    ):
        self.webhook_repo = webhook_repo
        self.payment_repo = payment_repo

    def process_webhook(self, db: Session, event_in: WebhookEventCreate) -> WebhookEventResponse:
        logger.info(
            f"Received webhook: event_id={event_in.event_id}, type={event_type_str(event_in)}, "
            f"payment_id={event_in.payment_id}, status={event_in.status}"
        )

        # 1. Idempotency Check (Fast Path)
        existing_event = self.webhook_repo.get_by_event_id(db, event_in.event_id)
        if existing_event:
            logger.info(
                f"Idempotent webhook skipped: event_id='{event_in.event_id}' "
                f"was already processed at {existing_event.processed_at}"
            )
            return WebhookEventResponse(
                success=True,
                event_id=event_in.event_id,
                message="Webhook event already processed.",
                status="ALREADY_PROCESSED",
                processed_at=existing_event.processed_at,
            )

        # 2. Lookup Payment by reference (e.g. PAY-...) or ID
        payment = self.payment_repo.get_by_reference(db, event_in.payment_id)
        if not payment:
            # Check if payment_id was passed as numeric ID
            if event_in.payment_id.isdigit():
                payment = self.payment_repo.get_by_id(db, int(event_in.payment_id))

        if not payment:
            logger.error(f"Webhook error: Payment '{event_in.payment_id}' not found")
            raise NotFoundException("Payment", event_in.payment_id)

        # 3. Apply state transitions within database transaction
        booking = payment.booking
        new_payment_status = event_in.status

        # Update Payment Record
        payment.status = new_payment_status

        # Update Booking state if not already terminal
        if booking.status == BookingStatus.CANCELLED:
            logger.warning(
                f"Webhook: Booking ref={booking.booking_reference} is CANCELLED. "
                "Retaining CANCELLED state."
            )
        elif booking.status == BookingStatus.PENDING:
            if new_payment_status == PaymentStatus.SUCCESS:
                booking_service.transition_status(db, booking, BookingStatus.CONFIRMED)
            elif new_payment_status == PaymentStatus.FAILED:
                booking_service.transition_status(db, booking, BookingStatus.FAILED)
        elif booking.status == BookingStatus.CONFIRMED:
            if new_payment_status == PaymentStatus.FAILED:
                logger.info(
                    f"Confirmed booking {booking.booking_reference} received FAILED payment"
                )
                booking_service.transition_status(db, booking, BookingStatus.CANCELLED)

        # 4. Save Webhook Event Record (Idempotency Key guarantee)
        now_dt = datetime.now(UTC)
        payload_str = json.dumps(event_in.model_dump(mode="json"))

        try:
            event_record = self.webhook_repo.create_event(
                db=db,
                event_id=event_in.event_id,
                event_type=event_in.event_type,
                payment_id=event_in.payment_id,
                payload=payload_str,
                processed_at=now_dt,
            )
            db.commit()
            logger.info(
                f"Webhook event '{event_in.event_id}' successfully processed and committed."
            )
        except IntegrityError:
            # Handle race condition where exact same event_id was inserted concurrently
            db.rollback()
            logger.warning(
                f"Concurrent duplicate webhook detected for event_id '{event_in.event_id}'"
            )
            existing_event = self.webhook_repo.get_by_event_id(db, event_in.event_id)
            return WebhookEventResponse(
                success=True,
                event_id=event_in.event_id,
                message="Webhook event already processed.",
                status="ALREADY_PROCESSED",
                processed_at=existing_event.processed_at if existing_event else now_dt,
            )

        return WebhookEventResponse(
            success=True,
            event_id=event_record.event_id,
            message="Webhook processed successfully.",
            status=new_payment_status.value,
            processed_at=event_record.processed_at,
        )


def event_type_str(event: WebhookEventCreate) -> str:
    return event.event_type


webhook_service = WebhookService()
