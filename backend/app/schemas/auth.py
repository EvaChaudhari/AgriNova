"""Authentication, Farmer Identity, and Device Session Schemas (Pydantic v2)."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    """JWT bearer access token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    """Registration request payload for a new farmer identity."""

    phone_number: str = Field(..., min_length=10, max_length=20, description="Farmer mobile number")
    full_name: str = Field(..., min_length=2, max_length=120, description="Farmer full name")
    pin: str = Field(..., min_length=4, max_length=8, description="4 to 8 digit numeric security PIN")
    preferred_language: str = Field(default="hi", max_length=10, description="Preferred language code (e.g. hi, te, mr, en)")
    kisan_id: Optional[str] = Field(default=None, max_length=50, description="Government PM-KISAN ID")
    device_id: Optional[str] = Field(default=None, max_length=128, description="Hardware device UUID to associate")


class LoginPIN(BaseModel):
    """Farmer PIN authentication payload."""

    phone_number: str = Field(..., min_length=10, max_length=20)
    pin: str = Field(..., min_length=4, max_length=8)
    device_id: Optional[str] = Field(default=None, max_length=128)


class DeviceSessionCreate(BaseModel):
    """Device session registration and hardware sync request."""

    device_id: str = Field(..., min_length=1, max_length=128, description="Hardware device UUID")
    device_model: Optional[str] = Field(default=None, max_length=120)
    os_version: Optional[str] = Field(default=None, max_length=64)
    app_version: Optional[str] = Field(default=None, max_length=64)
    farmer_name: Optional[str] = Field(default=None, max_length=120)
    preferred_language: Optional[str] = Field(default="hi", max_length=10)


class UserResponse(BaseModel):
    """Public farmer profile representation."""

    id: int
    phone_number: str
    full_name: str
    preferred_language: str
    kisan_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceResponse(BaseModel):
    """Hardware device session status representation."""

    id: int
    device_id: str
    user_id: Optional[int] = None
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    last_active_at: datetime
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthProfileResponse(BaseModel):
    """Current authenticated user profile and associated hardware devices."""

    user: Optional[UserResponse] = None
    device: Optional[DeviceResponse] = None
    devices: list[DeviceResponse] = []
    auth_type: str = "jwt"
    token: Optional[Token] = None
