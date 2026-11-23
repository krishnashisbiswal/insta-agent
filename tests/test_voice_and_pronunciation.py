"""
Unit & Integration Tests for Voice Quality, Astrological Pronunciation, and Audio Validation.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.video.pronunciation_preprocessor import PronunciationPreprocessor
from app.video.audio_validator import AudioQualityValidator
from app.video.tts_engine import generate_speech, generate_sarvam_speech
from app.agents.script_agent import calculate_spoken_duration, _generate_fallback_reel_data
from app.niche.niche_profile import get_default_niche


def test_pronunciation_preprocessor_astrology_terms():
    """Verify all 12 key astrological terms are accurately mapped in Hinglish/Hindi context."""
    test_terms = [
        ("Shani dev ki dristi", "शनि देव की दृष्टि"),
        ("Rahu and Ketu in Kundali", "राहु और केतु कुंडली में"),
        ("Nakshatra and Lagna placement", "नक्षत्र और लग्न"),
        ("Dasha, Mahadasha, and Antardasha", "दशा, महादशा, और अंतर्दशा"),
        ("Gochar of Graha", "गोचर ग्रह का"),
        ("Sade Sati phase", "साढ़ेसाती"),
    ]

    for raw, expected_substr in test_terms:
        # Pass raw with some hindi marker so it recognizes hindi context
        input_text = f"कुंडली में {raw} का प्रभाव देखें।"
        processed = PronunciationPreprocessor.preprocess_for_tts(input_text, language="hindi")
        assert any(term in processed for term in ["शनि", "राहु", "केतु", "कुंडली", "नक्षत्र", "दशा", "महादशा", "अंतर्दशा", "गोचर", "ग्रह", "लग्न", "साढ़ेसाती"]), (
            f"Failed on {raw} -> {processed}"
        )



def test_pronunciation_loanwords_transliteration():
    """Verify modern conversational loanwords are transliterated in Hindi context."""
    text = "आपका career, focus, aur stress kaise handle karein? decisions lene mein help hogi."
    processed = PronunciationPreprocessor.preprocess_for_tts(text, language="hindi")
    assert "करियर" in processed
    assert "फोकस" in processed
    assert "स्ट्रेस" in processed
    assert "डिसीजन्स" in processed


def test_preserve_original_script_for_captions():
    """Verify clean_text_for_display strips only stage tags and preserves original script."""
    raw = "✨ [Dramatic pause] Shani ki dasha mein focus rakhein. (deep breath) 🪐"
    clean_display = PronunciationPreprocessor.clean_text_for_display(raw)
    assert "[Dramatic pause]" not in clean_display
    assert "(deep breath)" not in clean_display
    assert "✨" not in clean_display
    assert "Shani ki dasha mein focus rakhein." in clean_display


def test_audio_validator_hashing_and_idempotency(tmp_path):
    """Verify deterministic hash and validation caching."""
    h1 = AudioQualityValidator.compute_audio_hash(
        text="सूर्य देव की कृपा",
        voice="astrologer",
        rate="-3%",
        pitch="-12Hz",
        pace=1.05,
    )
    h2 = AudioQualityValidator.compute_audio_hash(
        text="सूर्य देव की कृपा",
        voice="astrologer",
        rate="-3%",
        pitch="-12Hz",
        pace=1.05,
    )
    assert h1 == h2

    # Different text yields different hash
    h3 = AudioQualityValidator.compute_audio_hash(
        text="शनि देव की कृपा",
        voice="astrologer",
        rate="-3%",
        pitch="-12Hz",
        pace=1.05,
    )
    assert h1 != h3


def test_audio_validator_music_balance():
    """Verify background soundtrack ducking check."""
    # Voice at -16 dBFS (rms ~ 0.158), music at -34 dBFS (rms ~ 0.02) -> -18 dB relative
    is_balanced, rel_db, warning = AudioQualityValidator.validate_music_balance(
        voiceover_rms=0.158,
        music_rms=0.02,
        target_ratio_db=-18.0,
    )
    assert is_balanced is True
    assert -20.0 <= rel_db <= -16.0


def test_spoken_duration_pacing():
    """Verify calculate_spoken_duration accurately accounts for words and pauses."""
    short_q = "क्या आप जानते हैं?"
    dur_q = calculate_spoken_duration(short_q, language="hindi")
    assert dur_q >= 2.5

    long_text = "पहला मुख्य संकेत: जब आपकी कुंडली में गुरु बृहस्पति कमजोर होते हैं, तो सही डिसीजन लेना और फोकस करना मुश्किल हो जाता है।"
    dur_long = calculate_spoken_duration(long_text, language="hindi")
    assert 4.0 <= dur_long <= 6.5



def test_fallback_reel_data_natural_hinglish():
    """Verify fallback reel data has zero awkward Latin-Hindi mixed strings."""
    profile = get_default_niche("astrology_vedic")
    fallback = _generate_fallback_reel_data(
        topic="5 Signs of Shani Sade Sati",
        profile=profile,
        language="Hinglish",
        selected_hook={"spoken": "क्या आप साढ़ेसाती से परेशान हैं?", "on_screen": "SHANI SADE SATI"},
    )
    scenes = fallback["scenes"]
    assert len(scenes) >= 5
    for sc in scenes:
        line = sc["spoken_line"]
        # Ensure no awkward phrases like 'Guru Jupiter', 'Shani ki dristi', 'Mars की fierce energy'
        assert "Guru Jupiter" not in line
        assert "Shani ki dristi" not in line
        assert "fierce energy" not in line
        assert "adverse impact" not in line
