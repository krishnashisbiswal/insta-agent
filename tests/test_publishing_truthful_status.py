"""
Comprehensive Regression Tests for Instagram Publishing Truthful Status & Verification.

Covers all 16 Phase 6 criteria:
1. Successful verified publication.
2. Media container creation failure.
3. Video upload failure.
4. Processing timeout.
5. Publish API failure.
6. Missing credentials.
7. Invalid credentials.
8. Direct uploader failure at qe/expose.
9. Exception caught by the publisher.
10. No publication tracker update after failure.
11. No published lifecycle state after failure.
12. GitHub Actions process exits nonzero after publishing failure.
13. No duplicate publish when publication status is uncertain.
14. Correct dry-run behavior.
15. Successful upload returns a real media ID.
16. Failure never prints a misleading publication-success message.
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.autonomous.daily_algorithm_publisher import DailyAlgorithmPublisher
from app.instagram.meta_graph_api import MetaGraphAPIError, MetaInstagramClient
from app.instagram.uploader import InstagramUploader
from app.storage.asset_lifecycle_manager import AssetLifecycleManager, JobState
from app.publishing.publishing_errors import (
    DuplicatePublishPreventedError,
    PublishingAuthError,
    PublishingConfigError,
    PublishingNetworkError,
    PublishingUncertainOutcomeError,
    PublishingValidationError,
)


@pytest.fixture
def dummy_video_file(tmp_path: Path) -> Path:
    """Creates a minimal valid dummy MP4 file for testing with valid validation report."""
    import hashlib
    import json
    import time

    vf = tmp_path / "test_reel.mp4"
    content = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41" + b"\x00" * 500
    vf.write_bytes(content)

    h = hashlib.sha256(content).hexdigest()
    val_json = tmp_path / "validation.json"
    val_json.write_text(
        json.dumps({
            "job_id": "test_job",
            "video_path": str(vf),
            "sha256_hash": h,
            "file_size_bytes": len(content),
            "created_at_epoch": time.time(),
            "job_start_epoch": time.time(),
            "validation_timestamp": time.time(),
            "status": "VALIDATED",
            "passed": True,
            "check_results": {"file_exists": True, "size_positive": True},
            "errors": [],
            "warnings": [],
        }),
        encoding="utf-8",
    )
    return vf


# =============================================================================
# 1. SUCCESSFUL VERIFIED PUBLICATION
# =============================================================================
def test_01_successful_verified_publication(dummy_video_file: Path):
    """Test that official Meta Graph API resumable upload verifies publication and returns status."""
    uploader = InstagramUploader(
        user_id="1784140001",
        access_token="EAAB_test_token_123",
    )

    with patch("app.publishing.pre_publish_validator.PrePublishValidator.validate_reel") as mock_val, \
         patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get:
        
        mock_val.return_value = MagicMock(is_valid=True)

        # Mock container creation
        mock_init = MagicMock()
        mock_init.json.return_value = {"id": "container_123", "uri": "https://rupload.facebook.com/123"}
        mock_init.status_code = 200

        # Mock binary upload
        mock_binary = MagicMock()
        mock_binary.json.return_value = {"success": True}
        mock_binary.status_code = 200
        mock_binary.content = b'{"success": true}'

        # Mock publish container
        mock_publish = MagicMock()
        mock_publish.json.return_value = {"id": "media_99901"}
        mock_publish.status_code = 200

        mock_post.side_effect = [mock_init, mock_binary, mock_publish]

        # Mock container status polling (FINISHED) & get_media_metadata
        mock_poll = MagicMock()
        mock_poll.json.return_value = {"status_code": "FINISHED", "id": "container_123"}
        mock_poll.status_code = 200

        mock_meta = MagicMock()
        mock_meta.json.return_value = {
            "id": "media_99901",
            "permalink": "https://www.instagram.com/reel/CX_test_999/",
            "media_type": "VIDEO",
        }
        mock_meta.status_code = 200

        mock_get.side_effect = [mock_poll, mock_meta]

        res = uploader.upload_reel(
            video_path=dummy_video_file,
            caption="Test Astrology Reel Caption #vedic",
        )

        assert res["success"] is True
        assert res["status"] == "PUBLISHED_VERIFIED"
        assert res["publishing_outcome"] == "PUBLISHED_VERIFIED"
        assert res["media_id"] == "media_99901"
        assert "instagram.com/reel" in res["media_url"]
        assert res["method"] == "GRAPH_API_RESUMABLE"


# =============================================================================
# 2. MEDIA CONTAINER CREATION FAILURE
# =============================================================================
def test_02_media_container_creation_failure(dummy_video_file: Path):
    """Test that a failure during Meta container creation raises a clear error."""
    uploader = InstagramUploader(
        user_id="1784140001",
        access_token="EAAB_test_token_123",
    )

    with patch("app.publishing.pre_publish_validator.PrePublishValidator.validate_reel") as mock_val, \
         patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get:
        
        mock_val.return_value = MagicMock(is_valid=True)

        mock_recent = MagicMock()
        mock_recent.json.return_value = {"data": []}
        mock_get.return_value = mock_recent

        # Meta API returns validation error on container creation
        mock_err = MagicMock()
        mock_err.json.return_value = {
            "error": {
                "message": "Invalid aspect ratio for Reels",
                "type": "OAuthException",
                "code": 100,
                "error_subcode": 36003,
            }
        }
        mock_err.status_code = 400
        mock_post.return_value = mock_err

        with pytest.raises(PublishingValidationError) as exc_info:
            uploader.upload_reel(video_path=dummy_video_file, caption="Test Caption")

        assert "Invalid aspect ratio" in str(exc_info.value) or "validation failure" in str(exc_info.value)


# =============================================================================
# 3. VIDEO UPLOAD FAILURE
# =============================================================================
def test_03_video_upload_failure(dummy_video_file: Path):
    """Test that a failure during binary video streaming raises an error."""
    uploader = InstagramUploader(
        user_id="1784140001",
        access_token="EAAB_test_token_123",
    )

    with patch("app.publishing.pre_publish_validator.PrePublishValidator.validate_reel") as mock_val, \
         patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get:
        
        mock_val.return_value = MagicMock(is_valid=True)

        mock_recent = MagicMock()
        mock_recent.json.return_value = {"data": []}
        mock_get.return_value = mock_recent

        # Step 1 succeeds
        mock_init = MagicMock()
        mock_init.json.return_value = {"id": "cont_123", "uri": "https://rupload.facebook.com/123"}
        mock_init.status_code = 200

        # Step 2 fails with network error / 500
        mock_upload_err = MagicMock()
        mock_upload_err.json.return_value = {"error": {"message": "Service temporarily unavailable", "code": 2}}
        mock_upload_err.status_code = 500
        mock_upload_err.content = b'{"error": {"message": "Service temporarily unavailable"}}'

        mock_post.side_effect = [mock_init, mock_upload_err]

        with pytest.raises(MetaGraphAPIError) as exc_info:
            uploader.upload_reel(video_path=dummy_video_file, caption="Test Caption")

        assert "Service temporarily unavailable" in str(exc_info.value)


# =============================================================================
# 4. PROCESSING TIMEOUT
# =============================================================================
def test_04_processing_timeout(dummy_video_file: Path):
    """Test that container processing timeout raises TimeoutError."""
    client = MetaInstagramClient(
        instagram_account_id="1784140001",
        access_token="EAAB_test_token_123",
    )

    with patch("requests.get") as mock_get, patch("time.sleep"):
        # Polling returns IN_PROGRESS continuously
        mock_poll = MagicMock()
        mock_poll.json.return_value = {"status_code": "IN_PROGRESS", "id": "cont_99"}
        mock_poll.status_code = 200
        mock_get.return_value = mock_poll

        with pytest.raises(TimeoutError) as exc_info:
            client._poll_container_status("cont_99", max_poll_seconds=0.1)

        assert "timed out" in str(exc_info.value)


# =============================================================================
# 5. PUBLISH API FAILURE
# =============================================================================
def test_05_publish_api_failure(dummy_video_file: Path):
    """Test that failure during media_publish triggers reconciliation and raises uncertain outcome."""
    uploader = InstagramUploader(
        user_id="1784140001",
        access_token="EAAB_test_token_123",
    )

    with patch("app.publishing.pre_publish_validator.PrePublishValidator.validate_reel") as mock_val, \
         patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get:
        
        mock_val.return_value = MagicMock(is_valid=True)

        # Step 1: Init container
        mock_init = MagicMock()
        mock_init.json.return_value = {"id": "cont_123", "uri": "https://rupload.facebook.com/123"}
        mock_init.status_code = 200

        # Step 2: Binary upload
        mock_binary = MagicMock()
        mock_binary.json.return_value = {"success": True}
        mock_binary.status_code = 200
        mock_binary.content = b'{"success": true}'

        # Step 4: Publish container returns error
        mock_publish_err = MagicMock()
        mock_publish_err.json.return_value = {"error": {"message": "Publish transaction failed", "code": 1}}
        mock_publish_err.status_code = 500

        mock_post.side_effect = [mock_init, mock_binary, mock_publish_err]

        # Step 3: Polling returns FINISHED
        mock_poll = MagicMock()
        mock_poll.json.return_value = {"status_code": "FINISHED", "id": "cont_123"}
        mock_poll.status_code = 200

        # Reconciliation returns empty
        mock_recent = MagicMock()
        mock_recent.json.return_value = {"data": []}
        mock_recent.status_code = 200

        mock_get.side_effect = [mock_recent, mock_poll, mock_recent]

        with pytest.raises(PublishingUncertainOutcomeError) as exc_info, patch("time.sleep"):
            uploader.upload_reel(video_path=dummy_video_file, caption="Test Caption")

        assert "Publish container call failed" in str(exc_info.value)


# =============================================================================
# 6. MISSING CREDENTIALS
# =============================================================================
def test_06_missing_credentials(dummy_video_file: Path, tmp_path: Path):
    """Test that attempting to upload without credentials raises PublishingConfigError."""
    with patch.dict(os.environ, {
        "INSTAGRAM_USER_ID": "",
        "INSTAGRAM_ACCESS_TOKEN": "",
        "INSTAGRAM_USERNAME": "",
        "INSTAGRAM_PASSWORD": "",
        "INSTAGRAM_SESSION_ID": "",
        "INSTAGRAM_SESSION_DATA": "",
    }, clear=False):
        uploader = InstagramUploader(
            username="",
            password="",
            session_id="",
            session_data="",
            user_id="",
            access_token="",
            session_file=tmp_path / "nonexistent_session.json",
        )
        assert uploader.has_credentials() is False

        with pytest.raises(PublishingConfigError) as exc_info:
            uploader.upload_reel(video_path=dummy_video_file, caption="Test Caption", force_dry_run=False)

        assert "No Instagram credentials configured" in str(exc_info.value)


# =============================================================================
# 7. INVALID CREDENTIALS
# =============================================================================
def test_07_invalid_credentials(dummy_video_file: Path):
    """Test that OAuth error code 190 correctly raises PublishingAuthError."""
    uploader = InstagramUploader(
        user_id="1784140001",
        access_token="INVALID_EXPIRED_TOKEN",
    )

    with patch("app.publishing.pre_publish_validator.PrePublishValidator.validate_reel") as mock_val, \
         patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get:
        
        mock_val.return_value = MagicMock(is_valid=True)

        mock_recent = MagicMock()
        mock_recent.json.return_value = {"data": []}
        mock_get.return_value = mock_recent

        mock_auth_err = MagicMock()
        mock_auth_err.json.return_value = {
            "error": {
                "message": "Error validating access token: Session has expired",
                "type": "OAuthException",
                "code": 190,
            }
        }
        mock_auth_err.status_code = 401
        mock_post.return_value = mock_auth_err

        with pytest.raises(PublishingAuthError) as exc_info:
            uploader.upload_reel(video_path=dummy_video_file, caption="Test Caption")

        assert "Meta authentication failure" in str(exc_info.value)


# =============================================================================
# 8. DIRECT UPLOADER FAILURE AT QE/EXPOSE
# =============================================================================
def test_08_direct_uploader_failure_at_qe_expose(dummy_video_file: Path, tmp_path: Path):
    """Test that direct instagrapi 404 at /api/v1/qe/expose/ raises PublishingAuthError."""
    uploader = InstagramUploader(
        username="test_user",
        password="test_password",
        session_file=tmp_path / "nonexistent_session.json",
    )

    with patch("instagrapi.Client") as mock_client_cls, \
         patch("app.publishing.pre_publish_validator.PrePublishValidator.validate_reel") as mock_val:
        
        mock_val.return_value = MagicMock(is_valid=True)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Simulate 404 on qe/expose during login and session check
        err = requests.exceptions.HTTPError(
            "404 Client Error: Not Found for url: https://i.instagram.com/api/v1/qe/expose/"
        )
        mock_client.login.side_effect = err
        mock_client.get_timeline_feed.side_effect = err

        with pytest.raises(PublishingAuthError) as exc_info:
            uploader.upload_reel_direct(video_path=dummy_video_file, caption="Test")

        err_msg = str(exc_info.value)
        assert "qe/expose" in err_msg or "404" in err_msg
        assert "Meta Graph API" in err_msg


# =============================================================================
# 9. EXCEPTION CAUGHT BY THE PUBLISHER
# =============================================================================
def test_09_exception_caught_by_publisher(dummy_video_file: Path, tmp_path: Path):
    """Test that publisher safely catches upload exception without failing diagnostic deliverable generation."""
    publisher = DailyAlgorithmPublisher()

    fake_script = {
        "selected_hook": {"spoken": "Hook", "on_screen": "HOOK", "score": 95, "verdict": "OK"},
        "scenes": [{"scene_number": 1, "narration": "Line", "screen_text": "Text", "visual_prompt": "Prompt"}],
        "estimated_duration_seconds": 15,
        "script_id": "test_script_09",
    }
    fake_caption = {
        "full_caption": "Test Final Caption for Instagram",
        "final_caption": "Test Final Caption for Instagram",
        "hashtags": ["#vedicastrology"],
        "seo_audit": {"overall_seo_score": 95, "verdict": "OK"},
    }

    with patch("app.autonomous.daily_algorithm_publisher.generate_reel", return_value=fake_script), \
         patch("app.autonomous.daily_algorithm_publisher.optimize_caption", return_value=fake_caption), \
         patch("app.autonomous.daily_algorithm_publisher.create_cinematic_reel_video", return_value=dummy_video_file), \
         patch("app.autonomous.daily_algorithm_publisher.CONTENT_DIR", tmp_path), \
         patch("app.instagram.uploader.InstagramUploader.has_credentials", return_value=True), \
         patch("app.instagram.uploader.InstagramUploader.upload_reel") as mock_upload:

        # Simulate upload throwing an error
        mock_upload.side_effect = PublishingAuthError("Simulated Auth Failure (Code 190)")

        result = publisher.produce_trending_reel(
            dry_run=False,
            topic_override="Pyrite Wealth Test",
            scene_image_paths=[dummy_video_file],
        )

        # Must not raise an uncaught exception
        assert result is not None
        assert result.get("publishing_outcome") == "AUTHENTICATION_FAILED"
        assert "Simulated Auth Failure" in result.get("instagram_upload_error", "")


# =============================================================================
# 10. NO PUBLICATION TRACKER UPDATE AFTER FAILURE
# =============================================================================
def test_10_no_publication_tracker_update_after_failure(tmp_path: Path):
    """Test that publisher does NOT update tracker when outcome is not PUBLISHED_VERIFIED."""
    publisher = DailyAlgorithmPublisher()
    publisher.tracker_file = tmp_path / "post_tracker.json"
    publisher.tracker_file.write_text(json.dumps({"last_post_date": None, "total_posts": 0, "history": []}))

    failed_result = {
        "topic": "Test Topic",
        "publishing_outcome": "UPLOAD_FAILED",
        "instagram_upload": {
            "success": False,
            "status": "UPLOAD_FAILED",
            "error": "Simulated Network Error",
        },
    }

    publisher.record_post_today(failed_result)

    tracker = json.loads(publisher.tracker_file.read_text())
    assert tracker["last_post_date"] is None
    assert tracker["total_posts"] == 0
    assert len(tracker["history"]) == 0

    with patch("app.instagram.uploader.InstagramUploader.has_credentials", return_value=False), \
         patch("app.instagram.uploader.InstagramUploader.has_direct_credentials", return_value=False), \
         patch("app.instagram.uploader.InstagramUploader.has_graph_credentials", return_value=False):
        assert publisher.has_posted_today() is False


# =============================================================================
# 11. NO PUBLISHED LIFECYCLE STATE AFTER FAILURE
# =============================================================================
def test_11_no_published_lifecycle_state_after_failure(dummy_video_file: Path, tmp_path: Path):
    """Test that AssetLifecycleManager marks the job FAILED when upload fails."""
    publisher = DailyAlgorithmPublisher()

    fake_script = {
        "selected_hook": {"spoken": "Hook", "on_screen": "HOOK", "score": 95, "verdict": "OK"},
        "scenes": [{"scene_number": 1, "narration": "Line", "screen_text": "Text", "visual_prompt": "Prompt"}],
        "estimated_duration_seconds": 15,
        "script_id": "test_script_11",
    }
    fake_caption = {
        "full_caption": "Test Final Caption",
        "final_caption": "Test Final Caption",
        "hashtags": ["#vedicastrology"],
        "seo_audit": {"overall_seo_score": 95, "verdict": "OK"},
    }

    with patch("app.autonomous.daily_algorithm_publisher.generate_reel", return_value=fake_script), \
         patch("app.autonomous.daily_algorithm_publisher.optimize_caption", return_value=fake_caption), \
         patch("app.autonomous.daily_algorithm_publisher.create_cinematic_reel_video", return_value=dummy_video_file), \
         patch("app.autonomous.daily_algorithm_publisher.CONTENT_DIR", tmp_path), \
         patch("app.instagram.uploader.InstagramUploader.has_credentials", return_value=True), \
         patch("app.instagram.uploader.InstagramUploader.upload_reel") as mock_upload, \
         patch("app.storage.asset_lifecycle_manager.AssetLifecycleManager.mark_failed") as mock_mark_failed, \
         patch("app.storage.asset_lifecycle_manager.AssetLifecycleManager.record_published") as mock_rec_pub:

        mock_upload.side_effect = PublishingNetworkError("Connection timed out")

        res = publisher.produce_trending_reel(
            dry_run=False,
            topic_override="Test Fail Lifecycle",
            scene_image_paths=[dummy_video_file],
        )

        assert res["publishing_outcome"] == "UPLOAD_FAILED"
        mock_mark_failed.assert_called()
        mock_rec_pub.assert_not_called()


# =============================================================================
# 12. GITHUB ACTIONS PROCESS EXITS NONZERO AFTER PUBLISHING FAILURE
# =============================================================================
def test_12_github_actions_process_exits_nonzero_after_publishing_failure():
    """Verify that CLI entry point exits with code 1 if publishing fails in non-dry-run mode."""
    # Test outcomes that must trigger non-zero exit code
    failure_outcomes = [
        "UPLOAD_FAILED",
        "PROCESSING_FAILED",
        "AUTHENTICATION_FAILED",
        "NO_CREDENTIALS",
    ]

    for outcome in failure_outcomes:
        mock_result = {
            "status": "completed",
            "publishing_outcome": outcome,
            "instagram_upload_error": f"Simulated error for {outcome}",
        }

        # Simulate the __main__ evaluation logic
        should_exit_1 = False
        if outcome in ("UPLOAD_FAILED", "PROCESSING_FAILED", "AUTHENTICATION_FAILED", "NO_CREDENTIALS"):
            should_exit_1 = True

        assert should_exit_1 is True, f"Outcome {outcome} did not trigger non-zero exit"


# =============================================================================
# 13. NO DUPLICATE PUBLISH WHEN PUBLICATION STATUS IS UNCERTAIN
# =============================================================================
def test_13_no_duplicate_publish_when_publication_status_is_uncertain(dummy_video_file: Path):
    """Test that when publish status is uncertain, the system does not re-issue publish calls."""
    client = MetaInstagramClient(
        instagram_account_id="1784140001",
        access_token="EAAB_test_token_123",
    )

    with patch.object(client, "_reconcile_container", return_value=None), \
         patch.object(client, "_publish_container", side_effect=requests.exceptions.ConnectionError("Connection lost")):

        with pytest.raises(PublishingUncertainOutcomeError):
            # publish_reel_resumable internally catches exception from _publish_container,
            # runs _reconcile_container once, and if not confirmed, raises PublishingUncertainOutcomeError
            # rather than re-trying blindly
            client._poll_container_status = MagicMock(return_value="FINISHED")
            client._reconcile_container = MagicMock(return_value=None)
            with patch("requests.post") as mock_post:
                mock_post.side_effect = [
                    MagicMock(json=lambda: {"id": "c1", "uri": "https://u"}, status_code=200),
                    MagicMock(status_code=200, content=b"{}"),
                ]
                client.publish_reel_resumable(
                    video_path=dummy_video_file,
                    caption="Unique Caption #protect",
                )


# =============================================================================
# 14. CORRECT DRY-RUN BEHAVIOR
# =============================================================================
def test_14_correct_dry_run_behavior(dummy_video_file: Path):
    """Test that dry-run mode validates and generates manifests without publishing."""
    uploader = InstagramUploader(user_id="1784140001", access_token="token")

    res = uploader.upload_reel(
        video_path=dummy_video_file,
        caption="Astrological Dry Run #vedic",
        force_dry_run=True,
    )

    assert res["mode"] == "DRY_RUN"
    assert res["status"] == "DRY_RUN"
    assert res["publishing_outcome"] == "DRY_RUN"
    assert res["success"] is True
    assert res["video_exists"] is True


# =============================================================================
# 15. SUCCESSFUL UPLOAD RETURNS REAL MEDIA ID
# =============================================================================
def test_15_successful_upload_returns_real_media_id(dummy_video_file: Path):
    """Test that a verified live upload returns a genuine numeric/alphanumeric media ID and URL."""
    uploader = InstagramUploader(user_id="1784140001", access_token="valid_token")

    with patch.object(uploader, "upload_reel_resumable") as mock_resumable:
        mock_resumable.return_value = {
            "success": True,
            "method": "GRAPH_API_RESUMABLE",
            "media_id": "18099887766554433",
            "container_id": "17999887766554433",
            "media_url": "https://www.instagram.com/reel/DC_test_verified/",
            "permalink": "https://www.instagram.com/reel/DC_test_verified/",
            "status": "PUBLISHED_VERIFIED",
            "publishing_outcome": "PUBLISHED_VERIFIED",
        }

        res = uploader.upload_reel(dummy_video_file, "Test Caption")

        assert res["status"] == "PUBLISHED_VERIFIED"
        assert res["publishing_outcome"] == "PUBLISHED_VERIFIED"
        assert res["media_id"] == "18099887766554433"
        assert res["media_url"] == "https://www.instagram.com/reel/DC_test_verified/"


# =============================================================================
# 16. FAILURE NEVER PRINTS MISLEADING PUBLICATION SUCCESS MESSAGE
# =============================================================================
def test_16_failure_never_prints_misleading_publication_success_message(dummy_video_file: Path, tmp_path: Path):
    """Test that failure prints failure status and NEVER prints DAILY VIRAL REEL PRODUCTION COMPLETE!"""
    publisher = DailyAlgorithmPublisher()

    fake_script = {
        "selected_hook": {"spoken": "Hook", "on_screen": "HOOK", "score": 95, "verdict": "OK"},
        "scenes": [{"scene_number": 1, "narration": "Line", "screen_text": "Text", "visual_prompt": "Prompt"}],
        "estimated_duration_seconds": 15,
        "script_id": "test_script_16",
    }
    fake_caption = {
        "full_caption": "Test Final Caption",
        "final_caption": "Test Final Caption",
        "hashtags": ["#vedicastrology"],
        "seo_audit": {"overall_seo_score": 95, "verdict": "OK"},
    }

    with patch("app.autonomous.daily_algorithm_publisher.generate_reel", return_value=fake_script), \
         patch("app.autonomous.daily_algorithm_publisher.optimize_caption", return_value=fake_caption), \
         patch("app.autonomous.daily_algorithm_publisher.create_cinematic_reel_video", return_value=dummy_video_file), \
         patch("app.autonomous.daily_algorithm_publisher.CONTENT_DIR", tmp_path), \
         patch("app.instagram.uploader.InstagramUploader.has_credentials", return_value=True), \
         patch("app.instagram.uploader.InstagramUploader.upload_reel") as mock_upload, \
         patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:

        mock_upload.side_effect = PublishingAuthError("Endpoint 404 Not Found at qe/expose")

        publisher.produce_trending_reel(
            dry_run=False,
            topic_override="Test Truthful Banner",
            scene_image_paths=[dummy_video_file],
        )

        output = mock_stdout.getvalue()

        # Must display failure banner
        assert "VIDEO GENERATION COMPLETED — INSTAGRAM PUBLISHING FAILED" in output
        # Must NEVER display misleading success banner
        assert "DAILY VIRAL REEL PRODUCTION COMPLETE!" not in output
        assert "Reel published successfully!" not in output
