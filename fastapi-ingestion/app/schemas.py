from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TelemetryPayload(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    timestamp: datetime
    speed: float | None = Field(default=None, ge=0.0)
    heading: float | None = Field(default=None, ge=0.0, lt=360.0)
    accuracy: float | None = Field(default=None, ge=0.0)
    battery: int | None = Field(default=None, ge=0, le=100)

    @field_validator("timestamp", mode="before")
    @classmethod
    def reject_naive_datetimes(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (include UTC offset or Z)")
        return v


class DeviceInfo(BaseModel):
    device_id: UUID
    org_id: UUID
    asset_id: UUID
