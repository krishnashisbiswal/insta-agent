import pytest
from pathlib import Path
from unittest.mock import MagicMock
from app.publishing.publishing_service import PublishingService
from app.publishing.state_machine import PublishingState, DuplicateJobError


def test_publishing_service_dry_run_guard(tmp_path):
    ps = PublishingService(storage_dir=tmp_path)
    dummy_video = tmp_path / "dummy_reel.mp4"
    dummy_video.write_bytes(b"\x00" * 512)

    # By default, AUTO_PUBLISH is not enabled, so it should safely transition to DRY_RUN
    rec = ps.publish_reel(
        account_id="acc_abc",
        niche_id="tech",
        topic="AI Updates 2026",
        video_path=dummy_video,
        caption="New AI models launched!",
        force_dry_run=True,
    )
    assert rec.state == PublishingState.DRY_RUN
    assert rec.job_id.startswith("job_")


def test_publishing_service_mocked_live(tmp_path):
    ps = PublishingService(storage_dir=tmp_path)
    dummy_video = tmp_path / "dummy_reel.mp4"
    dummy_video.write_bytes(b"\x00" * 512)

    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.publish_reel_resumable.return_value = {
        "success": True,
        "container_id": "c_123",
        "media_id": "m_456",
        "permalink": "https://instagram.com/reel/xyz",
    }

    # Enable auto publish via monkeypatch
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("AUTO_PUBLISH", "true")
        rec = ps.publish_reel(
            account_id="acc_abc",
            niche_id="tech",
            topic="Live Reel Post",
            video_path=dummy_video,
            caption="Live test caption",
            meta_client=mock_client,
        )
        assert rec.state == PublishingState.PUBLISHED
        assert rec.instagram_media_id == "m_456"
        assert rec.instagram_permalink == "https://instagram.com/reel/xyz"


def test_publishing_service_duplicate_prevented(tmp_path):
    ps = PublishingService(storage_dir=tmp_path)
    dummy_video = tmp_path / "dummy_reel.mp4"
    dummy_video.write_bytes(b"\x00" * 512)

    ps.publish_reel(
        account_id="acc_1",
        niche_id="tech",
        topic="Identical Topic",
        video_path=dummy_video,
        caption="Caption",
        force_dry_run=True,
    )

    # Submitting identical topic for same account raises DuplicateJobError
    with pytest.raises(DuplicateJobError):
        ps.publish_reel(
            account_id="acc_1",
            niche_id="tech",
            topic="Identical Topic",
            video_path=dummy_video,
            caption="Caption",
            force_dry_run=True,
        )
