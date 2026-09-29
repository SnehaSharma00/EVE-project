from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DiagnosticTestBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Test name")
    description: str | None = Field(default=None, description="Detailed description")
    category: str = Field(..., min_length=1, max_length=100, description="Test category")


class DiagnosticTestCreate(DiagnosticTestBase):
    is_active: bool = Field(default=True, description="Whether test is active")


class DiagnosticTestResponse(DiagnosticTestBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
