import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from app.instagram.meta_graph_api import (
    MetaInstagramClient,
    MetaGraphAPIError,
)


def test_client_unconfigured_dry_run(tmp_path):
    dummy_video = tmp_path / "dummy.mp4"
    dummy_video.write_bytes(b"\x00" * 1024)

    client = MetaInstagramClient(instagram_account_id="", access_token="")
    assert not client.is_configured

    res = client.publish_reel_resumable(
        video_path=dummy_video,
        caption="Test unconfigured",
        dry_run=True,
    )
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["mode"] == "DRY_RUN"


def test_carousel_validation():
    client = MetaInstagramClient(instagram_account_id="123", access_token="token")
    # Carousel requires 2 to 10 images
    with pytest.raises(ValueError):
        client.publish_carousel(image_urls=["http://example.com/1.jpg"], caption="Too few")

    with pytest.raises(ValueError):
        client.publish_carousel(
            image_urls=[f"http://example.com/{i}.jpg" for i in range(11)],
            caption="Too many",
        )


@patch("requests.post")
@patch("requests.get")
def test_successful_reel_flow(mock_get, mock_post, tmp_path):
    dummy_video = tmp_path / "reel.mp4"
    dummy_video.write_bytes(b"\x00" * 2048)

    client = MetaInstagramClient(instagram_account_id="ig_user_456", access_token="EAABtest")

    # Mock init container
    init_mock = MagicMock()
    init_mock.json.return_value = {"id": "container_111", "uri": "https://rupload.facebook.com/111"}
    init_mock.status_code = 200

    # Mock binary upload
    upload_mock = MagicMock()
    upload_mock.status_code = 200
    upload_mock.content = b'{"success": true}'
    upload_mock.json.return_value = {"success": True}

    # Mock media publish
    publish_mock = MagicMock()
    publish_mock.status_code = 200
    publish_mock.json.return_value = {"id": "media_9999"}

    mock_post.side_effect = [init_mock, upload_mock, publish_mock]

    # Mock polling status -> FINISHED, and metadata call
    poll_mock = MagicMock()
    poll_mock.json.return_value = {"status_code": "FINISHED", "id": "container_111"}
    poll_mock.status_code = 200

    meta_mock = MagicMock()
    meta_mock.json.return_value = {
        "id": "media_9999",
        "permalink": "https://www.instagram.com/reel/Cxxxx/",
        "media_type": "VIDEO",
    }
    meta_mock.status_code = 200

    mock_get.side_effect = [poll_mock, meta_mock]

    res = client.publish_reel_resumable(
        video_path=dummy_video,
        caption="Automated production reel #tech",
        dry_run=False,
    )

    assert res["success"] is True
    assert res["media_id"] == "media_9999"
    assert res["container_id"] == "container_111"
    assert "https://www.instagram.com/reel/Cxxxx/" in res["permalink"]


@patch("requests.get")
def test_verify_account_unconfigured(mock_get):
    client = MetaInstagramClient(instagram_account_id="", access_token="")
    status = client.verify_account()
    assert status["status"] == "BLOCKED"
    assert status["configured"] is False
