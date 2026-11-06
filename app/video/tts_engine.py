import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    AUDIO_DIR,
    DEFAULT_VOICE,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    VOICE_ENGINE,
    VOICE_MAP,
)

import edge_tts

logger = logging.getLogger(__name__)


def clean_speech_text(text: str) -> str:
    """
    Removes visual formatting, emojis, markdown asterisks, and stage directions
    so AI voice engines (ElevenLabs & Neural) speak only clean, natural words.
    """
    if not text:
        return ""
    # Strip bracketed/parenthetical stage notes like [Pause] or (dramatic tone)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\((?:pause|whisper|beat|dramatic|tone|sound)[^)]*\)", "", text, flags=re.IGNORECASE)
    # Strip markdown symbols
    text = re.sub(r"[*_~`#]", "", text)
    # Strip emojis
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"[\u2600-\u27BF]", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_language(text: str) -> str:
    """Detect if text has Devanagari Hindi or Hinglish vs pure English."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hindi"

    hinglish_words = {
        "kare", "karna", "hoti", "hote", "hota", "hai", "hain", "shani", "graha",
        "kundli", "aap", "aapko", "lekin", "isliye", "sabse", "bhi", "yeh", "woh",
        "kaise", "kyun", "kya", "dekho", "samjho"
    }
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    matches = sum(1 for w in words if w in hinglish_words)
    if matches >= 2:
        return "hinglish"

    return "english"


def get_recommended_voice(text: str, gender: str = "male") -> str:
    """Select appropriate voice based on language and gender preference."""
    lang = detect_language(text)
    key = f"{lang}_{gender}" if f"{lang}_{gender}" in VOICE_MAP else lang
    return VOICE_MAP.get(key, DEFAULT_VOICE)


def is_valid_elevenlabs_voice_id(v: Optional[str]) -> bool:
    """Validate if string matches ElevenLabs voice ID format (alphanumeric, ~20 chars, no hyphens or Neural suffix)."""
    if not v:
        return False
    if "Neural" in v or "-" in v or " " in v:
        return False
    return len(v) >= 15 and v.isalnum()


async def generate_speech_async(
    text: str,
    output_path: Path,
    voice: Optional[str] = None,
    rate: str = "-5%",
    pitch: str = "+0Hz",
) -> Tuple[Path, float, List[Dict[str, Any]]]:
    """
    Generate audio using edge-tts with smooth, unhurried pacing.
    Returns:
    - Path to saved mp3
    - Total estimated audio duration in seconds
    - List of timestamped sentences: [{"text": ..., "start": float, "duration": float}]
    """
    clean_text = clean_speech_text(text)
    chosen_voice = voice or get_recommended_voice(clean_text)
    logger.info(f"Generating smooth neural TTS ('{chosen_voice}', rate={rate}) -> {output_path.name}")

    tts = edge_tts.Communicate(clean_text, voice=chosen_voice, rate=rate, pitch=pitch)

    sentences = []
    audio_chunks = []

    async for chunk in tts.stream():
        chunk_type = chunk.get("type")
        if chunk_type == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk_type == "SentenceBoundary":
            start_sec = chunk["offset"] / 10_000_000.0
            dur_sec = chunk["duration"] / 10_000_000.0
            sentences.append({
                "text": chunk.get("text", "").strip(),
                "start": round(start_sec, 3),
                "duration": round(dur_sec, 3),
                "end": round(start_sec + dur_sec, 3),
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for b in audio_chunks:
            f.write(b)

    total_dur = sentences[-1]["end"] if sentences else 0.0

    return output_path, total_dur, sentences


def generate_elevenlabs_speech(
    text: str,
    output_path: Path,
    voice_id: Optional[str] = None,
) -> Tuple[Path, float, List[Dict[str, Any]]]:
    """
    Generate studio-master human speech using ElevenLabs API (eleven_multilingual_v2).
    Provides fluent, natural inflection with zero robotic slurring.
    """
    import httpx
    from moviepy import AudioFileClip

    clean_text = clean_speech_text(text)
    api_key = os.getenv("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY).strip()
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not configured")

    # Select valid ElevenLabs voice ID (default: 'pNInz6obpgDQGcFmaJgB' -> Adam / Deep Narrative)
    target_voice = "pNInz6obpgDQGcFmaJgB"
    if is_valid_elevenlabs_voice_id(voice_id):
        target_voice = voice_id
    elif is_valid_elevenlabs_voice_id(ELEVENLABS_VOICE_ID):
        target_voice = ELEVENLABS_VOICE_ID

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": clean_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.50,          # Calm, natural stability with human intonation
            "similarity_boost": 0.85,   # High clarity and timbre richness
            "style": 0.15,              # Expressive cadence without slurring
            "use_speaker_boost": True,  # Crisp studio punch
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=45.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"ElevenLabs TTS failed ({resp.status_code}): {resp.text}")
        output_path.write_bytes(resp.content)

    with AudioFileClip(str(output_path)) as a:
        dur = a.duration

    return output_path, dur, []


def generate_speech(
    text: str,
    output_filename: Optional[str] = None,
    voice: Optional[str] = None,
    rate: str = "-5%",
    pitch: str = "+0Hz",
) -> Dict[str, Any]:
    """
    Unified voice synthesizer with smart priority routing:
    1. ElevenLabs Multilingual V2 (if key is present and engine is 'elevenlabs', 'auto', or 'smart')
    2. Seamless fallback to Microsoft Multilingual / Expressive Neural voice pack (rate=-5%, pitch=+0Hz)
    """
    clean_text = clean_speech_text(text)
    if not output_filename:
        safe_name = re.sub(r"[^\w\-]", "_", clean_text[:25].lower()).strip("_")
        output_filename = f"voice_{safe_name}.mp3"

    output_path = AUDIO_DIR / output_filename

    # Check if ElevenLabs is configured and eligible
    active_engine = os.getenv("VOICE_ENGINE", VOICE_ENGINE).strip().lower()
    active_key = os.getenv("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY).strip()

    can_use_elevenlabs = bool(active_key) and active_engine in ["elevenlabs", "auto", "smart", ""]

    if can_use_elevenlabs:
        try:
            logger.info("Synthesizing studio voice with ElevenLabs Multilingual V2...")
            out_p, dur, sents = generate_elevenlabs_speech(clean_text, output_path, voice_id=voice)
            target_v_id = voice if is_valid_elevenlabs_voice_id(voice) else (ELEVENLABS_VOICE_ID or "Adam (pNInz6obpgDQGcFmaJgB)")
            return {
                "audio_path": str(out_p),
                "duration": dur,
                "sentences": sents,
                "voice": f"ElevenLabs ({target_v_id})",
                "engine": "elevenlabs",
            }
        except Exception as exc:
            logger.warning(f"ElevenLabs synthesis notice ({exc}). Falling back to Expressive Neural voice...")

    # High-Fidelity Edge Neural Voice Fallback
    chosen_voice = voice if (voice and "Neural" in voice) else get_recommended_voice(clean_text)
    output_path, total_duration, sentences = asyncio.run(
        generate_speech_async(
            text=clean_text,
            output_path=output_path,
            voice=chosen_voice,
            rate=rate,
            pitch=pitch,
        )
    )

    return {
        "audio_path": str(output_path),
        "duration": total_duration,
        "sentences": sentences,
        "voice": chosen_voice,
        "engine": "edge_neural",
    }


if __name__ == "__main__":
    test_text = "Saturn delays your results to build rock-solid character. Never give up."
    print("Testing TTS generation...")
    res = generate_speech(test_text)
    print("Saved audio to:", res["audio_path"])
    print("Duration:", res["duration"], "seconds")
    print("Engine:", res["engine"])
    print("Voice:", res["voice"])
