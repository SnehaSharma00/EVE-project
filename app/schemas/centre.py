from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CentreBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Centre name")
    address: str = Field(..., min_length=1, max_length=500, description="Physical address")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str = Field(..., min_length=1, max_length=100, description="State")
    latitude: float | None = Field(default=None, description="GPS Latitude")
    longitude: float | None = Field(default=None, description="GPS Longitude")


class CentreCreate(CentreBase):
    is_active: bool = Field(default=True, description="Whether centre is active")


class CentreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool | None = None


class CentreResponse(CentreBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
