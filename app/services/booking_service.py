import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.logging import logger
from app.db.models.appointment_slot import AppointmentSlot
from app.db.models.booking import Booking
from app.db.models.enums import BookingStatus, UserRole
from app.db.models.user import User
from app.repositories.booking_repository import BookingRepository
from app.repositories.centre_repository import CentreRepository
from app.schemas.booking import BookingCreate


class BookingService:
    def __init__(
        self,
        booking_repo: type[BookingRepository] = BookingRepository,
        centre_repo: type[CentreRepository] = CentreRepository,
    ):
        self.booking_repo = booking_repo
        self.centre_repo = centre_repo

    def generate_booking_reference(self) -> str:
        date_prefix = datetime.now(UTC).strftime("%Y%m%d")
        unique_suffix = uuid.uuid4().hex[:8].upper()
        return f"BKG-{date_prefix}-{unique_suffix}"

    def create_booking(self, db: Session, user: User, booking_in: BookingCreate) -> Booking:
        logger.info(
            f"Initiating booking: user_id={user.id}, centre_test_id={booking_in.centre_test_id}, "
            f"slot_id={booking_in.appointment_slot_id}"
        )

        # 1. Validate CentreTest
        centre_test = self.centre_repo.get_centre_test_by_id(db, booking_in.centre_test_id)
        if not centre_test:
            raise NotFoundException("CentreTest", booking_in.centre_test_id)

        if not centre_test.is_available:
            raise ValidationException(
                "TEST_UNAVAILABLE", "The requested diagnostic test is currently unavailable."
            )
        if not centre_test.centre.is_active:
            raise ValidationException(
                "CENTRE_INACTIVE", "The diagnostic centre is currently inactive."
            )
        if not centre_test.test.is_active:
            raise ValidationException("TEST_INACTIVE", "The diagnostic test is currently inactive.")

        # 2. Acquire and lock Appointment Slot
        slot = db.scalar(
            select(AppointmentSlot)
            .where(AppointmentSlot.id == booking_in.appointment_slot_id)
            .with_for_update()
        )
        if not slot:
            raise NotFoundException("AppointmentSlot", booking_in.appointment_slot_id)

        if slot.centre_id != centre_test.centre_id:
            raise ValidationException(
                "INVALID_SLOT_CENTRE",
                "The selected appointment slot does not belong to this centre.",
            )

        if not slot.is_available:
            raise ConflictException(
                "SLOT_ALREADY_BOOKED",
                "The selected appointment slot is already booked and unavailable.",
            )

        # 3. Check appointment slot is in the future
        slot_dt = slot.appointment_datetime
        if slot_dt.tzinfo is None:
            slot_dt = slot_dt.replace(tzinfo=UTC)
        if slot_dt <= datetime.now(UTC):
            raise ValidationException(
                "PAST_APPOINTMENT_DATE",
                "Cannot book an appointment slot in the past.",
            )

        # 4. Atomically reserve slot & Snapshot price
        slot.is_available = False
        amount_snapshot = centre_test.price
        booking_ref = self.generate_booking_reference()

        # 5. Create Booking in PENDING state
        booking = self.booking_repo.create(
            db=db,
            user_id=user.id,
            centre_test_id=centre_test.id,
            slot_id=slot.id,
            amount=amount_snapshot,
            booking_reference=booking_ref,
        )

        db.commit()
        db.refresh(booking)
        logger.info(
            f"Booking created successfully: ref={booking.booking_reference}, "
            f"amount={booking.amount}, status={booking.status}"
        )
        return self.get_booking(db, user, booking.id)

    def get_booking(self, db: Session, user: User, booking_id: int) -> Booking:
        booking = self.booking_repo.get_by_id(db, booking_id)
        if not booking:
            raise NotFoundException("Booking", booking_id)

        if user.role != UserRole.ADMIN and booking.user_id != user.id:
            logger.warning(
                f"Unauthorized booking access attempt: user_id={user.id} on booking_id={booking_id}"
            )
            raise ForbiddenException("You are not authorized to access this booking.")

        return booking

    def list_bookings(
        self, db: Session, user: User, skip: int = 0, limit: int = 100
    ) -> Sequence[Booking]:
        if user.role == UserRole.ADMIN:
            return self.booking_repo.list_all(db, skip=skip, limit=limit)
        return self.booking_repo.list_by_user(db, user_id=user.id, skip=skip, limit=limit)

    def cancel_booking(self, db: Session, user: User, booking_id: int) -> Booking:
        booking = self.booking_repo.get_by_id(db, booking_id)
        if not booking:
            raise NotFoundException("Booking", booking_id)

        if user.role != UserRole.ADMIN and booking.user_id != user.id:
            logger.warning(
                f"Unauthorized cancellation attempt: user_id={user.id} on booking_id={booking_id}"
            )
            raise ForbiddenException("You are not authorized to cancel this booking.")

        # State Machine Validation
        if booking.status in (BookingStatus.CANCELLED, BookingStatus.FAILED):
            raise ConflictException(
                "INVALID_STATE_TRANSITION",
                f"Cannot cancel a booking that is already in '{booking.status}' state.",
            )

        # Release the appointment slot
        if booking.appointment_slot:
            booking.appointment_slot.is_available = True

        booking.status = BookingStatus.CANCELLED
        db.commit()
        db.refresh(booking)
        logger.info(f"Booking ref={booking.booking_reference} cancelled successfully")
        return booking

    def transition_status(
        self, db: Session, booking: Booking, new_status: BookingStatus
    ) -> Booking:
        """Internal state transition validator for payment and webhook engines."""
        current_status = booking.status

        # Valid transitions:
        # PENDING -> CONFIRMED
        # PENDING -> FAILED
        # PENDING -> CANCELLED
        # CONFIRMED -> CANCELLED
        valid_transitions = {
            BookingStatus.PENDING: {
                BookingStatus.CONFIRMED,
                BookingStatus.FAILED,
                BookingStatus.CANCELLED,
            },
            BookingStatus.CONFIRMED: {BookingStatus.CANCELLED},
            BookingStatus.FAILED: set(),
            BookingStatus.CANCELLED: set(),
        }

        if new_status == current_status:
            return booking

        if new_status not in valid_transitions.get(current_status, set()):
            raise ConflictException(
                "INVALID_STATE_TRANSITION",
                f"Illegal booking state transition from '{current_status}' to '{new_status}'.",
            )

        if new_status in (BookingStatus.FAILED, BookingStatus.CANCELLED):
            if booking.appointment_slot:
                booking.appointment_slot.is_available = True

        booking.status = new_status
        db.flush()
        logger.info(
            f"Booking ref={booking.booking_reference} transitioned: "
            f"{current_status} -> {new_status}"
        )
        return booking


booking_service = BookingService()
