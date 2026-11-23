import os
import re
from typing import Any, Dict, Tuple
from app.video.pronunciation_preprocessor import (
    ASTRO_CORE_TERMS as ASTRO_DEVNAGARI_MAP,
    PronunciationPreprocessor,
)


def clean_pronunciation_for_hindi(text: str) -> str:
    """
    Substitutes Roman / English astrological keywords with precise Devanagari phonemes
    and cleans formatting symbols to guarantee zero slurring or pronunciation distortion.
    Delegates to PronunciationPreprocessor for unified terminology and prosody.
    """
    return PronunciationPreprocessor.preprocess_for_tts(
        text=text,
        engine="sarvam",
        language="hindi",
    )



def determine_smart_voice(
    topic: str,
    voice_mode: str = "smart",
    gender: str = "male",
) -> Tuple[str, str, str]:
    """
    Smart Voice Switch:
    Selects the optimal language mode, target voice ID, and scriptural prompt profile.

    Returns:
    - (selected_language, selected_voice_id, script_mode)
    """
    mode = voice_mode.lower().strip()

    if mode in ["astrologer", "vedic", "pandit", "guruji"]:
        return "Hindi", "astrologer", "pure_hindi"

    if mode in ["hindi", "hi"]:
        voice_id = "astrologer" if gender == "male" else "hi-IN-SwaraNeural"
        return "Hindi", voice_id, "pure_hindi"

    if mode in ["english", "en"]:
        voice_id = "en-IN-PrabhatNeural" if gender == "male" else "en-IN-NeerjaNeural"
        return "English", voice_id, "pure_english"

    # SMART AUTOMATIC MODE (Topic-based intelligence)
    traditional_markers = [
        "dosh", "pitru", "shani", "sade sati", "havan", "kundli", "rahu", "ketu",
        "puja", "mantra", "sanctum", "peepal", "bhairav", "moksha", "karma", "surya", "graha"
    ]
    t_lower = topic.lower()
    is_traditional = any(m in t_lower for m in traditional_markers)

    if is_traditional:
        voice_id = "astrologer" if gender == "male" else "hi-IN-SwaraNeural"
        return "Hindi", voice_id, "pure_hindi"
    else:
        voice_id = "en-IN-PrabhatNeural" if gender == "male" else "en-IN-NeerjaNeural"
        return "English", voice_id, "pure_english"
