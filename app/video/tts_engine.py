import asyncio
import logging
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
    VOICE_MAP,
    VOICE_ENGINE,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
)

import edge_tts

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """Detect if text has Devanagari Hindi or Hinglish vs pure English."""
    # Check for Devanagari script characters
    if re.search(r"[\u0900-\u097F]", text):
        return "hindi"

    # Common Hinglish markers
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


async def generate_speech_async(
    text: str,
    output_path: Path,
    voice: Optional[str] = None,
    rate: str = "-2%",
    pitch: str = "-1Hz",
) -> Tuple[Path, float, List[Dict[str, Any]]]:
    """
    Generate audio using edge-tts and extract SentenceBoundary timestamps.
    Returns:
    - Path to saved mp3
    - Total estimated audio duration in seconds
    - List of timestamped sentences: [{"text": ..., "start": float, "duration": float}]
    """
    chosen_voice = voice or get_recommended_voice(text)
    logger.info(f"Generating TTS using voice '{chosen_voice}' -> {output_path.name}")

    tts = edge_tts.Communicate(text, voice=chosen_voice, rate=rate, pitch=pitch)

    sentences = []
    audio_chunks = []

    async for chunk in tts.stream():
        chunk_type = chunk.get("type")
        if chunk_type == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk_type == "SentenceBoundary":
            # Offset and duration are in 100-nanosecond units (10,000,000 units = 1 second)
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

    # Calculate total duration
    total_dur = sentences[-1]["end"] if sentences else 0.0

    return output_path, total_dur, sentences


def generate_elevenlabs_speech(
    text: str,
    output_path: Path,
    voice_id: Optional[str] = None,
) -> Tuple[Path, float, List[Dict[str, Any]]]:
    """Generate audio using ElevenLabs API for human-indistinguishable quality."""
    import httpx
    from moviepy import AudioFileClip

    target_voice = voice_id or ELEVENLABS_VOICE_ID or "pNInz6obpgDQGcFmaJgB"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
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
    rate: str = "-2%",
    pitch: str = "-1Hz",
) -> Dict[str, Any]:
    """
    Synchronous wrapper for generating speech and timing metadata.
    Automatically uses ElevenLabs if ELEVENLABS_API_KEY is configured in .env,
    otherwise uses high-fidelity Microsoft Multilingual/Expressive Neural voices.
    """
    if not output_filename:
        safe_name = re.sub(r"[^\w\-]", "_", text[:25].lower()).strip("_")
        output_filename = f"voice_{safe_name}.mp3"

    output_path = AUDIO_DIR / output_filename

    # Use ElevenLabs only if explicitly enabled via VOICE_ENGINE == "elevenlabs"
    if VOICE_ENGINE == "elevenlabs" and ELEVENLABS_API_KEY:
        try:
            logger.info("Generating studio human voice via ElevenLabs...")
            out_p, dur, sents = generate_elevenlabs_speech(text, output_path, voice_id=voice)
            return {
                "audio_path": str(out_p),
                "duration": dur,
                "sentences": sents,
                "voice": f"ElevenLabs ({voice or ELEVENLABS_VOICE_ID})",
                "engine": "elevenlabs",
            }
        except Exception as exc:
            logger.warning(f"ElevenLabs error ({exc}), falling back to Expressive Neural voice...")

    chosen_voice = voice or get_recommended_voice(text)
    output_path, total_duration, sentences = asyncio.run(
        generate_speech_async(
            text=text,
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
    print("Sentences:", res["sentences"])
