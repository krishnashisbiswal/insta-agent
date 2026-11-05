import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows UTF-8 safety
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
from app.analytics.self_learning_engine import SelfLearningEngine
from app.analytics.seo_optimizer import generate_seo_metadata, verify_seo_integrity
from app.autonomous.content_manager import ContentManager
from app.autonomous.timing_engine import (
    get_current_time,
    is_in_optimal_window,
    seconds_until_next_optimal,
)
from app.instagram.uploader import InstagramUploader
from app.video.tts_engine import generate_speech
from app.video.video_composer import create_reel_video
from config.settings import (
    CONTENT_LANGUAGE,
    CONTENT_NICHE,
    CONTENT_THEME,
    OUTPUT_DIR,
    TIMEZONE,
)

logger = logging.getLogger("AutopilotEngine")


def run_single_autonomous_publish(
    niche: Optional[str] = None,
    language: Optional[str] = None,
    theme_name: Optional[str] = None,
    force_dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Executes a single completely autonomous end-to-end production & publish cycle.
    No human interaction required.
    """
    target_niche = niche or CONTENT_NICHE
    target_lang = language or CONTENT_LANGUAGE
    target_theme = theme_name or CONTENT_THEME
    tz = TIMEZONE or "Asia/Kolkata"

    curr_dt = get_current_time(tz)
    in_peak, peak_name = is_in_optimal_window(tz)

    print("\n" + "=" * 75)
    print("      ZERO-HUMAN-INTERACTION AUTOPILOT REEL MAKER & PUBLISHER")
    print("=" * 75)
    print(f"Timestamp:        {curr_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz})")
    print(f"Engagement Slot:  {peak_name} ({'PEAK ALGORITHM WINDOW' if in_peak else 'REGULAR WINDOW'})")
    print(f"Target Niche:     {target_niche}")
    print(f"Target Language:  {target_lang}")
    print(f"Visual Theme:     {target_theme}")
    print("=" * 75)

    # 0. AUTONOMOUS DAILY SELF-TRAINING & KNOWLEDGE UPGRADE
    learning_engine = SelfLearningEngine()
    if learning_engine.should_upgrade_today():
        print("\n[AUTOPILOT 0/6] Running daily self-training & meta-learning upgrade...")
        learning_engine.run_daily_self_upgrade()
    else:
        playbook = learning_engine.load_playbook()
        print(f"\n[AUTOPILOT 0/6] Agent Brain Active at Level {playbook.get('evolution_level', 1.0):.1f} (Daily Knowledge Evolved)")

    # 1. AUTONOMOUS CONTENT SELECTION & MEMORY CHECK
    print("\n[AUTOPILOT 1/6] Selecting next viral topic from content queue...")
    cm = ContentManager()
    topic_data = cm.pop_next_topic(niche=target_niche, language=target_lang)
    topic = topic_data.get("topic", "Planetary Secrets")
    target_dur = int(topic_data.get("target_seconds", 25))

    print(f" -> Selected Topic: \"{topic}\"")
    if topic_data.get("angle"):
        print(f"    Angle: {topic_data['angle']}")

    # 2. INSTAGRAM SEO & KEYWORD EXTRACTION
    print("\n[AUTOPILOT 2/6] Extracting Instagram SEO keywords & watch-time loop...")
    seo_meta = generate_seo_metadata(topic=topic, niche=target_niche)
    keywords = seo_meta.get("primary_search_keywords", [])
    loop_phrase = seo_meta.get("loop_closing_phrase", "")
    print(f" -> Search Keywords: {', '.join(keywords[:4])}")
    print(f" -> Replay Loop:     \"{loop_phrase}\"")

    # 3. SCRIPT GENERATION & HOOK SCORING (26 FORMULAS)
    print("\n[AUTOPILOT 3/6] Writing loop-engineered script with Gemini AI...")
    script_data = generate_reel(
        topic=topic,
        niche=target_niche,
        language=target_lang,
        duration=target_dur,
    )
    hook = script_data["selected_hook"]
    print(f" -> Winning Hook: \"{hook['spoken']}\"")
    print(f"    On-Screen:    \"{hook['on_screen']}\"")
    print(f"    Hook Score:   {hook.get('score')}/100 [{hook.get('verdict')}]")

    # 4. STUDIO NEURAL VOICEOVER (TTS)
    print("\n[AUTOPILOT 4/6] Generating studio neural voiceover audio...")
    audio_meta = generate_speech(text=script_data["full_script"])
    audio_path = audio_meta["audio_path"]
    print(f" -> Voice:     {audio_meta['voice']}")
    print(f"    Duration:  {audio_meta['duration']:.2f} seconds")

    # 5. 1080x1920 VERTICAL REEL COMPOSITION
    print("\n[AUTOPILOT 5/6] Composing 1080x1920 MP4 vertical Reel...")
    video_path = create_reel_video(
        script_data=script_data,
        audio_path=audio_path,
        theme_name=target_theme,
    )
    print(f" -> MP4 File:  {video_path.name}")

    # 6. SEO-OPTIMIZED CAPTION & DIRECT INSTAGRAM PUBLISH
    print("\n[AUTOPILOT 6/6] Generating feed-cut caption & publishing to Instagram...")
    caption_res = optimize_caption(
        topic=topic,
        script_hook=hook["spoken"],
        draft_caption=script_data["caption"],
        niche=target_niche,
    )
    final_caption = caption_res["full_caption"]
    hashtags = caption_res["hashtags"]

    # Verify SEO compliance
    seo_audit = verify_seo_integrity(script_data, final_caption, hashtags)
    print(f" -> SEO Audit Score: {seo_audit['overall_seo_score']}/100 [{seo_audit['verdict']}]")
    print(f"    Visible Hook:    \"{caption_res['visible_first_line']}\"")
    print(f"    Tags:            {' '.join(hashtags)}")

    # Execute Direct Publish or Safe Dry-Run
    uploader = InstagramUploader()
    upload_result = uploader.upload_reel(
        video_path=video_path,
        caption=final_caption,
        force_dry_run=force_dry_run,
    )

    # 7. RECORD TO PUBLISHED HISTORY LOG
    log_record = {
        "timestamp": int(time.time()),
        "time_str": curr_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "slot": peak_name,
        "topic": topic,
        "niche": target_niche,
        "language": target_lang,
        "video_path": str(video_path),
        "audio_path": audio_path,
        "hook": hook["spoken"],
        "caption": final_caption,
        "seo_score": seo_audit["overall_seo_score"],
        "upload_method": upload_result.get("method", "DRY_RUN"),
        "upload_status": upload_result.get("status", "COMPLETED"),
        "media_id": upload_result.get("media_id"),
        "media_url": upload_result.get("media_url"),
    }
    cm.record_published(log_record)

    print("\n" + "=" * 75)
    print("                 AUTONOMOUS CYCLE COMPLETED!")
    print("=" * 75)
    print(f"Video File:     {video_path}")
    print(f"Publish Method: {upload_result.get('method', 'DRY_RUN')}")
    if upload_result.get("media_url"):
        print(f"Live Reel URL:  {upload_result.get('media_url')}")
    print("=" * 75 + "\n")

    return log_record


def start_autopilot_daemon(
    niche: Optional[str] = None,
    language: Optional[str] = None,
    theme: Optional[str] = None,
    follow_peak_schedule: bool = True,
    dry_run: bool = False,
):
    """
    Starts the continuous autonomous daemon.
    Follows Instagram's highest engagement windows automatically.
    """
    tz = TIMEZONE or "Asia/Kolkata"
    print("\n" + "=" * 75)
    print("         AUTOPILOT DAEMON: 100% HANDS-FREE INSTAGRAM GROWTH")
    print("=" * 75)
    print(f"Timezone:             {tz}")
    print(f"Peak Timing Sync:     {'ENABLED (Posts only during peak slots)' if follow_peak_schedule else 'HOURLY INTERVAL'}")
    print(f"Publishing Mode:      {'DRY-RUN (Local Video + Manifest)' if dry_run else 'LIVE AUTOMATIC PUBLISHING'}")
    print("=" * 75 + "\n")

    cycle = 0

    while True:
        cycle += 1
        curr_dt = get_current_time(tz)

        if follow_peak_schedule:
            in_peak, slot_name = is_in_optimal_window(tz)
            if not in_peak:
                secs_wait, next_slot, next_dt = seconds_until_next_optimal(tz)
                print(f"[AUTOPILOT] Currently off-peak. Next engagement slot: {next_slot} at {next_dt.strftime('%H:%M:%S')}")
                print(f"[AUTOPILOT] Sleeping for {secs_wait // 60} minutes ({secs_wait}s)...")
                try:
                    time.sleep(secs_wait)
                except KeyboardInterrupt:
                    print("\n[AUTOPILOT] Daemon stopped by user.")
                    break

        print(f"\n>>> [AUTOPILOT TRIGGER - CYCLE #{cycle}] Starting production...")
        try:
            run_single_autonomous_publish(
                niche=niche,
                language=language,
                theme_name=theme,
                force_dry_run=dry_run,
            )
        except Exception as exc:
            print(f"[AUTOPILOT ERROR] Cycle #{cycle} encountered an issue: {exc}")
            logger.exception("Autopilot cycle error")

        # After posting, sleep at least 15 minutes to prevent re-triggering the same slot immediately
        print("[AUTOPILOT] Cycle finished. Waiting 15 minutes before checking next schedule...")
        try:
            time.sleep(900)
        except KeyboardInterrupt:
            print("\n[AUTOPILOT] Daemon stopped by user.")
            break


def main():
    parser = argparse.ArgumentParser(description="Autopilot Zero-Human-Interaction Reel Maker")
    parser.add_argument("--now", action="store_true", help="Run one autonomous cycle immediately and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background following peak post times")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run validation")
    parser.add_argument("--niche", type=str, default=CONTENT_NICHE, help="Target niche")
    parser.add_argument("--lang", type=str, default=CONTENT_LANGUAGE, help="Target language")
    parser.add_argument("--theme", type=str, default=CONTENT_THEME, help="Visual theme")

    args = parser.parse_args()

    if args.daemon:
        start_autopilot_daemon(
            niche=args.niche,
            language=args.lang,
            theme=args.theme,
            follow_peak_schedule=True,
            dry_run=args.dry_run,
        )
    else:
        # Default: run one immediate autonomous production cycle
        run_single_autonomous_publish(
            niche=args.niche,
            language=args.lang,
            theme_name=args.theme,
            force_dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
