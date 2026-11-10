import pytest
from pathlib import Path
from app.publishing.state_machine import (
    PublishingState,
    PublishingStateMachine,
    InvalidStateTransitionError,
    DuplicateJobError,
)


def test_valid_state_machine_flow(tmp_path):
    sm = PublishingStateMachine(storage_dir=tmp_path)
    job = sm.create_job(
        job_id="test_job_1",
        account_id="acc_123",
        niche_id="tech_ai",
        topic="OpenAI Releases New Voice Agent",
    )
    assert job.state == PublishingState.CREATED
    assert job.job_id == "test_job_1"

    # Move through states
    j = sm.transition("test_job_1", PublishingState.QUEUED, actor="test", reason="enqueued")
    assert j.state == PublishingState.QUEUED

    j = sm.transition("test_job_1", PublishingState.GENERATING, actor="test")
    assert j.state == PublishingState.GENERATING

    j = sm.transition("test_job_1", PublishingState.RENDERING, actor="test")
    assert j.state == PublishingState.RENDERING

    j = sm.transition("test_job_1", PublishingState.QUALITY_CHECK, actor="test")
    assert j.state == PublishingState.QUALITY_CHECK

    j = sm.transition("test_job_1", PublishingState.READY, actor="test")
    assert j.state == PublishingState.READY

    j = sm.transition(
        "test_job_1",
        PublishingState.UPLOADING,
        actor="test",
        metadata={"rendered_assets": ["output/reels/test.mp4"]},
    )
    assert j.state == PublishingState.UPLOADING

    j = sm.transition(
        "test_job_1",
        PublishingState.PROCESSING,
        actor="test",
        metadata={"instagram_container_id": "container_999"},
    )
    assert j.state == PublishingState.PROCESSING
    assert j.instagram_container_id == "container_999"

    j = sm.transition(
        "test_job_1",
        PublishingState.PUBLISHED,
        actor="test",
        metadata={"instagram_media_id": "media_777", "instagram_permalink": "https://instagr.am/p/xyz"},
    )
    assert j.state == PublishingState.PUBLISHED
    assert j.instagram_media_id == "media_777"
    assert len(j.history) == 9


def test_invalid_state_transition(tmp_path):
    sm = PublishingStateMachine(storage_dir=tmp_path)
    sm.create_job("test_job_2", "acc_1", "niche_1", "Topic A")

    # Cannot jump straight from CREATED to PUBLISHED
    with pytest.raises(InvalidStateTransitionError):
        sm.transition("test_job_2", PublishingState.PUBLISHED)


def test_duplicate_job_detection(tmp_path):
    sm = PublishingStateMachine(storage_dir=tmp_path)
    sm.create_job("job_orig", "acc_1", "tech", "Same Topic Name")

    with pytest.raises(DuplicateJobError):
        sm.create_job("job_dup", "acc_1", "tech", "Same Topic Name")


def test_dry_run_transition(tmp_path):
    sm = PublishingStateMachine(storage_dir=tmp_path)
    sm.create_job("dry_run_job", "acc_1", "tech", "Dry Run Topic")
    record = sm.transition("dry_run_job", PublishingState.DRY_RUN, reason="Dry run preview mode")
    assert record.state == PublishingState.DRY_RUN


def test_state_machine_persistence(tmp_path):
    sm1 = PublishingStateMachine(storage_dir=tmp_path)
    sm1.create_job("job_p1", "acc_x", "niche_y", "Persistent Topic")
    sm1.transition("job_p1", PublishingState.QUEUED)

    # Re-instantiate from same directory
    sm2 = PublishingStateMachine(storage_dir=tmp_path)
    loaded_job = sm2.get_record("job_p1")
    assert loaded_job is not None
    assert loaded_job.state == PublishingState.QUEUED
    assert loaded_job.topic == "Persistent Topic"
