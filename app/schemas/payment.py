from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import PaymentStatus
from app.schemas.booking import BookingResponse


class PaymentCreate(BaseModel):
    booking_id: int = Field(..., description="ID of the booking to pay for")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Payment amount")
    simulate_status: PaymentStatus = Field(
        default=PaymentStatus.SUCCESS,
        description="Simulated gateway outcome: SUCCESS or FAILED",
    )


class PaymentResponse(BaseModel):
    id: int
    payment_reference: str
    booking_id: int
    amount: Decimal
    status: PaymentStatus
    provider: str
    provider_transaction_id: str | None = None
    idempotency_key: str | None = None
    created_at: datetime
    updated_at: datetime
    booking: BookingResponse | None = None

    model_config = ConfigDict(from_attributes=True)
