"""Bootstrap and Profile schemas (Pydantic v2)."""

from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DeviceProfileBase(BaseModel):
    farmer_name: str = Field(..., min_length=2, max_length=120)
    preferred_language: str = Field(default="hi", max_length=10)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    kisan_id: Optional[str] = Field(default=None, max_length=50)


class DeviceProfileCreate(DeviceProfileBase):
    device_id: str = Field(..., min_length=3, max_length=128)


class DeviceProfileResponse(DeviceProfileBase):
    device_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BootstrapResponse(BaseModel):
    device_id: str
    is_onboarded: bool
    message: str
    profile: Optional[DeviceProfileResponse] = None
    active_plot_id: Optional[int] = None
    context: Optional[dict[str, Any]] = None
    hazard_state: Optional[str] = None
    enforced_restrictions: list[str] = Field(default_factory=list)

