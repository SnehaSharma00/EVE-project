import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.logging import logger
from app.db.models.enums import BookingStatus, PaymentStatus, UserRole
from app.db.models.payment import Payment
from app.db.models.user import User
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreate
from app.services.booking_service import booking_service


class PaymentService:
    def __init__(
        self,
        payment_repo: type[PaymentRepository] = PaymentRepository,
        booking_repo: type[BookingRepository] = BookingRepository,
    ):
        self.payment_repo = payment_repo
        self.booking_repo = booking_repo

    def generate_payment_reference(self) -> str:
        date_prefix = datetime.now(UTC).strftime("%Y%m%d")
        unique_suffix = uuid.uuid4().hex[:8].upper()
        return f"PAY-{date_prefix}-{unique_suffix}"

    def process_payment(
        self,
        db: Session,
        user: User,
        payment_in: PaymentCreate,
        idempotency_key: str | None = None,
    ) -> Payment:
        logger.info(
            f"Processing payment for booking_id={payment_in.booking_id}, "
            f"amount={payment_in.amount}, idempotency_key={idempotency_key}"
        )

        # 1. Check Idempotency Key
        if idempotency_key:
            existing_payment = self.payment_repo.get_by_idempotency_key(db, idempotency_key)
            if existing_payment:
                logger.info(
                    f"Idempotent payment return for key '{idempotency_key}', "
                    f"payment_ref={existing_payment.payment_reference}"
                )
                return existing_payment

        # 2. Fetch and validate Booking
        booking = self.booking_repo.get_by_id(db, payment_in.booking_id)
        if not booking:
            raise NotFoundException("Booking", payment_in.booking_id)

        # Check ownership
        if user.role != UserRole.ADMIN and booking.user_id != user.id:
            logger.warning(
                f"Unauthorized payment attempt: user_id={user.id} for booking_id={booking.id}"
            )
            raise ForbiddenException("You are not authorized to pay for this booking.")

        # Check Booking Status
        if booking.status == BookingStatus.CONFIRMED:
            raise ConflictException(
                "BOOKING_ALREADY_CONFIRMED", "This booking is already paid and confirmed."
            )
        if booking.status == BookingStatus.CANCELLED:
            raise ConflictException(
                "BOOKING_ALREADY_CANCELLED", "Cannot make payment for a cancelled booking."
            )
        if booking.status == BookingStatus.FAILED:
            raise ConflictException("BOOKING_FAILED", "Cannot make payment for a failed booking.")

        # 3. Check for existing successful payment on this booking
        successful_payment = self.payment_repo.get_successful_payment_for_booking(db, booking.id)
        if successful_payment:
            raise ConflictException(
                "PAYMENT_ALREADY_COMPLETED",
                "A successful payment already exists for this booking.",
            )

        # 4. Amount Verification
        if payment_in.amount != booking.amount:
            logger.warning(
                f"Payment amount mismatch: received {payment_in.amount}, expected {booking.amount}"
            )
            raise ValidationException(
                "PAYMENT_AMOUNT_MISMATCH",
                f"Amount '{payment_in.amount}' does not match booking amount '{booking.amount}'.",
            )

        # 5. Create Simulated Payment
        payment_ref = self.generate_payment_reference()
        provider_tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        simulated_status = payment_in.simulate_status

        payment = self.payment_repo.create(
            db=db,
            booking_id=booking.id,
            amount=payment_in.amount,
            payment_reference=payment_ref,
            status=simulated_status,
            provider="mock_gateway",
            provider_transaction_id=provider_tx_id,
            idempotency_key=idempotency_key,
        )

        # 6. Update Booking state accordingly
        if simulated_status == PaymentStatus.SUCCESS:
            booking_service.transition_status(db, booking, BookingStatus.CONFIRMED)
        else:
            booking_service.transition_status(db, booking, BookingStatus.FAILED)

        db.commit()
        db.refresh(payment)
        logger.info(
            f"Payment processed: ref={payment.payment_reference}, "
            f"status={payment.status}, booking_status={booking.status}"
        )
        return payment

    def get_payment(self, db: Session, user: User, payment_id: int) -> Payment:
        payment = self.payment_repo.get_by_id(db, payment_id)
        if not payment:
            raise NotFoundException("Payment", payment_id)

        if user.role != UserRole.ADMIN and payment.booking.user_id != user.id:
            raise ForbiddenException("You are not authorized to view this payment.")

        return payment


payment_service = PaymentService()
