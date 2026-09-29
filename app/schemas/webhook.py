from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import PaymentStatus


class WebhookEventCreate(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=100, description="Unique event ID")
    event_type: str = Field(
        default="payment.updated",
        min_length=1,
        max_length=100,
        description="Type of webhook event",
    )
    payment_id: str = Field(..., min_length=1, max_length=100, description="Payment reference")
    status: PaymentStatus = Field(..., description="Payment outcome: SUCCESS or FAILED")


class WebhookEventResponse(BaseModel):
    success: bool = True
    event_id: str
    message: str
    status: str
    processed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
