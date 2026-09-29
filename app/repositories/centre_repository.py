from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.appointment_slot import AppointmentSlot
from app.db.models.centre import DiagnosticCentre
from app.db.models.centre_test import CentreTest
from app.schemas.centre import CentreCreate, CentreUpdate
from app.schemas.centre_test import CentreTestCreate
from app.schemas.slot import SlotCreate


class CentreRepository:
    @staticmethod
    def get_by_id(db: Session, centre_id: int) -> DiagnosticCentre | None:
        return db.scalar(select(DiagnosticCentre).where(DiagnosticCentre.id == centre_id))

    @staticmethod
    def list_centres(
        db: Session,
        city: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[DiagnosticCentre]:
        query = select(DiagnosticCentre)
        if city:
            query = query.where(DiagnosticCentre.city.ilike(f"%{city}%"))
        if is_active is not None:
            query = query.where(DiagnosticCentre.is_active == is_active)
        return db.scalars(query.offset(skip).limit(limit)).all()

    @staticmethod
    def create(db: Session, centre_in: CentreCreate) -> DiagnosticCentre:
        centre = DiagnosticCentre(
            name=centre_in.name.strip(),
            address=centre_in.address.strip(),
            city=centre_in.city.strip(),
            state=centre_in.state.strip(),
            latitude=centre_in.latitude,
            longitude=centre_in.longitude,
            is_active=centre_in.is_active,
        )
        db.add(centre)
        db.commit()
        db.refresh(centre)
        return centre

    @staticmethod
    def update(db: Session, centre: DiagnosticCentre, centre_in: CentreUpdate) -> DiagnosticCentre:
        update_data = centre_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(centre, field, value)
        db.commit()
        db.refresh(centre)
        return centre

    @staticmethod
    def get_centre_test(db: Session, centre_id: int, test_id: int) -> CentreTest | None:
        return db.scalar(
            select(CentreTest)
            .where(CentreTest.centre_id == centre_id, CentreTest.test_id == test_id)
            .options(selectinload(CentreTest.test))
        )

    @staticmethod
    def get_centre_test_by_id(db: Session, centre_test_id: int) -> CentreTest | None:
        return db.scalar(
            select(CentreTest)
            .where(CentreTest.id == centre_test_id)
            .options(selectinload(CentreTest.test), selectinload(CentreTest.centre))
        )

    @staticmethod
    def list_centre_tests(
        db: Session, centre_id: int, is_available: bool | None = None
    ) -> Sequence[CentreTest]:
        query = (
            select(CentreTest)
            .where(CentreTest.centre_id == centre_id)
            .options(selectinload(CentreTest.test))
        )
        if is_available is not None:
            query = query.where(CentreTest.is_available == is_available)
        return db.scalars(query).all()

    @staticmethod
    def add_centre_test(
        db: Session, centre_id: int, centre_test_in: CentreTestCreate
    ) -> CentreTest:
        centre_test = CentreTest(
            centre_id=centre_id,
            test_id=centre_test_in.test_id,
            price=centre_test_in.price,
            is_available=centre_test_in.is_available,
        )
        db.add(centre_test)
        db.commit()
        db.refresh(centre_test)
        return centre_test

    @staticmethod
    def list_slots(
        db: Session,
        centre_id: int,
        is_available: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[AppointmentSlot]:
        query = select(AppointmentSlot).where(AppointmentSlot.centre_id == centre_id)
        if is_available is not None:
            query = query.where(AppointmentSlot.is_available == is_available)
        return db.scalars(query.offset(skip).limit(limit)).all()

    @staticmethod
    def create_slot(db: Session, centre_id: int, slot_in: SlotCreate) -> AppointmentSlot:
        slot = AppointmentSlot(
            centre_id=centre_id,
            centre_test_id=slot_in.centre_test_id,
            appointment_datetime=slot_in.appointment_datetime,
            is_available=slot_in.is_available,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)
        return slot

    @staticmethod
    def get_slot_by_id(db: Session, slot_id: int) -> AppointmentSlot | None:
        return db.scalar(select(AppointmentSlot).where(AppointmentSlot.id == slot_id))
