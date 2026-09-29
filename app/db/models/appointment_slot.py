from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    centre_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("diagnostic_centres.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    centre_test_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("centre_tests.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    appointment_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    centre = relationship("DiagnosticCentre", back_populates="slots")
    booking = relationship("Booking", back_populates="appointment_slot", uselist=False)
