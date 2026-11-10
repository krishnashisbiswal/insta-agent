"""
Authoritative Publishing State Machine and Idempotency Control.

Guarantees:
- Strict state transition enforcement.
- Idempotency key tracking to eliminate concurrent and duplicate publishing.
- Full transition audit trail with timestamps and metadata.
- Durable JSON / SQLite persistence.
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PublishingState(str, enum.Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    RENDERING = "RENDERING"
    QUALITY_CHECK = "QUALITY_CHECK"
    READY = "READY"
    SCHEDULED = "SCHEDULED"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DRY_RUN = "DRY_RUN"


# Permitted state transitions
VALID_TRANSITIONS: Dict[PublishingState, Set[PublishingState]] = {
    PublishingState.CREATED: {
        PublishingState.QUEUED,
        PublishingState.GENERATING,
        PublishingState.READY,
        PublishingState.UPLOADING,
        PublishingState.FAILED,
        PublishingState.CANCELLED,
        PublishingState.DRY_RUN,
    },
    PublishingState.QUEUED: {
        PublishingState.GENERATING,
        PublishingState.CANCELLED,
        PublishingState.FAILED,
        PublishingState.DRY_RUN,
    },
    PublishingState.GENERATING: {
        PublishingState.RENDERING,
        PublishingState.FAILED,
        PublishingState.CANCELLED,
        PublishingState.DRY_RUN,
    },
    PublishingState.RENDERING: {
        PublishingState.QUALITY_CHECK,
        PublishingState.FAILED,
        PublishingState.CANCELLED,
        PublishingState.DRY_RUN,
    },
    PublishingState.QUALITY_CHECK: {
        PublishingState.READY,
        PublishingState.FAILED,
        PublishingState.CANCELLED,
        PublishingState.DRY_RUN,
    },
    PublishingState.READY: {
        PublishingState.SCHEDULED,
        PublishingState.UPLOADING,
        PublishingState.CANCELLED,
        PublishingState.DRY_RUN,
    },
    PublishingState.SCHEDULED: {
        PublishingState.UPLOADING,
        PublishingState.CANCELLED,
        PublishingState.FAILED,
        PublishingState.DRY_RUN,
    },
    PublishingState.UPLOADING: {
        PublishingState.PROCESSING,
        PublishingState.PUBLISHED,  # For single images / carousels without async container
        PublishingState.FAILED,
        PublishingState.CANCELLED,
    },
    PublishingState.PROCESSING: {
        PublishingState.PUBLISHED,
        PublishingState.FAILED,
        PublishingState.CANCELLED,
    },
    PublishingState.PUBLISHED: set(),  # Terminal success state
    PublishingState.FAILED: {
        PublishingState.QUEUED,  # Retry capability
        PublishingState.GENERATING,
        PublishingState.CANCELLED,
    },
    PublishingState.CANCELLED: set(),  # Terminal user state
    PublishingState.DRY_RUN: set(),    # Terminal simulation state
}


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""
    pass


class DuplicateJobError(Exception):
    """Raised when a job with an identical idempotency key already exists or is running."""
    pass


@dataclass
class StateTransition:
    from_state: str
    to_state: str
    timestamp: float
    actor: str
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishingRecord:
    job_id: str
    account_id: str
    niche_id: str
    idempotency_key: str
    content_format: str  # REEL, CAROUSEL, STORY, POST
    state: PublishingState
    created_at: float
    updated_at: float
    topic: str
    script_data: Optional[Dict[str, Any]] = None
    rendered_assets: List[str] = field(default_factory=list)
    instagram_container_id: Optional[str] = None
    instagram_media_id: Optional[str] = None
    instagram_permalink: Optional[str] = None
    error_message: Optional[str] = None
    history: List[StateTransition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        data["history"] = [asdict(t) for t in self.history]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PublishingRecord:
        data_copy = dict(data)
        data_copy["state"] = PublishingState(data_copy["state"])
        history_raw = data_copy.get("history", [])
        data_copy["history"] = [StateTransition(**h) for h in history_raw]
        return cls(**data_copy)


class PublishingStateMachine:
    """
    Manages publishing lifecycles with strict locking and transition auditing.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        from config.settings import STORAGE_DIR
        self.storage_dir = Path(storage_dir or (STORAGE_DIR / "publishing_state"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.records_file = self.storage_dir / "publishing_records.json"
        self._lock = threading.Lock()
        self._records: Dict[str, PublishingRecord] = {}
        self._idempotency_index: Dict[str, str] = {}  # idempotency_key -> job_id
        self._load()

    @staticmethod
    def compute_idempotency_key(
        account_id: str,
        niche_id: str,
        topic: str,
        content_format: str = "REEL",
        scheduled_date: Optional[str] = None,
    ) -> str:
        """
        Derive a deterministic idempotency key for content.
        """
        normalized = f"{account_id.strip()}:{niche_id.strip()}:{topic.strip().lower()}:{content_format.upper()}"
        if scheduled_date:
            normalized += f":{scheduled_date.strip()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def create_job(
        self,
        job_id: str,
        account_id: str,
        niche_id: str,
        topic: str,
        content_format: str = "REEL",
        scheduled_date: Optional[str] = None,
        custom_idempotency_key: Optional[str] = None,
    ) -> PublishingRecord:
        """
        Create a new publishing job with duplicate detection.
        """
        with self._lock:
            idempotency_key = custom_idempotency_key or self.compute_idempotency_key(
                account_id=account_id,
                niche_id=niche_id,
                topic=topic,
                content_format=content_format,
                scheduled_date=scheduled_date,
            )

            if idempotency_key in self._idempotency_index:
                existing_job_id = self._idempotency_index[idempotency_key]
                existing_record = self._records.get(existing_job_id)
                if existing_record and existing_record.state not in (
                    PublishingState.FAILED,
                    PublishingState.CANCELLED,
                ):
                    raise DuplicateJobError(
                        f"Job with idempotency key '{idempotency_key}' already exists "
                        f"(job_id: {existing_job_id}, state: {existing_record.state.value})"
                    )

            now = time.time()
            record = PublishingRecord(
                job_id=job_id,
                account_id=account_id,
                niche_id=niche_id,
                idempotency_key=idempotency_key,
                content_format=content_format.upper(),
                state=PublishingState.CREATED,
                created_at=now,
                updated_at=now,
                topic=topic,
                history=[
                    StateTransition(
                        from_state="NONE",
                        to_state=PublishingState.CREATED.value,
                        timestamp=now,
                        actor="system",
                        reason="Job created",
                    )
                ],
            )
            self._records[job_id] = record
            self._idempotency_index[idempotency_key] = job_id
            self._save()
            logger.info(f"Created publishing job {job_id} for account {account_id}")
            return record

    def transition(
        self,
        job_id: str,
        to_state: PublishingState,
        actor: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PublishingRecord:
        """
        Atomically transition a job to a new state if valid.
        """
        with self._lock:
            record = self._records.get(job_id)
            if not record:
                raise KeyError(f"Job {job_id} not found in state machine.")

            from_state = record.state
            if to_state not in VALID_TRANSITIONS.get(from_state, set()):
                raise InvalidStateTransitionError(
                    f"Cannot transition job {job_id} from {from_state.value} to {to_state.value}. "
                    f"Allowed transitions: {[s.value for s in VALID_TRANSITIONS.get(from_state, set())]}"
                )

            now = time.time()
            record.state = to_state
            record.updated_at = now
            if metadata:
                if "instagram_container_id" in metadata:
                    record.instagram_container_id = metadata["instagram_container_id"]
                if "instagram_media_id" in metadata:
                    record.instagram_media_id = metadata["instagram_media_id"]
                if "instagram_permalink" in metadata:
                    record.instagram_permalink = metadata["instagram_permalink"]
                if "error_message" in metadata:
                    record.error_message = metadata["error_message"]
                if "rendered_assets" in metadata:
                    record.rendered_assets = metadata["rendered_assets"]
                if "script_data" in metadata:
                    record.script_data = metadata["script_data"]

            record.history.append(
                StateTransition(
                    from_state=from_state.value,
                    to_state=to_state.value,
                    timestamp=now,
                    actor=actor,
                    reason=reason,
                    metadata=metadata or {},
                )
            )
            self._save()
            logger.info(
                f"Transitioned job {job_id}: {from_state.value} -> {to_state.value} ({reason or 'no reason'})"
            )
            return record

    def get_record(self, job_id: str) -> Optional[PublishingRecord]:
        with self._lock:
            return self._records.get(job_id)

    def list_records(
        self,
        account_id: Optional[str] = None,
        state: Optional[PublishingState] = None,
    ) -> List[PublishingRecord]:
        with self._lock:
            results = list(self._records.values())
            if account_id:
                results = [r for r in results if r.account_id == account_id]
            if state:
                results = [r for r in results if r.state == state]
            return results

    def _save(self) -> None:
        try:
            temp_file = self.records_file.with_suffix(".tmp")
            data = {
                "records": {jid: r.to_dict() for jid, r in self._records.items()},
                "idempotency_index": self._idempotency_index,
                "saved_at": time.time(),
            }
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, self.records_file)
        except Exception as exc:
            logger.error(f"Failed to persist state machine records: {exc}")

    def _load(self) -> None:
        if not self.records_file.exists():
            return
        try:
            with open(self.records_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            records_raw = data.get("records", {})
            self._records = {
                jid: PublishingRecord.from_dict(r_data)
                for jid, r_data in records_raw.items()
            }
            self._idempotency_index = data.get("idempotency_index", {})
            logger.info(f"Loaded {len(self._records)} publishing records from disk.")
        except Exception as exc:
            logger.error(f"Failed to load state machine records: {exc}")
