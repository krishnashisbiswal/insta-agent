import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows UTF-8 console output
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.agents.caption_agent import optimize_caption
from app.agents.script_agent import generate_reel
from app.autonomous.content_manager import ContentManager
from app.instagram.uploader import InstagramUploader
from app.video.tts_engine import generate_speech
from app.video.video_composer import create_reel_video
from config.settings import (
    CONTENT_LANGUAGE,
    CONTENT_NICHE,
    CONTENT_THEME,
    OUTPUT_DIR,
)

logger = logging.getLogger("AutonomousAgent")


def run_autonomous_reel_cycle(
    niche: Optional[str] = None,
    language: Optional[str] = None,
    theme_name: Optional[str] = None,
    force_dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Execute a completely autonomous Reel cycle:
    1. Select or brainstorm fresh viral topic
    2. Write, humanize & score script with Gemini
    3. Generate natural neural voiceover audio
    4. Render 1080x1920 vertical video
    5. Optimize caption, hashtags & CTA
    6. Upload directly to Instagram
    7. Save history log
    """
    target_niche = niche or CONTENT_NICHE
    target_lang = language or CONTENT_LANGUAGE
    target_theme = theme_name or CONTENT_THEME

    print("\n" + "=" * 70)
    print("       AUTONOMOUS INSTAGRAM REEL AGENT (1-CLICK ENGINE)")
    print("=" * 70)
    print(f"Time:         {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Niche:        {target_niche}")
    print(f"Language:     {target_lang}")
    print(f"Theme:        {target_theme}")
    print("=" * 70)

    # 1. TOPIC SELECTION
    cm = ContentManager()
    topic_data = cm.pop_next_topic(niche=target_niche, language=target_lang)
    topic = topic_data.get("topic", "Astrology Secrets")
    target_duration = int(topic_data.get("target_seconds", 25))

    print(f"\n[AUTONOMOUS STEP 1/6] Selected Topic: \"{topic}\"")
    if topic_data.get("angle"):
        print(f"  Angle: {topic_data['angle']}")

    # 2. SCRIPT GENERATION & HOOK SCORING
    print("\n[AUTONOMOUS STEP 2/6] Generating Reel script & hook options with Gemini...")
    script_data = generate_reel(
        topic=topic,
        niche=target_niche,
        language=target_lang,
        duration=target_duration,
    )
    hook = script_data["selected_hook"]
    print(f"  Winning Hook: \"{hook['spoken']}\"")
    print(f"  On-Screen:    \"{hook['on_screen']}\"")
    print(f"  Hook Score:   {hook.get('score')}/100 [{hook.get('verdict')}]")
    print(f"  Total Scenes: {len(script_data['scenes'])}")

    # 3. NEURAL VOICEOVER GENERATION
    print("\n[AUTONOMOUS STEP 3/6] Generating studio neural voiceover audio...")
    audio_meta = generate_speech(text=script_data["full_script"])
    audio_path = audio_meta["audio_path"]
    actual_duration = audio_meta["duration"]
    print(f"  Audio File:   {Path(audio_path).name}")
    print(f"  Duration:     {actual_duration:.2f}s (Voice: {audio_meta['voice']})")

    # 4. 1080x1920 VIDEO COMPOSITION
    print("\n[AUTONOMOUS STEP 4/6] Rendering 1080x1920 vertical Reel video...")
    video_path = create_reel_video(
        script_data=script_data,
        audio_path=audio_path,
        theme_name=target_theme,
    )
    print(f"  Video File:   {video_path.name}")

    # 5. CAPTION OPTIMIZATION
    print("\n[AUTONOMOUS STEP 5/6] Optimizing Instagram caption with Gemini...")
    caption_res = optimize_caption(
        topic=topic,
        script_hook=hook["spoken"],
        draft_caption=script_data["caption"],
        niche=target_niche,
    )
    final_caption = caption_res["full_caption"]
    print(f"  First line:   \"{caption_res['visible_first_line']}\"")
    print(f"  Hashtags:     {' '.join(caption_res['hashtags'])}")

    # 6. DIRECT INSTAGRAM UPLOAD
    print("\n[AUTONOMOUS STEP 6/6] Publishing directly to Instagram...")
    uploader = InstagramUploader()
    upload_result = uploader.upload_reel(
        video_path=video_path,
        caption=final_caption,
        force_dry_run=force_dry_run,
    )

    # 7. RECORD IN HISTORY LOG
    log_record = {
        "topic": topic,
        "niche": target_niche,
        "language": target_lang,
        "video_path": str(video_path),
        "audio_path": audio_path,
        "hook": hook["spoken"],
        "caption": final_caption,
        "upload_status": upload_result.get("status", "COMPLETED"),
        "media_id": upload_result.get("media_id"),
        "media_url": upload_result.get("media_url"),
        "method": upload_result.get("method", "DRY_RUN"),
    }
    cm.record_published(log_record)

    print("\n" + "=" * 70)
    print("            AUTONOMOUS REEL CYCLE COMPLETE!")
    print("=" * 70)
    print(f"Topic:        {topic}")
    print(f"Video File:   {video_path}")
    print(f"Publish Mode: {upload_result.get('method', 'DRY_RUN')}")
    if upload_result.get("media_url"):
        print(f"Live Reel:    {upload_result.get('media_url')}")
    print("=" * 70 + "\n")

    return log_record


if __name__ == "__main__":
    print("Testing autonomous cycle in Dry-Run mode...")
    res = run_autonomous_reel_cycle(force_dry_run=True)
    print("Autonomous Cycle Result:", res)
