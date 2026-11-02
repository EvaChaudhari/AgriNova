"""Farmer Identity and Dual-Mode Authentication Engine.

Supports dual-mode identity resolution:
1. Primary: JWT Bearer Token (signed for registered farmer user).
2. Fallback: Hardware Device binding (X-Device-ID or device_id parameter) for single-tenant offline workflows.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any, Optional

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenActionError, UnauthorizedAccessError
from app.core.rate_limiter import is_token_blacklisted
from app.core.security import decode_access_token
from app.models.auth import Device, User
from app.models.consent import AuditLog
from app.models.profile import DeviceProfile


@dataclass
class Identity:
    """Resolved farmer identity context for authorization and telemetry tagging."""

    id: Optional[int] = None
    phone_number: Optional[str] = None
    device_id: Optional[str] = None
    auth_type: str = "anonymous"  # "jwt", "device", "anonymous"
    user: Optional[User] = None
    device: Optional[Device] = None
    is_authenticated: bool = False


def get_current_identity(
    request: Request,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    device_id_query: Optional[str] = Query(None, alias="device_id"),
) -> Identity:
    """Resolve caller identity via JWT Authorization header or hardware device fallback."""
    auth_header = request.headers.get("Authorization")

    # 1. Primary path: JWT Bearer Token
    if auth_header and auth_header.strip().startswith("Bearer "):
        token = auth_header.strip()[7:].strip()
        if is_token_blacklisted(token):
            raise UnauthorizedAccessError("Token has been revoked. Please authenticate again.")
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedAccessError("Token subject is missing.")

        # Look up user by ID or phone number
        user = None
        if sub.isdigit():
            user = db.query(User).filter(User.id == int(sub)).first()
        if not user:
            user = db.query(User).filter(User.phone_number == sub).first()

        if not user or not user.is_active:
            raise UnauthorizedAccessError("User identified in token does not exist or is inactive.")

        # Resolve device context if present
        dev_id = payload.get("device_id") or x_device_id or device_id_query
        device = None
        if dev_id:
            device = db.query(Device).filter(Device.device_id == dev_id).first()
            if device:
                device.last_active_at = datetime.now(timezone.utc)
                db.commit()

        return Identity(
            id=user.id,
            phone_number=user.phone_number,
            device_id=dev_id,
            auth_type="jwt",
            user=user,
            device=device,
            is_authenticated=True,
        )

    # 2. Fallback path: Hardware Device binding
    dev_id = x_device_id or device_id_query
    if dev_id:
        dev_id = dev_id.strip()
        device = db.query(Device).filter(Device.device_id == dev_id).first()
        user = None
        if device and device.user_id:
            user = db.query(User).filter(User.id == device.user_id, User.is_active.is_(True)).first()

        # Check legacy DeviceProfile if Device not found
        if not device:
            legacy_profile = db.query(DeviceProfile).filter(DeviceProfile.device_id == dev_id).first()
            if legacy_profile:
                # Sync into Device table for consistency
                device = Device(
                    device_id=dev_id,
                    last_active_at=datetime.now(timezone.utc),
                    is_active=True,
                )
                db.add(device)
                db.commit()
                db.refresh(device)
        else:
            device.last_active_at = datetime.now(timezone.utc)
            db.commit()

        return Identity(
            id=user.id if user else None,
            phone_number=user.phone_number if user else None,
            device_id=dev_id,
            auth_type="device",
            user=user,
            device=device,
            is_authenticated=True,
        )

    # 3. Anonymous caller
    return Identity(
        id=None,
        phone_number=None,
        device_id=None,
        auth_type="anonymous",
        user=None,
        device=None,
        is_authenticated=False,
    )


def get_current_user(
    identity: Identity = Depends(get_current_identity),
) -> User:
    """Enforce that caller has a valid registered farmer account."""
    if not identity.user:
        raise UnauthorizedAccessError("Registered farmer identity required. Please register or login with your PIN.")
    if not identity.user.is_active:
        raise ForbiddenActionError("Farmer account is inactive. Please contact support.")
    return identity.user


def get_required_identity(
    identity: Identity = Depends(get_current_identity),
) -> Identity:
    """Enforce that caller has either an authenticated User account or a recognized Device session."""
    if not identity.is_authenticated:
        raise UnauthorizedAccessError("Authentication required. Please provide a Bearer token or X-Device-ID header.")
    return identity


def record_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    device_id: Optional[str] = None,
    details: Optional[Any] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Append a standardized entry to the compliance and security audit log."""
    details_str = json.dumps(details) if isinstance(details, (dict, list)) else (str(details) if details else None)
    log = AuditLog(
        user_id=user_id,
        device_id=device_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details_str,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

