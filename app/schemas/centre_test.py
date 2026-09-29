from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.diagnostic_test import DiagnosticTestResponse


class CentreTestCreate(BaseModel):
    test_id: int = Field(..., description="ID of the diagnostic test to offer")
    price: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Price of the test at this centre"
    )
    is_available: bool = Field(default=True, description="Availability flag")


class CentreTestResponse(BaseModel):
    id: int
    centre_id: int
    test_id: int
    price: Decimal
    is_available: bool
    created_at: datetime
    updated_at: datetime
    test: DiagnosticTestResponse | None = None

    model_config = ConfigDict(from_attributes=True)
