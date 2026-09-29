from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import BookingStatus
from app.schemas.centre_test import CentreTestResponse
from app.schemas.slot import SlotResponse
from app.schemas.user import UserResponse


class BookingCreate(BaseModel):
    centre_test_id: int = Field(..., description="ID of the CentreTest to book")
    appointment_slot_id: int = Field(..., description="ID of the AppointmentSlot to reserve")


class BookingResponse(BaseModel):
    id: int
    booking_reference: str
    user_id: int
    centre_test_id: int
    appointment_slot_id: int
    amount: Decimal
    status: BookingStatus
    created_at: datetime
    updated_at: datetime
    user: UserResponse | None = None
    centre_test: CentreTestResponse | None = None
    appointment_slot: SlotResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingCancelResponse(BaseModel):
    id: int
    booking_reference: str
    status: BookingStatus
    message: str = "Booking cancelled successfully."
