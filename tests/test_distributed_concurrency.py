"""
Distributed Concurrency, Leasing, Worker & Idempotency Test Suite.

Tests:
- Distributed execution leases (worker claiming, lease timeouts).
- Abandoned job recovery: expired leases automatically reclaimed by next worker.
- Active heartbeat lease renewal.
- Complete background worker pipeline execution (CREATED -> GENERATING -> RENDERING -> QUALITY_CHECK -> READY).
- Database-level duplicate job prevention via SHA-256 idempotency keys.
- Pre-publish Meta reconciliation to eliminate duplicate uploads after network timeouts.
"""

import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.models.saas_models import InstagramAccount, Organization, PublishingJobModel, get_db_session
from app.publishing.publishing_service import PublishingService
from app.publishing.state_machine import (
    DatabasePublishingStateMachine,
    DuplicateJobError,
    PublishingState,
    PublishingStateMachine,
)
from app.workers.publishing_worker import PublishingWorker


@pytest.fixture(autouse=True)
def clean_jobs():
    db = next(get_db_session())
    db.query(PublishingJobModel).filter(
        PublishingJobModel.state.in_([
            PublishingState.QUEUED.value,
            PublishingState.GENERATING.value,
            PublishingState.RENDERING.value,
            PublishingState.UPLOADING.value,
        ])
    ).delete(synchronize_session=False)
    db.commit()
    yield


@pytest.fixture
def test_account(tmp_path):
    db = next(get_db_session())
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    org = Organization(org_id=org_id, name="Concurrency Test Org")
    db.add(org)

    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    account = InstagramAccount(
        account_id=account_id,
        org_id=org_id,
        username=f"test_concurrency_{uuid.uuid4().hex[:4]}",
        niche_id="tech_ai",
        auto_publish=False,
    )
    db.add(account)
    db.commit()
    return {"account_id": account_id, "org_id": org_id}


def test_distributed_worker_claiming_and_leasing(test_account):
    db = next(get_db_session())
    job_id = f"job_lease_{uuid.uuid4().hex[:8]}"

    # Create job in QUEUED state
    job = DatabasePublishingStateMachine.create_job(
        db=db,
        job_id=job_id,
        account_id=test_account["account_id"],
        niche_id="tech_ai",
        topic="Distributed Computing in 2026",
    )
    DatabasePublishingStateMachine.transition(db=db, job_id=job_id, to_state=PublishingState.QUEUED)

    # Worker 1 claims the job with a 60 second lease
    claimed1 = DatabasePublishingStateMachine.claim_next_job(db=db, worker_id="worker_1", lease_seconds=60)
    assert claimed1 is not None
    assert claimed1.job_id == job_id
    assert claimed1.claimed_by == "worker_1"
    assert claimed1.lease_expires_at > time.time()

    # Worker 2 attempts to claim next job immediately -> None available (locked by Worker 1)
    claimed2 = DatabasePublishingStateMachine.claim_next_job(db=db, worker_id="worker_2", lease_seconds=60)
    assert claimed2 is None

    # Worker 1 renews lease
    renewed = DatabasePublishingStateMachine.renew_lease(db=db, job_id=job_id, worker_id="worker_1", additional_seconds=120)
    assert renewed is True

    # Worker 2 cannot renew Worker 1's lease
    unauthorized_renew = DatabasePublishingStateMachine.renew_lease(db=db, job_id=job_id, worker_id="worker_2", additional_seconds=120)
    assert unauthorized_renew is False


def test_abandoned_job_recovery_after_lease_expiry(test_account):
    db = next(get_db_session())
    job_id = f"job_abandon_{uuid.uuid4().hex[:8]}"

    # Create job and advance to GENERATING
    DatabasePublishingStateMachine.create_job(
        db=db,
        job_id=job_id,
        account_id=test_account["account_id"],
        niche_id="tech_ai",
        topic="Fault Tolerant Systems",
    )
    DatabasePublishingStateMachine.transition(db=db, job_id=job_id, to_state=PublishingState.GENERATING)

    # Artificially assign an expired lease to worker_crashed
    j = db.query(PublishingJobModel).filter_by(job_id=job_id).first()
    j.claimed_by = "worker_crashed"
    j.lease_expires_at = time.time() - 10.0  # Expired 10 seconds ago
    db.commit()

    # Worker_healthy claims next job -> recovers the abandoned job!
    recovered = DatabasePublishingStateMachine.claim_next_job(db=db, worker_id="worker_healthy", lease_seconds=90)
    assert recovered is not None
    assert recovered.job_id == job_id
    assert recovered.claimed_by == "worker_healthy"


def test_background_worker_end_to_end_pipeline(test_account):
    db = next(get_db_session())
    job_id = f"job_worker_{uuid.uuid4().hex[:8]}"

    # Create job in QUEUED state
    DatabasePublishingStateMachine.create_job(
        db=db,
        job_id=job_id,
        account_id=test_account["account_id"],
        niche_id="tech_ai",
        topic="Neural Network Optimization in PyTorch",
        content_format="CAROUSEL",
    )
    DatabasePublishingStateMachine.transition(db=db, job_id=job_id, to_state=PublishingState.QUEUED)

    # Instantiate worker and execute one job
    worker = PublishingWorker(worker_id="worker_test_runner", lease_duration_seconds=60)
    executed_job_id = worker.run_once()
    assert executed_job_id == job_id

    # Verify job advanced through pipeline to READY state
    updated_job = db.query(PublishingJobModel).filter_by(job_id=job_id).first()
    assert updated_job.state == PublishingState.READY.value
    assert updated_job.rendered_assets_json is not None
    assert len(updated_job.history) >= 4  # CREATED -> QUEUED -> GENERATING -> RENDERING -> QUALITY_CHECK -> READY


def test_idempotency_key_collision_prevention(test_account):
    db = next(get_db_session())
    topic = "Unique Machine Learning Architectures"

    # 1. Create first job
    job1 = DatabasePublishingStateMachine.create_job(
        db=db,
        job_id=f"job_first_{uuid.uuid4().hex[:6]}",
        account_id=test_account["account_id"],
        niche_id="tech_ai",
        topic=topic,
    )
    assert job1 is not None

    # 2. Attempting to create duplicate job with identical topic & account raises DuplicateJobError
    with pytest.raises(DuplicateJobError):
        DatabasePublishingStateMachine.create_job(
            db=db,
            job_id=f"job_dup_{uuid.uuid4().hex[:6]}",
            account_id=test_account["account_id"],
            niche_id="tech_ai",
            topic=topic,  # Identical topic!
        )


def test_meta_pre_retry_reconciliation(test_account):
    db = next(get_db_session())
    account = db.query(InstagramAccount).filter_by(account_id=test_account["account_id"]).first()
    ps = PublishingService(db_session=db)

    mock_client = MagicMock()
    mock_client.is_configured = True
    # Simulate Meta API returning a media item matching our topic
    mock_client.get_recent_media.return_value = [
        {
            "id": "meta_17999888222",
            "caption": "Exploring AI Agents in 2026 and Autonomous Architecture #ai",
            "permalink": "https://instagram.com/p/meta17999",
        }
    ]

    reconciled = ps.reconcile_with_meta(
        account=account,
        topic="Exploring AI Agents in 2026",
        meta_client=mock_client,
    )
    assert reconciled is not None
    assert reconciled["id"] == "meta_17999888222"
    assert reconciled["permalink"] == "https://instagram.com/p/meta17999"
