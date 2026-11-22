import base64
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.video.tts_engine import (
    clean_speech_text,
    generate_sarvam_speech,
    generate_speech,
)


def test_clean_speech_text():
    raw = "✨ [Dramatic pause] *Om Namah Shivaya*! (deep breath) #Astrology 🪐"
    cleaned = clean_speech_text(raw)
    assert "[Dramatic pause]" not in cleaned
    assert "✨" not in cleaned
    assert "*" not in cleaned
    assert "Om Namah Shivaya! Astrology" in cleaned


def test_sarvam_missing_api_key_raises_value_error(tmp_path):
    out_file = tmp_path / "test.wav"
    with patch.dict(os.environ, {"SARVAM_API_KEY": ""}):
        with pytest.raises(ValueError, match="SARVAM_API_KEY is not configured"):
            generate_sarvam_speech("Test text", out_file)


def test_sarvam_api_mock_success(tmp_path):
    out_file = tmp_path / "test_sarvam.wav"
    dummy_wav_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    dummy_b64 = base64.b64encode(dummy_wav_content).decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "request_id": "test_req_123",
        "audios": [dummy_b64],
    }

    with patch.dict(os.environ, {"SARVAM_API_KEY": "fake_sarvam_test_key_123"}):
        with patch("httpx.Client.post", return_value=mock_resp):
            with patch("moviepy.AudioFileClip") as mock_audio:
                mock_audio.return_value.__enter__.return_value.duration = 4.2
                p, dur, _ = generate_sarvam_speech("नमस्ते", out_file, speaker="arjun")
                assert p.exists()
                assert dur == 4.2
                assert p.read_bytes() == dummy_wav_content


def test_generate_speech_fallback_to_edge_neural():
    with patch.dict(os.environ, {"SARVAM_API_KEY": "", "VOICE_ENGINE": "sarvam"}):
        res = generate_speech("Test speech fallback", output_filename="test_fb.mp3")
        assert res["engine"] == "edge_neural"
        assert res["duration"] > 0
        assert Path(res["audio_path"]).exists()


def test_sarvam_subh_speaker_and_bulbul_v4_mapping(tmp_path):
    out_file = tmp_path / "test_subh.wav"
    dummy_wav_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    dummy_b64 = base64.b64encode(dummy_wav_content).decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "request_id": "test_subh_123",
        "audios": [dummy_b64],
    }

    captured_payloads = []

    def mock_post(url, json=None, headers=None):
        captured_payloads.append(json)
        return mock_resp

    with patch.dict(os.environ, {"SARVAM_API_KEY": "fake_key_123"}):
        with patch("httpx.Client.post", side_effect=mock_post):
            with patch("moviepy.AudioFileClip") as mock_audio:
                mock_audio.return_value.__enter__.return_value.duration = 3.5

                # Test 'subh' alias and 'bulbul v4' model string
                generate_sarvam_speech(
                    "सूर्य और शनि का प्रभाव जानें",
                    out_file,
                    speaker="subh",
                    model="bulbul v4",
                )
                assert len(captured_payloads) == 1
                payload = captured_payloads[0]
                assert payload["speaker"] == "shubh_hi_devotional"
                assert payload["model"] == "bulbul:v4-flash"

                # Test 'astrologer' mapped to shubh_hi_devotional
                generate_sarvam_speech(
                    "सूर्य और शनि का प्रभाव जानें",
                    tmp_path / "test_astrologer.wav",
                    speaker="astrologer",
                )
                assert captured_payloads[1]["speaker"] == "shubh_hi_devotional"


def test_generate_speech_routes_astrologer_to_shubh(tmp_path):
    dummy_wav_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    dummy_b64 = base64.b64encode(dummy_wav_content).decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "request_id": "test_route_123",
        "audios": [dummy_b64],
    }

    captured_payloads = []

    def mock_post(url, json=None, headers=None):
        captured_payloads.append(json)
        return mock_resp

    with patch.dict(os.environ, {
        "SARVAM_API_KEY": "fake_key_123",
        "VOICE_ENGINE": "sarvam",
        "SARVAM_SPEAKER": "subh",
        "SARVAM_MODEL": "bulbul:v4-flash",
    }):
        with patch("httpx.Client.post", side_effect=mock_post):
            with patch("moviepy.AudioFileClip") as mock_audio:
                mock_audio.return_value.__enter__.return_value.duration = 4.0
                res = generate_speech("सूर्य और शनि का प्रभाव जानें", voice="astrologer")
                assert res["engine"] == "sarvam"
                assert captured_payloads[0]["speaker"] == "shubh_hi_devotional"
                assert captured_payloads[0]["model"] == "bulbul:v4-flash"
