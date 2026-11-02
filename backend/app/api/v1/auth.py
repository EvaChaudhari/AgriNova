"""Farmer Authentication and Device Session Endpoints.

Provides farmer registration with numeric PIN hashing, JWT token issuance,
PIN verification, and hardware device session binding.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.auth import Identity, get_current_identity, get_required_identity, record_audit_log
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    ForbiddenActionError,
    UnauthorizedAccessError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    hash_pin_or_password,
    verify_pin_or_password,
)
from app.models.auth import Device, User
from app.models.profile import DeviceProfile
from app.schemas.auth import (
    AuthProfileResponse,
    DeviceResponse,
    DeviceSessionCreate,
    LoginPIN,
    Token,
    UserCreate,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Farmer Authentication & Identity"])


@router.post("/register", response_model=AuthProfileResponse, status_code=status.HTTP_201_CREATED)
def register_farmer(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthProfileResponse:
    """Register a new farmer profile with phone number and encrypted PIN."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.phone_number == payload.phone_number).first()
    if existing_user:
        raise ValidationError(
            f"A farmer with mobile number '{payload.phone_number}' is already registered.",
            invalid_params=[{"field": "phone_number", "issue": "ALREADY_REGISTERED"}],
        )

    # Hash PIN securely with PBKDF2
    hashed_pin = hash_pin_or_password(payload.pin)

    # Create User record
    user = User(
        phone_number=payload.phone_number,
        full_name=payload.full_name,
        hashed_pin=hashed_pin,
        preferred_language=payload.preferred_language,
        kisan_id=payload.kisan_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Associate device if specified
    device = None
    if payload.device_id:
        device = db.query(Device).filter(Device.device_id == payload.device_id).first()
        if not device:
            device = Device(
                device_id=payload.device_id,
                user_id=user.id,
                last_active_at=datetime.now(timezone.utc),
                is_active=True,
            )
            db.add(device)
        else:
            device.user_id = user.id
            device.last_active_at = datetime.now(timezone.utc)

        # Synchronize legacy DeviceProfile for backwards compatibility
        profile = db.query(DeviceProfile).filter(DeviceProfile.device_id == payload.device_id).first()
        if not profile:
            profile = DeviceProfile(
                device_id=payload.device_id,
                farmer_name=user.full_name,
                preferred_language=user.preferred_language,
                phone_number=user.phone_number,
                kisan_id=user.kisan_id,
            )
            db.add(profile)
        else:
            profile.farmer_name = user.full_name
            profile.phone_number = user.phone_number
            profile.kisan_id = user.kisan_id
            profile.preferred_language = user.preferred_language

        db.commit()
        db.refresh(device)

    # Log regulatory audit trail
    ip_addr = request.client.host if request.client else None
    record_audit_log(
        db,
        action="USER_REGISTERED",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        device_id=payload.device_id,
        details={"phone_number": user.phone_number, "full_name": user.full_name},
        ip_address=ip_addr,
    )

    # Generate JWT token
    access_token = create_access_token(
        subject=str(user.id),
        claims={"phone_number": user.phone_number, "device_id": payload.device_id},
    )
    token_resp = Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    devices = [DeviceResponse.model_validate(device)] if device else []

    return AuthProfileResponse(
        user=UserResponse.model_validate(user),
        devices=devices,
        auth_type="jwt",
        token=token_resp,
    )


@router.post("/login-pin", response_model=Token)
def login_with_pin(
    payload: LoginPIN,
    request: Request,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate farmer with phone number and PIN, issuing a JWT access token."""
    user = db.query(User).filter(User.phone_number == payload.phone_number).first()
    ip_addr = request.client.host if request.client else None

    if not user or not verify_pin_or_password(payload.pin, user.hashed_pin):
        record_audit_log(
            db,
            action="LOGIN_FAILED",
            resource_type="user",
            resource_id=str(user.id) if user else None,
            user_id=user.id if user else None,
            device_id=payload.device_id,
            details={"phone_number": payload.phone_number, "reason": "INVALID_CREDENTIALS"},
            ip_address=ip_addr,
        )
        raise UnauthorizedAccessError("Invalid phone number or PIN. Please verify your credentials.")

    if not user.is_active:
        raise ForbiddenActionError("Farmer account is inactive. Please contact support.")

    # Link/update device if specified
    if payload.device_id:
        device = db.query(Device).filter(Device.device_id == payload.device_id).first()
        if not device:
            device = Device(
                device_id=payload.device_id,
                user_id=user.id,
                last_active_at=datetime.now(timezone.utc),
                is_active=True,
            )
            db.add(device)
        else:
            device.user_id = user.id
            device.last_active_at = datetime.now(timezone.utc)
        db.commit()

    record_audit_log(
        db,
        action="LOGIN_SUCCESS",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        device_id=payload.device_id,
        details={"phone_number": user.phone_number},
        ip_address=ip_addr,
    )

    access_token = create_access_token(
        subject=str(user.id),
        claims={"phone_number": user.phone_number, "device_id": payload.device_id},
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/device-session", response_model=DeviceResponse)
def establish_device_session(
    payload: DeviceSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> DeviceResponse:
    """Register or refresh hardware device session for single-tenant or offline-first operation."""
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        device = Device(
            device_id=payload.device_id,
            device_model=payload.device_model,
            os_version=payload.os_version,
            app_version=payload.app_version,
            last_active_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(device)
    else:
        if payload.device_model:
            device.device_model = payload.device_model
        if payload.os_version:
            device.os_version = payload.os_version
        if payload.app_version:
            device.app_version = payload.app_version
        device.last_active_at = datetime.now(timezone.utc)
        device.is_active = True

    # Ensure DeviceProfile exists for backwards compatibility
    profile = db.query(DeviceProfile).filter(DeviceProfile.device_id == payload.device_id).first()
    if not profile:
        profile = DeviceProfile(
            device_id=payload.device_id,
            farmer_name=payload.farmer_name or "Farmer",
            preferred_language=payload.preferred_language or "hi",
        )
        db.add(profile)

    db.commit()
    db.refresh(device)

    ip_addr = request.client.host if request.client else None
    record_audit_log(
        db,
        action="DEVICE_SESSION_UPDATED",
        resource_type="device",
        resource_id=device.device_id,
        user_id=device.user_id,
        device_id=device.device_id,
        details={"device_model": device.device_model, "os_version": device.os_version},
        ip_address=ip_addr,
    )

    return DeviceResponse.model_validate(device)


@router.get("/me", response_model=AuthProfileResponse)
def get_current_profile(
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> AuthProfileResponse:
    """Retrieve currently authenticated farmer profile and linked devices."""
    if identity.user:
        devices = db.query(Device).filter(Device.user_id == identity.user.id).all()
        return AuthProfileResponse(
            user=UserResponse.model_validate(identity.user),
            devices=[DeviceResponse.model_validate(d) for d in devices],
            auth_type=identity.auth_type,
        )

    # Hardware device fallback
    device_obj = identity.device
    devices = [DeviceResponse.model_validate(device_obj)] if device_obj else []
    return AuthProfileResponse(
        user=None,
        device=DeviceResponse.model_validate(device_obj) if device_obj else None,
        devices=devices,
        auth_type=identity.auth_type,
    )

