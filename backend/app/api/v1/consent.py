"""Farmer Consent and Compliance Audit Logging Endpoints.

Implements DPDP-compliant consent tracking (grant, revoke, status query)
and immutable audit log inspection.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth import Identity, get_required_identity, record_audit_log
from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.models.consent import AuditLog, ConsentRecord
from app.schemas.consent import (
    VALID_CONSENT_PURPOSES,
    AuditLogResponse,
    ConsentGrantRequest,
    ConsentResponse,
    ConsentRevokeRequest,
    ConsentStatusResponse,
)

router = APIRouter(prefix="/consent", tags=["Consent & DPDP Compliance"])


@router.post("/grant", response_model=ConsentResponse, status_code=status.HTTP_200_OK)
def grant_consent(
    payload: ConsentGrantRequest,
    request: Request,
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> ConsentResponse:
    """Explicitly grant consent for an agronomic or analytical data processing purpose."""
    if payload.purpose not in VALID_CONSENT_PURPOSES:
        raise ValidationError(
            f"Invalid consent purpose '{payload.purpose}'. Must be one of: {sorted(list(VALID_CONSENT_PURPOSES))}",
            invalid_params=[{"field": "purpose", "issue": "INVALID_PURPOSE"}],
        )

    dev_id = payload.device_id or identity.device_id
    user_id = identity.id if identity.user else None

    # Find existing consent record or create new
    query = db.query(ConsentRecord).filter(ConsentRecord.purpose == payload.purpose)
    if user_id:
        record = query.filter(ConsentRecord.user_id == user_id).first()
    else:
        record = query.filter(ConsentRecord.device_id == dev_id).first()

    ip_addr = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    if not record:
        record = ConsentRecord(
            user_id=user_id,
            device_id=dev_id,
            purpose=payload.purpose,
            status="GRANTED",
            granted_at=datetime.now(timezone.utc),
            revoked_at=None,
            ip_address=ip_addr,
            user_agent=user_agent,
        )
        db.add(record)
    else:
        record.status = "GRANTED"
        record.granted_at = datetime.now(timezone.utc)
        record.revoked_at = None
        record.ip_address = ip_addr
        record.user_agent = user_agent

    db.commit()
    db.refresh(record)

    record_audit_log(
        db,
        action="CONSENT_GRANTED",
        resource_type="consent",
        resource_id=str(record.id),
        user_id=user_id,
        device_id=dev_id,
        details={"purpose": payload.purpose, "status": "GRANTED"},
        ip_address=ip_addr,
    )

    return ConsentResponse.model_validate(record)


@router.post("/revoke", response_model=ConsentResponse, status_code=status.HTTP_200_OK)
def revoke_consent(
    payload: ConsentRevokeRequest,
    request: Request,
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> ConsentResponse:
    """Explicitly revoke previously granted consent for an agricultural data purpose."""
    if payload.purpose not in VALID_CONSENT_PURPOSES:
        raise ValidationError(
            f"Invalid consent purpose '{payload.purpose}'. Must be one of: {sorted(list(VALID_CONSENT_PURPOSES))}",
            invalid_params=[{"field": "purpose", "issue": "INVALID_PURPOSE"}],
        )

    dev_id = payload.device_id or identity.device_id
    user_id = identity.id if identity.user else None

    query = db.query(ConsentRecord).filter(ConsentRecord.purpose == payload.purpose)
    if user_id:
        record = query.filter(ConsentRecord.user_id == user_id).first()
    else:
        record = query.filter(ConsentRecord.device_id == dev_id).first()

    ip_addr = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    if not record:
        record = ConsentRecord(
            user_id=user_id,
            device_id=dev_id,
            purpose=payload.purpose,
            status="REVOKED",
            granted_at=datetime.now(timezone.utc),
            revoked_at=datetime.now(timezone.utc),
            ip_address=ip_addr,
            user_agent=user_agent,
        )
        db.add(record)
    else:
        record.status = "REVOKED"
        record.revoked_at = datetime.now(timezone.utc)
        record.ip_address = ip_addr
        record.user_agent = user_agent

    db.commit()
    db.refresh(record)

    record_audit_log(
        db,
        action="CONSENT_REVOKED",
        resource_type="consent",
        resource_id=str(record.id),
        user_id=user_id,
        device_id=dev_id,
        details={"purpose": payload.purpose, "status": "REVOKED"},
        ip_address=ip_addr,
    )

    return ConsentResponse.model_validate(record)


@router.get("/status", response_model=ConsentStatusResponse)
def get_consent_status(
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    """Retrieve comprehensive consent status map and underlying records for farmer."""
    user_id = identity.id if identity.user else None
    dev_id = identity.device_id

    query = db.query(ConsentRecord)
    if user_id:
        records = query.filter(ConsentRecord.user_id == user_id).all()
    elif dev_id:
        records = query.filter(ConsentRecord.device_id == dev_id).all()
    else:
        records = []

    status_map = {purpose: False for purpose in VALID_CONSENT_PURPOSES}
    for r in records:
        if r.purpose in status_map:
            status_map[r.purpose] = (r.status == "GRANTED")

    return ConsentStatusResponse(
        purposes=status_map,
        records=[ConsentResponse.model_validate(r) for r in records],
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def get_audit_trail(
    limit: int = Query(default=50, ge=1, le=200),
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    """Inspect immutable security and regulatory compliance audit trail for farmer."""
    user_id = identity.id if identity.user else None
    dev_id = identity.device_id

    query = db.query(AuditLog)
    if user_id and dev_id:
        logs = query.filter((AuditLog.user_id == user_id) | (AuditLog.device_id == dev_id))
    elif user_id:
        logs = query.filter(AuditLog.user_id == user_id)
    elif dev_id:
        logs = query.filter(AuditLog.device_id == dev_id)
    else:
        logs = []

    records = logs.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [AuditLogResponse.model_validate(r) for r in records]

