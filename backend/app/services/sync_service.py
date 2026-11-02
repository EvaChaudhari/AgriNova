"""Two-Way Offline Synchronization Engine.

Reconciles client mutations queued during intermittent 2G/3G connectivity in rural areas.
Enforces strict idempotency via client-provided UUID keys and audits all mutations.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any
from sqlalchemy.orm import Session

from app.engines.roadmap_engine import RoadmapEngine
from app.models.workflows import OfflineSyncEvent, RoadmapCheckpoint
from app.schemas.workflows import (
    SyncActionItem,
    SyncActionResult,
    SyncBatchRequest,
    SyncBatchResponse,
)

logger = logging.getLogger("agrinova.sync")


class OfflineSyncService:
    """Idempotent sync service for offline farmer operations."""

    @classmethod
    def process_sync_batch(cls, db: Session, batch: SyncBatchRequest) -> SyncBatchResponse:
        """Process a batch of offline actions with idempotency checks."""
        server_ts = datetime.now(timezone.utc)
        results: list[SyncActionResult] = []
        applied_count = 0
        skipped_count = 0

        for action in batch.actions:
            result = cls._process_single_action(db, batch.device_id, action, server_ts)
            results.append(result)
            if result.status == "APPLIED":
                applied_count += 1
            else:
                skipped_count += 1

        db.commit()

        return SyncBatchResponse(
            device_id=batch.device_id,
            total_actions=len(batch.actions),
            applied=applied_count,
            skipped=skipped_count,
            results=results,
            server_timestamp=server_ts,
        )

    @classmethod
    def _process_single_action(
        cls,
        db: Session,
        device_id: str,
        action: SyncActionItem,
        server_ts: datetime,
    ) -> SyncActionResult:
        """Evaluate a single action against the idempotency log and apply mutations."""
        # 1. Idempotency duplicate check
        existing = (
            db.query(OfflineSyncEvent)
            .filter(OfflineSyncEvent.idempotency_key == action.idempotency_key)
            .first()
        )
        if existing:
            return SyncActionResult(
                idempotency_key=action.idempotency_key,
                action_type=action.action_type,
                status="DUPLICATE_SKIPPED",
                message=f"Action '{action.idempotency_key}' previously applied at {existing.server_timestamp.isoformat()}.",
            )

        # 2. Apply action logic
        try:
            msg = cls._dispatch_action(db, action.action_type, action.payload)
            status_val = "APPLIED"
        except Exception as exc:
            logger.warning("Error processing sync action %s: %s", action.idempotency_key, str(exc))
            msg = f"Failed to apply action: {str(exc)}"
            status_val = "ERROR"

        # 3. Log event audit trail
        event = OfflineSyncEvent(
            idempotency_key=action.idempotency_key,
            device_id=device_id,
            action_type=action.action_type,
            payload_json=json.dumps(action.payload),
            status=status_val,
            server_timestamp=server_ts,
            client_timestamp=action.client_timestamp,
        )
        db.add(event)
        db.flush()

        return SyncActionResult(
            idempotency_key=action.idempotency_key,
            action_type=action.action_type,
            status=status_val,
            message=msg,
        )

    @classmethod
    def _dispatch_action(cls, db: Session, action_type: str, payload: dict[str, Any]) -> str:
        """Route action payload to appropriate subsystem."""
        atype = action_type.upper().strip()

        if atype == "CHECKPOINT_COMPLETE":
            checkpoint_id = payload.get("checkpoint_id")
            if not checkpoint_id:
                raise ValueError("Missing 'checkpoint_id' in payload")
            notes = payload.get("notes")
            status = payload.get("status", "COMPLETED")
            RoadmapEngine.complete_checkpoint(db, int(checkpoint_id), notes=notes, status=status)
            return f"Checkpoint {checkpoint_id} updated to {status}."

        elif atype == "LOG_IRRIGATION":
            plot_id = payload.get("plot_id")
            depth_mm = payload.get("depth_mm", 0.0)
            return f"Irrigation event of {depth_mm}mm recorded for plot {plot_id}."

        elif atype == "OFFLINE_NOTE":
            plot_id = payload.get("plot_id")
            content = payload.get("note", "")
            return f"Field note for plot {plot_id} saved."

        else:
            return f"Custom action '{action_type}' recorded successfully."

