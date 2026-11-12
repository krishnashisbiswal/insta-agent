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
    SARVAM_API_KEY,
    SARVAM_MODEL,
    SARVAM_PACE,
    SARVAM_SPEAKER,
    VOICE_ENGINE,
    VOICE_MAP,
)

import edge_tts

logger = logging.getLogger(__name__)


def clean_speech_text(text: str) -> str:
    """
    Removes visual formatting, emojis, markdown asterisks, and stage directions
    so AI voice engines (Sarvam AI & Neural) speak only clean, natural words.
    """
    if not text:
        return ""
    # Strip bracketed/parenthetical stage notes like [Pause] or (dramatic tone)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\([^)]*(?:pause|whisper|beat|dramatic|tone|sound|breath)[^)]*\)", "", text, flags=re.IGNORECASE)
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


async def generate_speech_async(
    text: str,
    output_path: Path,
    voice: Optional[str] = None,
    rate: str = "-5%",
    pitch: str = "+0Hz",
) -> Tuple[Path, float, List[Dict[str, Any]]]:
    """
    Generate audio using edge-tts with smooth, unhurried pacing.
    Includes automatic retry with exponential backoff for network resilience.
    Returns:
    - Path to saved mp3
    - Total estimated audio duration in seconds
    - List of timestamped sentences: [{"text": ..., "start": float, "duration": float}]
    """
    clean_text = clean_speech_text(text)
    chosen_voice = voice or get_recommended_voice(clean_text)
    logger.info(f"Generating smooth neural TTS ('{chosen_voice}', rate={rate}) -> {output_path.name}")

    max_attempts = 4
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
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

            if not audio_chunks:
                raise RuntimeError("Edge-TTS returned empty audio data.")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for b in audio_chunks:
                    f.write(b)

            total_dur = sentences[-1]["end"] if sentences else 0.0
            if total_dur <= 0.0 and output_path.exists():
                try:
                    from moviepy import AudioFileClip
                    with AudioFileClip(str(output_path)) as a:
                        total_dur = a.duration
                except Exception:
                    pass

            return output_path, total_dur, sentences
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                wait_time = 1.5 * attempt
                logger.warning(f"Edge-TTS attempt {attempt}/{max_attempts} hit {exc}. Retrying in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Edge-TTS failed after {max_attempts} attempts: {exc}")
                raise last_exc


def generate_sarvam_speech(
    text: str,
    output_path: Path,
    speaker: str = "arjun",
    language_code: Optional[str] = None,
    model: str = "bulbul:v4-flash",
    pace: float = 1.00,
) -> Tuple[Path, float, List[Dict[str, Any]]]:
    """
    Generate authentic Indic speech using Sarvam AI Text-to-Speech API.
    Features native Indian phonemes, authoritative Vedic prosody, and the 'arjun' voice persona.
    """
    import base64
    import httpx
    from moviepy import AudioFileClip

    clean_text = clean_speech_text(text)
    api_key = os.getenv("SARVAM_API_KEY", SARVAM_API_KEY).strip()
    if not api_key:
        raise ValueError(
            "SARVAM_API_KEY is not configured. Please get a free API key with ₹100 free credits from dashboard.sarvam.ai"
        )

    # Determine BCP-47 language code: "hi-IN" or "en-IN"
    if not language_code:
        detected = detect_language(clean_text)
        language_code = "hi-IN" if detected in ["hindi", "hinglish"] else "en-IN"

    # Map requested persona to valid Sarvam Bulbul:v4-flash speaker keys
    requested_sp = (speaker or os.getenv("SARVAM_SPEAKER", SARVAM_SPEAKER) or "arjun").lower()
    speaker_map = {
        "arjun": "ratan_hi_latenight_warm" if language_code == "hi-IN" else "girish_en_documentary",
        "arjun_hindi": "ratan_hi_latenight_warm",
        "arjun_english": "girish_en_documentary",
        "astrologer": "ratan_hi_latenight_warm",
        "calm": "ratan_hi_latenight_warm",
        "gentle": "ratan_hi_latenight_warm",
        "ratan": "ratan_hi_latenight_warm",
        "anand": "anand_hi_documentary",
        "mahesh": "mahesh_hi_documentary",
        "shubh": "shubh_hi_devotional",
        "girish": "girish_hi_devotional",
        "ishita": "ishita_hi_devotional",
    }
    target_speaker = speaker_map.get(requested_sp, requested_sp)
    target_model = model or os.getenv("SARVAM_MODEL", SARVAM_MODEL) or "bulbul:v4-flash"
    if target_model == "bulbul:v1":
        target_model = "bulbul:v4-flash"

    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "text": clean_text,
        "target_language_code": language_code,
        "speaker": target_speaker,
        "model": target_model,
        "pace": pace,
        "speech_sample_rate": 22050,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_wav = output_path.with_suffix(".temp.wav")

    max_retries = 3
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise RuntimeError(f"Sarvam AI TTS failed ({resp.status_code}): {resp.text}")

                data = resp.json()
                audio_b64 = None
                if "audios" in data and data["audios"]:
                    audio_b64 = data["audios"][0]
                elif "audio" in data:
                    audio_b64 = data["audio"]

                if not audio_b64:
                    raise RuntimeError(f"Sarvam AI returned no audio data: {data}")

                raw_bytes = base64.b64decode(audio_b64)
                temp_wav.write_bytes(raw_bytes)
                break
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                logger.warning(f"Sarvam TTS attempt {attempt} failed ({exc}). Retrying...")
                import time
                time.sleep(1.0)
            else:
                raise last_err

    # Convert to MP3 if required or finalize output
    if output_path.suffix.lower() == ".mp3":
        with AudioFileClip(str(temp_wav)) as clip:
            clip.write_audiofile(str(output_path), fps=44100, logger=None)
            dur = clip.duration
        temp_wav.unlink(missing_ok=True)
    else:
        temp_wav.replace(output_path)
        with AudioFileClip(str(output_path)) as a:
            dur = a.duration

    return output_path, dur, []


def generate_speech(
    text: str,
    output_filename: Optional[str] = None,
    voice: Optional[str] = None,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> Dict[str, Any]:
    """
    Unified voice synthesizer with calm, gentle Vedic astrologer delivery:
    1. Sarvam AI Indic Neural Voice (Arjun / Ratan Warm speaker) at calm, unhurried pace (1.00x)
    2. Seamless fallback to Microsoft Edge-TTS Expressive Neural voice pack (rate=+0%, pitch=+0Hz)
    """
    clean_text = clean_speech_text(text)
    if not output_filename:
        safe_name = re.sub(r"[^\w\-]", "_", clean_text[:25].lower()).strip("_")
        output_filename = f"voice_{safe_name}.mp3"

    output_path = AUDIO_DIR / output_filename

    # Check engine preference and API credentials
    active_engine = os.getenv("VOICE_ENGINE", VOICE_ENGINE).strip().lower()
    sarvam_key = os.getenv("SARVAM_API_KEY", SARVAM_API_KEY).strip()

    # Determine if Sarvam AI should be used:
    can_use_sarvam = False
    if sarvam_key and active_engine in ["sarvam", "sarvam_ai", "arjun", "auto", "smart"]:
        can_use_sarvam = True

    if can_use_sarvam:
        try:
            speaker_choice = "arjun"
            if voice and ("arjun" in voice.lower() or voice.startswith("sarvam:")):
                speaker_choice = voice.split(":")[-1] if ":" in voice else voice
            elif os.getenv("SARVAM_SPEAKER", SARVAM_SPEAKER):
                speaker_choice = os.getenv("SARVAM_SPEAKER", SARVAM_SPEAKER).strip()

            sarvam_pace = float(os.getenv("SARVAM_PACE", SARVAM_PACE or "1.00"))
            logger.info(f"Synthesizing authentic Indic voice with Sarvam AI (Speaker: {speaker_choice}, Pace: {sarvam_pace})...")
            out_p, dur, sents = generate_sarvam_speech(clean_text, output_path, speaker=speaker_choice, pace=sarvam_pace)
            return {
                "audio_path": str(out_p),
                "duration": dur,
                "sentences": sents,
                "voice": f"Sarvam AI ({speaker_choice})",
                "engine": "sarvam",
            }
        except Exception as exc:
            logger.warning(f"Sarvam AI synthesis notice ({exc}). Falling back to Expressive Neural voice...")

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
