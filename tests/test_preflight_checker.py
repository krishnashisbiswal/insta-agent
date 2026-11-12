import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.video.preflight_checker import PreFlightQualityGate, format_preflight_report


def test_preflight_quality_gate_structure():
    """Verify PreFlightQualityGate runs and computes quality scores correctly."""
    mock_script = {
        "topic": "Career Breakthrough Secrets 2026",
        "selected_hook": {
            "spoken": "If your career felt completely blocked throughout 2025, listen closely.",
            "on_screen": "CAREER BLOCKED IN 2025?",
            "score": 92.0,
            "formula_name": "Contrarian Truth",
        },
        "scenes": [
            {"scene_num": 1, "spoken_line": "Line 1", "on_screen_text": "HOOK", "estimated_seconds": 3},
            {"scene_num": 2, "spoken_line": "Line 2", "on_screen_text": "SATURN SHIFT", "estimated_seconds": 4},
            {"scene_num": 3, "spoken_line": "Line 3", "on_screen_text": "10TH HOUSE REMEDY", "estimated_seconds": 4},
            {"scene_num": 4, "spoken_line": "Line 4", "on_screen_text": "COMMENT YOUR SIGN", "estimated_seconds": 3},
        ],
    }

    caption = (
        "Why your career was delayed until 2026. The 10th house transit is shifting.\n\n"
        "Comment 'CAREER' below for your personalized transit report.\n\n"
        "#vedicastrology #careerastrology #saturn #astrology2026"
    )
    hashtags = ["#vedicastrology", "#careerastrology", "#saturn", "#astrology2026"]

    # Even with missing video, it should run gracefully and flag the missing file
    result = PreFlightQualityGate.verify_content_package(
        video_path=Path("non_existent_video.mp4"),
        script_data=mock_script,
        caption=caption,
        hashtags=hashtags,
        timezone_str="Asia/Kolkata",
    )

    assert "verdict" in result
    assert "readiness_score" in result
    assert "algorithm_timing" in result
    assert "checks" in result
    assert result["checks"]["caption_and_seo"]["passed"] is True
    assert result["checks"]["hook_and_script"]["passed"] is True
    assert result["checks"]["video_specs"]["passed"] is False

    # Timing check
    timing = result["algorithm_timing"]
    assert "next_optimal_slot" in timing
    assert "recommendation" in timing

    # Report formatter check
    report = format_preflight_report(result)
    assert "PRE-FLIGHT QUALITY AUDIT REPORT" in report
    assert "INSTAGRAM ALGORITHM POSTING TIME ENGINE" in report
