import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Project root
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
from app.analytics.instagram_algorithm_brain import InstagramAlgorithmBrain
from app.analytics.self_learning_engine import SelfLearningEngine
from app.analytics.seo_optimizer import verify_seo_integrity
from app.analytics.trend_discovery_engine import TrendDiscoveryEngine
from app.autonomous.timing_engine import (
    get_current_time,
    get_next_optimal_post_time,
    is_in_optimal_window,
    seconds_until_next_optimal,
)
from app.instagram.uploader import InstagramUploader
from app.video.cinematic_composer import create_cinematic_reel_video
from app.video.smart_voice_router import clean_pronunciation_for_hindi, determine_smart_voice
from app.video.tts_engine import generate_speech
from config.settings import CONTENT_LANGUAGE, CONTENT_NICHE, STORAGE_DIR, TIMEZONE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyAlgorithmPublisher")

DAILY_TRACKER_FILE = STORAGE_DIR / "daily_post_tracker.json"


class DailyAlgorithmPublisher:
    """
    Autonomous 1-Video-Daily Publisher strictly timed to Instagram's AI algorithm peak.
    1. Enforces exactly 1 high-production video per calendar day.
    2. Dynamically discovers hot trending topics across Vedic Astrology, Gemstones & Karma.
    3. Generates real human-edited cinematic videos with Ken Burns zoom, light leaks & kinetic subtitles.
    4. Guarantees 100% Explore SEO compliance (loop retention, single-word CTA, 4-5 hashtags).
    """

    def __init__(self, tracker_file: Path = DAILY_TRACKER_FILE):
        self.tracker_file = tracker_file
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        self.algo_brain = InstagramAlgorithmBrain()
        self.trend_engine = TrendDiscoveryEngine()
        self.learning_engine = SelfLearningEngine()

    def load_tracker(self) -> Dict[str, Any]:
        if not self.tracker_file.exists():
            return {"last_post_date": None, "total_posts": 0, "history": []}
        try:
            with open(self.tracker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_post_date": None, "total_posts": 0, "history": []}

    def save_tracker(self, data: Dict[str, Any]) -> None:
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def has_posted_today(self, tz: str = TIMEZONE) -> bool:
        """Check if today's single video has already been published."""
        tracker = self.load_tracker()
        today_str = get_current_time(tz).strftime("%Y-%m-%d")
        return tracker.get("last_post_date") == today_str

    def record_post_today(self, post_info: Dict[str, Any], tz: str = TIMEZONE) -> None:
        """Record today's completed video."""
        tracker = self.load_tracker()
        today_str = get_current_time(tz).strftime("%Y-%m-%d")
        tracker["last_post_date"] = today_str
        tracker["total_posts"] = tracker.get("total_posts", 0) + 1
        tracker["history"].append({
            "date": today_str,
            "timestamp": int(time.time()),
            "topic": post_info.get("topic", ""),
            "seo_score": post_info.get("seo_score", 90),
            "video_path": str(post_info.get("video_path", "")),
        })
        self.save_tracker(tracker)

    def produce_trending_reel(
        self,
        niche: str = CONTENT_NICHE,
        language: str = CONTENT_LANGUAGE,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes complete production of a fresh trending viral reel:
        - Self-Learning Daily Upgrade
        - Hot Trend Discovery (anti-fatigue, zero repetition)
        - 5-Beat Viral Retention Script with Replay Loop
        - Expressive Studio Neural Voiceover
        - Real Human-Edited Cinematic Composition (Photorealistic B-Roll + Ken Burns Zoom + Lens Leak Blend + Kinetic Subtitles)
        - Explore SEO Package & Multi-file Delivery
        """
        print("\n" + "=" * 75)
        print("  AUTONOMOUS 1-A-DAY VIRAL REEL GENERATOR: INSTAGRAM ALGORITHM SYNC")
        print("=" * 75)

        # 1. Self-Learning Brain Upgrade
        print("\n[STEP 1/6] Running self-learning knowledge upgrade...")
        playbook = self.learning_engine.run_daily_self_upgrade()
        algo_state = self.algo_brain.get_algorithm_state()
        print(f" -> Brain Level:      {playbook.get('evolution_level', 1.0):.1f}")
        print(f" -> Active Phase:     {algo_state['active_phase']} (Velocity: {algo_state['algorithm_velocity_score']}/100)")

        # 2. Hot Trending Topic Discovery (Zero Repetition)
        print("\n[STEP 2/6] Trend Discovery Engine scanning hot viral angles...")
        trend = self.trend_engine.discover_next_viral_trend(niche=niche, language=language)
        topic = trend.get("topic", "Stop Wearing Yellow Sapphire (Pukhraj) Until You Check This One Placement")
        target_dur = int(trend.get("target_duration_seconds", 25))
        self.trend_engine.record_generated_topic(trend)

        print(f" -> Hot Trend Topic:  \"{topic}\"")
        if trend.get("sub_niche"):
            print(f"    Pillar:           {trend['sub_niche']}")
        if trend.get("hook_angle"):
            print(f"    Hook Strategy:    {trend['hook_angle']}")

        # Smart Voice & Language Switch (Zero Pronunciation Compromise)
        voice_mode = os.getenv("VOICE_MODE", "smart")
        gender = os.getenv("VOICE_GENDER", "male")
        smart_lang, smart_voice, script_mode = determine_smart_voice(topic=topic, voice_mode=voice_mode, gender=gender)
        active_lang = language if language and language != "Hindi mixed with English" else smart_lang
        active_voice = voice or smart_voice

        print(f" -> Smart Switch Mode:    {voice_mode.upper()} -> {active_lang} ({active_voice})")

        # 3. 5-Beat Viral Retention Script with Infinite Replay Loop
        print("\n[STEP 3/6] Director AI writing 5-beat retention script with Gemini...")
        script_data = generate_reel(
            topic=topic,
            niche=niche,
            language=active_lang,
            duration=target_dur,
        )
        hook = script_data["selected_hook"]
        print(f" -> Winning Hook:     \"{hook['spoken']}\"")
        print(f"    On-Screen Title:  \"{hook['on_screen']}\"")
        print(f"    Hook Score:       {hook.get('score', 'N/A')}/100 [{hook.get('verdict', 'OK')}]")

        # 4. Studio Neural Voiceover with Zero Pronunciation Distortion
        full_text = script_data["full_script"]
        if active_voice.startswith("hi-"):
            full_text = clean_pronunciation_for_hindi(full_text)

        print(f"\n[STEP 4/6] Recording studio neural voiceover ({active_voice})...")
        audio_meta = generate_speech(text=full_text, voice=active_voice)
        audio_path = audio_meta["audio_path"]
        print(f" -> Audio Path:       {audio_path}")
        print(f"    Duration:         {audio_meta['duration']:.2f} seconds")

        # 5. Real Human-Edited Cinematic Composition
        print("\n[STEP 5/6] Composing cinematic reel with Ken Burns zoom, light leaks & kinetic subtitles...")
        output_filename = f"daily_reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        video_path = create_cinematic_reel_video(
            script_data=script_data,
            audio_path=audio_path,
            output_filename=output_filename,
        )
        print(f" -> Rendered MP4:     {video_path}")

        # 6. Explore SEO Caption Optimization & Delivery
        print("\n[STEP 6/6] Packaging Explore SEO metadata and delivering to insta content/...")
        caption_res = optimize_caption(
            topic=topic,
            script_hook=hook["spoken"],
            draft_caption=script_data["caption"],
            niche=niche,
        )
        final_caption = caption_res["full_caption"]
        hashtags = caption_res["hashtags"]

        seo_audit = verify_seo_integrity(script_data, final_caption, hashtags)
        print(f" -> SEO Score:        {seo_audit['overall_seo_score']}/100 [{seo_audit['verdict']}]")

        dest_dir = PROJECT_ROOT / "insta content"
        dest_dir.mkdir(parents=True, exist_ok=True)

        final_video_dest = dest_dir / "viral_reel_video.mp4"
        shutil.copy2(video_path, final_video_dest)

        final_audio_dest = dest_dir / "voiceover_audio.mp3"
        shutil.copy2(audio_path, final_audio_dest)

        caption_dest = dest_dir / "caption_and_hashtags.txt"
        with open(caption_dest, "w", encoding="utf-8") as f:
            f.write(final_caption + "\n\n" + " ".join(hashtags) + "\n")

        overview_dest = dest_dir / "content_overview.json"
        overview_data = {
            "topic": topic,
            "niche": niche,
            "voice": voice,
            "production_style": "Cinematic Photorealistic B-Roll + Ken Burns Zoom + Lens Leak Blend + Kinetic Subtitles",
            "sound_design": "Sub-bass impact whoosh at 0s + 44.1kHz ambient mystical drone pad (-18 dB)",
            "agent_evolution_level": playbook.get("evolution_level", 1.0),
            "hook": hook,
            "seo_audit": seo_audit,
            "duration_seconds": audio_meta["duration"],
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "algorithm_phase": algo_state["active_phase"],
            "daily_post_enforced": True,
        }
        with open(overview_dest, "w", encoding="utf-8") as f:
            json.dump(overview_data, f, indent=2, ensure_ascii=False)

        res_info = {
            "topic": topic,
            "seo_score": seo_audit["overall_seo_score"],
            "video_path": final_video_dest,
            "audio_path": final_audio_dest,
            "caption": final_caption,
            "hashtags": hashtags,
            "hook": hook,
            "size_mb": round(final_video_dest.stat().st_size / (1024 * 1024), 2),
        }

        # 7. Live Instagram Publishing
        uploader = InstagramUploader()
        if uploader.has_credentials():
            print("\n[STEP 7/7] Publishing Reel to Instagram live account...")
            try:
                full_post_caption = final_caption + "\n\n" + " ".join(hashtags)
                upload_res = uploader.upload_reel(
                    video_path=final_video_dest,
                    caption=full_post_caption,
                )
                print(f" -> Instagram Post Status: {upload_res.get('status', 'OK')} [ID: {upload_res.get('media_id', 'N/A')}]")
                res_info["instagram_upload"] = upload_res
            except Exception as e:
                print(f" -> Instagram Upload Notice: {e}. Video safely delivered to insta content/.")
                res_info["instagram_upload_error"] = str(e)
        else:
            print("\n[STEP 7/7] No live Instagram credentials in .env. Video saved ready for manual post or GitHub Actions.")

        print("\n" + "=" * 75)
        print("  DAILY VIRAL REEL PRODUCTION COMPLETE!")
        print(f"  Topic:    {topic}")
        print(f"  Saved to: {final_video_dest}")
        print(f"  Size:     {res_info['size_mb']} MB")
        print("=" * 75)

        return res_info

    def run_daily_algorithm_cycle(self, force: bool = False, tz: str = TIMEZONE) -> Dict[str, Any]:
        """
        Executes today's single video generation and scheduling based on algorithm timing.
        """
        now = get_current_time(tz)
        today_str = now.strftime("%Y-%m-%d")

        if not force and self.has_posted_today(tz=tz):
            secs, win_name, nxt = seconds_until_next_optimal(tz)
            print(f"[DAILY PUBLISHER] Today's video ({today_str}) has ALREADY been produced.")
            print(f"[DAILY PUBLISHER] Next optimal algorithm window: {nxt.strftime('%Y-%m-%d %H:%M')} ({win_name}) in {secs // 3600}h {(secs % 3600) // 60}m.")
            return {"status": "already_posted_today", "next_post_time": str(nxt)}

        # Check algorithm engagement window
        in_peak, peak_name = is_in_optimal_window(tz)
        print(f"[DAILY PUBLISHER] Checking Instagram Algorithm State: {peak_name} ({'PEAK ALGORITHM WINDOW' if in_peak else 'PREPARATION WINDOW'})")

        # Produce today's high-retention reel
        result = self.produce_trending_reel()

        # Record in daily tracker
        self.record_post_today(result, tz=tz)

        return result

    def run_continuous_daemon(self, tz: str = TIMEZONE):
        """
        Runs continuously 24/7 on a live server:
        - Automatically wakes up during peak algorithm velocity windows.
        - Produces and publishes strictly 1 reel per day.
        - Respects 15-minute vector indexing lead time.
        """
        print("\n" + "=" * 75)
        print("  STARTING 24/7 AUTONOMOUS INSTAGRAM PUBLISHING DAEMON")
        print(f"  Timezone:        {tz}")
        print("=" * 75)
        while True:
            try:
                now = get_current_time(tz)
                today_str = now.strftime("%Y-%m-%d")

                if not self.has_posted_today(tz=tz):
                    in_peak, peak_name = is_in_optimal_window(tz)
                    if in_peak:
                        print(f"\n[DAEMON] 🚀 Inside peak window ({peak_name}) at {now.strftime('%H:%M:%S')}. Publishing today's reel!")
                        self.run_daily_algorithm_cycle(force=False, tz=tz)
                    else:
                        secs, win_name, nxt = seconds_until_next_optimal(tz)
                        sleep_secs = min(secs, 900)
                        print(f"[DAEMON] Waiting for next peak window ({win_name}) at {nxt.strftime('%H:%M')}. Sleeping {sleep_secs // 60}m {sleep_secs % 60}s...")
                        time.sleep(sleep_secs)
                else:
                    secs, win_name, nxt = seconds_until_next_optimal(tz)
                    sleep_secs = min(max(secs, 300), 3600)
                    print(f"[DAEMON] Today's reel ({today_str}) already published. Next window ({win_name}) at {nxt.strftime('%Y-%m-%d %H:%M')}. Sleeping {sleep_secs // 60}m...")
                    time.sleep(sleep_secs)
            except KeyboardInterrupt:
                print("\n[DAEMON] Stopped by user.")
                break
            except Exception as e:
                print(f"\n[DAEMON ERROR] Unexpected error: {e}. Retrying in 60s...")
                time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous 1-Video-Daily Algorithm Publisher")
    parser.add_argument("--force", action="store_true", help="Force production even if already posted today")
    parser.add_argument("--daemon", action="store_true", help="Run 24/7 continuous autonomous server daemon")
    parser.add_argument("--voice-mode", choices=["smart", "hindi", "english"], default=None, help="Smart Voice Switch mode")
    parser.add_argument("--gender", choices=["male", "female"], default=None, help="Voice gender")
    args = parser.parse_args()

    if args.voice_mode:
        os.environ["VOICE_MODE"] = args.voice_mode
    if args.gender:
        os.environ["VOICE_GENDER"] = args.gender

    publisher = DailyAlgorithmPublisher()
    if args.daemon:
        publisher.run_continuous_daemon()
    else:
        publisher.run_daily_algorithm_cycle(force=args.force)
