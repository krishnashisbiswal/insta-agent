import json
import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.gemini_client import check_health, generate_text, generate_json
from app.video.visual_generator import generate_scene_frame
from app.instagram.uploader import InstagramUploader
from app.video.tts_engine import detect_language
from app.autonomous.timing_engine import get_next_optimal_post_time, is_in_optimal_window
from app.analytics.seo_optimizer import verify_seo_integrity
from app.autonomous.content_manager import ContentManager


def test_gemini_health():
    health = check_health()
    assert health["status"] == "healthy"
    assert "response" in health


def test_gemini_json_generation():
    prompt = "Return a JSON object with key 'status' equal to 'success'."
    res = generate_json(prompt)
    assert isinstance(res, dict)
    assert res.get("status") == "success"


def test_language_detection():
    assert detect_language("Shani Dev aapko delay dete hain lekin deny nahi karte") in ("hindi", "hinglish")
    assert detect_language("Saturn is the planet of karma and discipline") == "english"


def test_visual_frame_generation(tmp_path):
    frame_path = tmp_path / "test_frame.jpg"
    im = generate_scene_frame(scene_index=0, theme_name="cosmic", output_path=frame_path)
    assert frame_path.exists()
    assert im.size == (1080, 1920)


def test_instagram_dry_run(tmp_path):
    dummy_video = tmp_path / "test_video.mp4"
    dummy_video.write_bytes(b"\x00" * 1024 * 200)

    uploader = InstagramUploader(user_id="test_id", access_token="test_tok")
    manifest = uploader.dry_run_preview(dummy_video, "Test caption #Astrology")
    assert manifest["mode"] == "DRY_RUN"
    assert manifest["video_exists"] is True
    assert manifest["caption_within_limit"] is True


def test_timing_engine():
    next_time, window_name = get_next_optimal_post_time("Asia/Kolkata")
    assert next_time is not None
    assert len(window_name) > 0
    in_peak, _ = is_in_optimal_window("Asia/Kolkata")
    assert isinstance(in_peak, bool)


def test_seo_integrity_audit():
    dummy_script = {
        "selected_hook": {"spoken": "Stop wearing black clothes."},
        "scenes": [
            {"scene_num": 1, "estimated_seconds": 3, "on_screen_text": "DON'T WEAR BLACK"},
            {"scene_num": 2, "estimated_seconds": 3, "on_screen_text": "DO THIS INSTEAD"},
        ]
    }
    caption = "Stop wearing black clothes on Saturday.\n\nSave this reel for your transit.\n\n#Astrology #Shani #Kundli"
    audit = verify_seo_integrity(dummy_script, caption, ["#Astrology", "#Shani", "#Kundli"])
    assert audit["overall_seo_score"] >= 80
    assert audit["verdict"] in ("OPTIMIZED", "GOOD")


def test_content_manager(tmp_path):
    queue_file = tmp_path / "queue.json"
    history_file = tmp_path / "history.json"
    cm = ContentManager(queue_file=queue_file, history_file=history_file)
    cm.save_queue([
        {"topic": "Topic 1", "target_seconds": 20},
        {"topic": "Topic 2", "target_seconds": 20},
        {"topic": "Topic 3", "target_seconds": 20},
    ])
    next_item = cm.pop_next_topic()
    assert next_item["topic"] == "Topic 1"
    assert len(cm.load_queue()) == 2
