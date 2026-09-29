from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.logging import logger
from app.db.models.appointment_slot import AppointmentSlot
from app.db.models.centre import DiagnosticCentre
from app.db.models.centre_test import CentreTest
from app.repositories.centre_repository import CentreRepository
from app.repositories.test_repository import TestRepository
from app.schemas.centre import CentreCreate, CentreUpdate
from app.schemas.centre_test import CentreTestCreate
from app.schemas.slot import SlotCreate


class CentreService:
    def __init__(
        self,
        centre_repo: type[CentreRepository] = CentreRepository,
        test_repo: type[TestRepository] = TestRepository,
    ):
        self.centre_repo = centre_repo
        self.test_repo = test_repo

    def get_centre(self, db: Session, centre_id: int) -> DiagnosticCentre:
        centre = self.centre_repo.get_by_id(db, centre_id)
        if not centre:
            raise NotFoundException("DiagnosticCentre", centre_id)
        return centre

    def list_centres(
        self,
        db: Session,
        city: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[DiagnosticCentre]:
        return self.centre_repo.list_centres(
            db, city=city, is_active=is_active, skip=skip, limit=limit
        )

    def create_centre(self, db: Session, centre_in: CentreCreate) -> DiagnosticCentre:
        logger.info(f"Creating new diagnostic centre: '{centre_in.name}' in {centre_in.city}")
        return self.centre_repo.create(db, centre_in)

    def update_centre(
        self, db: Session, centre_id: int, centre_in: CentreUpdate
    ) -> DiagnosticCentre:
        centre = self.get_centre(db, centre_id)
        logger.info(f"Updating diagnostic centre id={centre_id}")
        return self.centre_repo.update(db, centre, centre_in)

    def add_test_to_centre(
        self, db: Session, centre_id: int, centre_test_in: CentreTestCreate
    ) -> CentreTest:
        centre = self.get_centre(db, centre_id)
        if not centre.is_active:
            raise ValidationException("INACTIVE_CENTRE", "Cannot add tests to an inactive centre.")

        test = self.test_repo.get_by_id(db, centre_test_in.test_id)
        if not test:
            raise NotFoundException("DiagnosticTest", centre_test_in.test_id)
        if not test.is_active:
            raise ValidationException("INACTIVE_TEST", "Cannot add an inactive test to a centre.")

        existing = self.centre_repo.get_centre_test(db, centre_id, centre_test_in.test_id)
        if existing:
            raise ConflictException(
                "DUPLICATE_CENTRE_TEST",
                "This diagnostic test is already configured for this centre.",
            )

        logger.info(
            f"Offering test id={centre_test_in.test_id} at centre id={centre_id} "
            f"for price={centre_test_in.price}"
        )
        return self.centre_repo.add_centre_test(db, centre_id, centre_test_in)

    def list_centre_tests(
        self, db: Session, centre_id: int, is_available: bool | None = None
    ) -> Sequence[CentreTest]:
        self.get_centre(db, centre_id)
        return self.centre_repo.list_centre_tests(db, centre_id, is_available)

    def create_slot(self, db: Session, centre_id: int, slot_in: SlotCreate) -> AppointmentSlot:
        self.get_centre(db, centre_id)

        # Normalize slot time to UTC and check for past datetime
        slot_dt = slot_in.appointment_datetime
        if slot_dt.tzinfo is None:
            slot_dt = slot_dt.replace(tzinfo=UTC)
        now_dt = datetime.now(UTC)

        if slot_dt <= now_dt:
            raise ValidationException(
                "PAST_APPOINTMENT_DATE",
                "Appointment slot time must be in the future.",
            )

        if slot_in.centre_test_id:
            ct = self.centre_repo.get_centre_test_by_id(db, slot_in.centre_test_id)
            if not ct or ct.centre_id != centre_id:
                raise ValidationException(
                    "INVALID_CENTRE_TEST",
                    "The specified centre test does not belong to this centre.",
                )

        logger.info(f"Created appointment slot for centre id={centre_id} at {slot_dt}")
        return self.centre_repo.create_slot(db, centre_id, slot_in)

    def list_slots(
        self,
        db: Session,
        centre_id: int,
        is_available: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[AppointmentSlot]:
        self.get_centre(db, centre_id)
        return self.centre_repo.list_slots(
            db, centre_id=centre_id, is_available=is_available, skip=skip, limit=limit
        )


centre_service = CentreService()
