"""Farmer Notification & Action Alerts API Router.

Provides endpoints to retrieve active hazard, irrigation, and roadmap alerts
and acknowledge them.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.schemas.workflows import (
    NotificationReadResponse,
    NotificationResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Farmer Notifications"])


@router.get("", response_model=list[NotificationResponse])
def get_farmer_notifications(
    device_id: str = Query(..., description="Device UUID of the smallholder farmer"),
    unread_only: bool = Query(False, description="Filter unread notifications only"),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    """Retrieve actionable notifications and hazard alerts for a farmer's device."""
    notifications = NotificationService.list_notifications(
        db=db,
        device_id=device_id,
        unread_only=unread_only,
    )
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.post("/{notification_id}/read", response_model=NotificationReadResponse)
def acknowledge_notification(
    notification_id: int,
    device_id: Optional[str] = Query(None, description="Optional device verification ID"),
    db: Session = Depends(get_db),
) -> NotificationReadResponse:
    """Mark a notification as read and record acknowledgment timestamp."""
    try:
        notif = NotificationService.mark_as_read(
            db=db,
            notification_id=notification_id,
            device_id=device_id,
        )
    except ValueError as exc:
        raise EntityNotFoundError(str(exc))

    return NotificationReadResponse(
        id=notif.id,
        is_read=notif.is_read,
        acknowledged_at=notif.read_at,
    )

