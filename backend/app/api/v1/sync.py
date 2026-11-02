"""Two-Way Offline Synchronization API Router.

Enables mobile clients in intermittent rural 2G/3G connectivity to reconcile
batches of queued offline actions with guaranteed idempotency and audit logs.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workflows import SyncBatchRequest, SyncBatchResponse
from app.services.sync_service import OfflineSyncService

router = APIRouter(prefix="/sync", tags=["Offline Synchronization"])


@router.post("/batch", response_model=SyncBatchResponse)
def synchronize_offline_batch(
    payload: SyncBatchRequest,
    db: Session = Depends(get_db),
) -> SyncBatchResponse:
    """Reconcile a batch of client-side offline actions with guaranteed idempotency."""
    return OfflineSyncService.process_sync_batch(db=db, batch=payload)

