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
from app.video.cinematic_composer import create_cinematic_reel_video
from app.analytics.reinforcement_engine import ReinforcementEvolutionEngine
import shutil
import base64
import imageio_ffmpeg
import subprocess
from moviepy import VideoFileClip
from PIL import Image
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
    Execute a completely autonomous, hands-free Reel cycle from the roots:
    1. Select or brainstorm fresh, diverse viral topic (Zero repetition)
    2. Write, humanize & score 4-Traits script with Gemini
    3. Generate frame-synchronized neural voiceover & sub-bass Vedic sound design
    4. Render 1080x1920 vertical video with dedicated matching photography
    5. Optimize caption, hashtags & CTA (Comment placement + DM consultation)
    6. Sync deliverables to 'insta content/' directory and update interactive player
    7. Upload directly to Instagram if configured, or save for 1-click publishing
    8. Record in diversity history so topic is NEVER repeated
    """
    target_niche = niche or CONTENT_NICHE
    target_lang = language or CONTENT_LANGUAGE
    target_theme = theme_name or CONTENT_THEME

    # 0. Autonomous Reinforcement Learning Upgrade
    rl_engine = ReinforcementEvolutionEngine()
    rl_state = rl_engine.run_daily_autonomous_training_cycle()
    evo_level = rl_state.get("evolution_level", 2.5)

    print("\n" + "=" * 70)
    print("       AUTONOMOUS INSTAGRAM REEL AGENT (1-CLICK ENGINE)")
    print("=" * 70)
    print(f"Time:            {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Niche:           {target_niche}")
    print(f"Language:        {target_lang}")
    print(f"Evolution Level: {evo_level:.1f}")
    print("=" * 70)

    # 1. TOPIC SELECTION (Rotates sub-niches, enforces cooldown, zero duplicates)
    cm = ContentManager()
    topic_data = cm.pop_next_topic(niche=target_niche, language=target_lang)
    topic = topic_data.get("topic", "Astrology Secrets")
    target_duration = int(topic_data.get("target_seconds", 30))

    print(f"\n[AUTONOMOUS STEP 1/6] Selected Fresh Topic: \"{topic}\"")
    if topic_data.get("category"):
        print(f"  Category: {topic_data['category']}")

    # 2. SCRIPT GENERATION & HOOK SCORING (3 to 4 Traits Framework)
    print("\n[AUTONOMOUS STEP 2/6] Generating 4-Traits Reel script with Gemini...")
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

    # 3. MASTER CINEMATIC VIDEO RENDERING (Frame-synchronized + Distinct Photography)
    print("\n[AUTONOMOUS STEP 3/6] Rendering cinematic 1080x1920 Reel video...")
    video_path = create_cinematic_reel_video(
        script_data=script_data,
        voice="hi-IN-MadhurNeural",
        output_filename=f"reel_{int(time.time())}.mp4",
    )
    print(f"  Rendered Video: {video_path.name}")

    # 4. CAPTION OPTIMIZATION (Comment Placement + DM to Book Consultation)
    print("\n[AUTONOMOUS STEP 4/6] Generating tailored Instagram caption & hashtags...")
    caption_res = optimize_caption(
        topic=topic,
        script_hook=hook["spoken"],
        draft_caption=script_data.get("caption", ""),
        niche=target_niche,
        script_data=script_data,
        language=target_lang,
    )
    final_caption = caption_res["full_caption"]
    print(f"  First Line:   \"{caption_res['visible_first_line']}\"")
    print(f"  Hashtags:     {' '.join(caption_res['hashtags'])}")

    # 5. SYNC MASTER DELIVERABLES TO 'insta content/'
    print("\n[AUTONOMOUS STEP 5/6] Updating master deliverables in 'insta content/'...")
    insta_dir = PROJECT_ROOT / "insta content"
    insta_dir.mkdir(parents=True, exist_ok=True)

    master_video = insta_dir / "viral_reel_video.mp4"
    shutil.copy(str(video_path), str(master_video))

    with open(insta_dir / "caption_and_hashtags.txt", "w", encoding="utf-8") as f:
        f.write(final_caption)

    # Export preview frames
    clip = VideoFileClip(str(master_video))
    dur = clip.duration
    f1 = clip.get_frame(1.2)
    Image.fromarray(f1).save(insta_dir / "frame_scene1_traits.jpg")
    f2 = clip.get_frame(min(dur * 0.28, dur - 1.0))
    Image.fromarray(f2).save(insta_dir / "frame_scene2_traits.jpg")
    f3 = clip.get_frame(min(dur * 0.52, dur - 1.0))
    Image.fromarray(f3).save(insta_dir / "frame_scene3_traits.jpg")
    f4 = clip.get_frame(min(dur * 0.72, dur - 1.0))
    Image.fromarray(f4).save(insta_dir / "frame_scene4_traits.jpg")
    f5 = clip.get_frame(max(0, dur - 1.8))
    Image.fromarray(f5).save(insta_dir / "frame_scene5_traits.jpg")
    clip.close()

    # Generate GIF preview
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg, "-y",
            "-ss", "0", "-t", "10",
            "-i", str(master_video),
            "-vf", "fps=12,scale=360:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
            str(insta_dir / "sample_preview.gif")
        ]
        subprocess.run(cmd, check=True)
    except Exception as e:
        logger.warning(f"GIF preview generation notice: {e}")

    # Content overview
    overview = {
        "topic": topic,
        "framework": "3 to 4 Traits Identification + Comment Planet Placement + DM to Book Consultation",
        "evolution_level": evo_level,
        "duration_seconds": round(dur, 2),
        "scenes": script_data["scenes"],
        "caption_hook": caption_res["visible_first_line"],
        "hashtags": caption_res["hashtags"],
    }
    with open(insta_dir / "content_overview.json", "w", encoding="utf-8") as f:
        json.dump(overview, f, indent=2, ensure_ascii=False)

    # 6. DIRECT INSTAGRAM UPLOAD / DRY RUN
    print("\n[AUTONOMOUS STEP 6/6] Checking publishing status...")
    uploader = InstagramUploader()
    upload_result = uploader.upload_reel(
        video_path=master_video,
        caption=final_caption,
        force_dry_run=force_dry_run,
    )

    # 7. RECORD IN HISTORY LOG (Enforces strict diversity)
    log_record = {
        "topic": topic,
        "niche": target_niche,
        "language": target_lang,
        "video_path": str(master_video),
        "hook": hook["spoken"],
        "caption": final_caption,
        "duration": round(dur, 2),
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
    print(f"Video File:   {master_video}")
    print(f"Duration:     {dur:.2f}s")
    print(f"Publish Mode: {upload_result.get('method', 'DRY_RUN')}")
    if upload_result.get("media_url"):
        print(f"Live Reel:    {upload_result.get('media_url')}")
    print("=" * 70 + "\n")

    return log_record


if __name__ == "__main__":
    print("Testing autonomous cycle in Dry-Run mode...")
    res = run_autonomous_reel_cycle(force_dry_run=True)
    print("Autonomous Cycle Result:", res)
