from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SlotCreate(BaseModel):
    centre_test_id: int | None = Field(default=None, description="Optional specific test ID")
    appointment_datetime: datetime = Field(..., description="Date and time of the appointment slot")
    is_available: bool = Field(default=True, description="Availability flag")


class SlotResponse(BaseModel):
    id: int
    centre_id: int
    centre_test_id: int | None
    appointment_datetime: datetime
    is_available: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
