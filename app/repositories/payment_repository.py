from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.booking import Booking
from app.db.models.enums import PaymentStatus
from app.db.models.payment import Payment


class PaymentRepository:
    @staticmethod
    def get_by_id(db: Session, payment_id: int) -> Payment | None:
        return db.scalar(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.booking).selectinload(Booking.user))
        )

    @staticmethod
    def get_by_reference(db: Session, payment_reference: str) -> Payment | None:
        return db.scalar(
            select(Payment)
            .where(Payment.payment_reference == payment_reference)
            .options(
                selectinload(Payment.booking).selectinload(Booking.user),
                selectinload(Payment.booking).selectinload(Booking.appointment_slot),
            )
        )

    @staticmethod
    def get_by_idempotency_key(db: Session, idempotency_key: str) -> Payment | None:
        return db.scalar(
            select(Payment)
            .where(Payment.idempotency_key == idempotency_key)
            .options(selectinload(Payment.booking))
        )

    @staticmethod
    def get_successful_payment_for_booking(db: Session, booking_id: int) -> Payment | None:
        return db.scalar(
            select(Payment).where(
                Payment.booking_id == booking_id, Payment.status == PaymentStatus.SUCCESS
            )
        )

    @staticmethod
    def create(
        db: Session,
        booking_id: int,
        amount: Decimal,
        payment_reference: str,
        status: PaymentStatus,
        provider: str = "mock_gateway",
        provider_transaction_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Payment:
        payment = Payment(
            booking_id=booking_id,
            amount=amount,
            payment_reference=payment_reference,
            status=status,
            provider=provider,
            provider_transaction_id=provider_transaction_id,
            idempotency_key=idempotency_key,
        )
        db.add(payment)
        db.flush()
        db.refresh(payment)
        return payment

    @staticmethod
    def update_status(
        db: Session,
        payment: Payment,
        new_status: PaymentStatus,
        provider_transaction_id: str | None = None,
    ) -> Payment:
        payment.status = new_status
        if provider_transaction_id:
            payment.provider_transaction_id = provider_transaction_id
        db.flush()
        db.refresh(payment)
        return payment
