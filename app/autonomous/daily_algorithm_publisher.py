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
from app.agents.comment_agent import CommentAgent
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
        from app.analytics.reinforcement_engine import ReinforcementEvolutionEngine
        self.reinforcement_engine = ReinforcementEvolutionEngine()

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
        """
        Check if today's single video has already been published.
        Dual-layer verification:
        1. Live Instagram profile feed inspection (ground truth: checks if Reel actually exists on Instagram)
        2. Local post tracker JSON fallback
        """
        today_str = get_current_time(tz).strftime("%Y-%m-%d")

        # 1. Live Instagram account check (ground truth)
        try:
            uploader = InstagramUploader()
            if uploader.has_direct_credentials():
                cl = uploader._init_direct_client()
                clips = cl.user_clips(cl.user_id, amount=1)
                if clips:
                    from app.autonomous.timing_engine import get_tz
                    tz_obj = get_tz(tz)
                    latest = clips[0]
                    latest_dt = latest.taken_at.astimezone(tz_obj)
                    if latest_dt.strftime("%Y-%m-%d") == today_str:
                        logger.info(f"Verified live Reel posted on Instagram today: {latest.code} at {latest_dt.strftime('%H:%M:%S IST')}")
                        tracker = self.load_tracker()
                        tracker["last_post_date"] = today_str
                        tracker["last_media_code"] = latest.code
                        self.save_tracker(tracker)
                        return True
                    else:
                        logger.info(f"Live Instagram profile check: No reel posted today ({today_str}). Latest post was {latest.code} on {latest_dt.strftime('%Y-%m-%d')}.")
                        return False
        except Exception as exc:
            logger.debug(f"Live Instagram profile verification skipped/failed: {exc}")

        # 2. Local tracker fallback
        tracker = self.load_tracker()
        return tracker.get("last_post_date") == today_str

    def record_post_today(self, post_info: Dict[str, Any], tz: str = TIMEZONE) -> None:
        """Record today's completed video ONLY if actually published to Instagram."""
        ig_res = post_info.get("instagram_upload", {})
        media_id = ig_res.get("media_id")
        media_code = ig_res.get("media_code", "")
        media_url = ig_res.get("media_url", "")

        # Never record a false positive if upload failed or was dry run
        if not media_id or ig_res.get("mode") == "DRY_RUN":
            logger.warning("[DAILY PUBLISHER] Skipping tracker update: Reel was not verified published on Instagram.")
            return

        tracker = self.load_tracker()
        today_str = get_current_time(tz).strftime("%Y-%m-%d")
        tracker["last_post_date"] = today_str
        tracker["total_posts"] = tracker.get("total_posts", 0) + 1
        tracker["history"].append({
            "date": today_str,
            "timestamp": int(time.time()),
            "topic": post_info.get("topic", ""),
            "seo_score": post_info.get("seo_score", 90),
            "media_id": media_id,
            "media_code": media_code,
            "media_url": media_url,
            "video_path": str(post_info.get("video_path", "")),
        })
        tracker[today_str] = {
            "published_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "media_id": media_id,
            "media_code": media_code,
            "media_url": media_url,
            "topic": post_info.get("topic", ""),
        }
        self.save_tracker(tracker)

    def produce_trending_reel(
        self,
        niche: str = CONTENT_NICHE,
        language: str = CONTENT_LANGUAGE,
        voice: Optional[str] = None,
        dry_run: bool = False,
        topic_override: Optional[str] = None,
        category: Optional[str] = None,
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

        # 1. Autonomous Reinforcement Learning & Self-Evolution Upgrade
        print("\n[STEP 1/6] Running autonomous reinforcement learning & policy upgrade...")
        rl_state = self.reinforcement_engine.run_daily_autonomous_training_cycle()
        algo_state = self.algo_brain.get_algorithm_state()
        print(f" -> Brain Level:      {rl_state.get('evolution_level', 2.0):.1f}")
        print(f" -> Active Policy:    {rl_state.get('policy', {}).get('trait_frameworks', [{}])[0].get('name', 'Relatable Traits Mirror')}")
        print(f" -> Active Phase:     {algo_state['active_phase']} (Velocity: {algo_state['algorithm_velocity_score']}/100)")

        # 2. Hot Trending Topic Discovery (Zero Repetition)
        print("\n[STEP 2/6] Trend Discovery Engine scanning hot viral angles...")
        if topic_override:
            topic = topic_override
            trend = {
                "topic": topic,
                "target_duration_seconds": 28,
                "sub_niche": "Vedic Astrology Insights & Karmic Traps",
                "hook_angle": "Viral Vedic insight on placements and karmic patterns",
            }
            target_dur = 28
            self.trend_engine.record_generated_topic(trend)
        else:
            trend = self.trend_engine.discover_next_viral_trend(niche=niche, language=language, category=category)
            topic = trend.get("topic", "Stop Wearing Yellow Sapphire (Pukhraj) Until You Check This One Placement")
            target_dur = int(trend.get("target_duration_seconds", 25))
            self.trend_engine.record_generated_topic(trend)

        print(f" -> Hot Trend Topic:  \"{topic}\"")
        if trend.get("sub_niche"):
            print(f"    Pillar:           {trend['sub_niche']}")
        if trend.get("hook_angle"):
            print(f"    Hook Strategy:    {trend['hook_angle']}")

        # Smart Voice & Language Switch (Zero Pronunciation Compromise)
        voice_mode = os.getenv("VOICE_MODE", "smart").lower().strip()
        voice_engine = os.getenv("VOICE_ENGINE", "sarvam").lower().strip()
        sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()
        sarvam_speaker = os.getenv("SARVAM_SPEAKER", "arjun").strip()
        gender = os.getenv("VOICE_GENDER", "male").lower().strip()
        smart_lang, smart_voice, script_mode = determine_smart_voice(topic=topic, voice_mode=voice_mode, gender=gender)

        if voice_engine in ["sarvam", "sarvam_ai"] and sarvam_key:
            active_lang = "Hindi" if voice_mode in ["hindi", "hi", "smart"] else "English"
            active_voice = voice or f"sarvam:{sarvam_speaker}"
        elif voice_mode in ["hindi", "hi"]:
            active_lang = "Hindi"
            active_voice = "hi-IN-MadhurNeural" if gender == "male" else "hi-IN-SwaraNeural"
        elif voice_mode in ["english", "en"]:
            active_lang = "English"
            active_voice = "en-IN-PrabhatNeural" if gender == "male" else "en-IN-NeerjaNeural"
        else:
            active_lang = smart_lang
            active_voice = voice or smart_voice

        print(f" -> Voice Engine / Voice: {voice_engine.upper()} -> {active_lang} ({active_voice})")

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

        # 4 & 5. Studio Neural Voiceover & Frame-Synchronized Cinematic Composition
        print(f"\n[STEP 4 & 5/6] Composing cinematic reel with frame-synchronized audio & video ({active_voice})...")
        output_filename = f"daily_reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        video_path = create_cinematic_reel_video(
            script_data=script_data,
            voice=active_voice,
            output_filename=output_filename,
        )
        print(f" -> Rendered MP4:     {video_path}")

        # Clean intermediate audio and frame generation chunks to save disk space
        try:
            from app.utils.storage_cleaner import StorageCleaner
            StorageCleaner.clean_intermediate_generation_data()
        except Exception as e:
            logger.debug(f"Intermediate cleanup notice: {e}")

        # 6. Explore SEO Caption Optimization & Delivery
        print("\n[STEP 6/6] Packaging Explore SEO metadata and delivering to insta content/...")
        caption_res = optimize_caption(
            topic=topic,
            script_hook=hook["spoken"],
            draft_caption=script_data.get("caption", ""),
            niche=niche,
            script_data=script_data,
            language=active_lang,
        )
        final_caption = caption_res["full_caption"]
        hashtags = caption_res["hashtags"]

        seo_audit = caption_res.get("seo_audit") or verify_seo_integrity(script_data, final_caption, hashtags)
        print(f" -> SEO Score:        {seo_audit['overall_seo_score']}/100 [{seo_audit['verdict']}]")

        dest_dir = PROJECT_ROOT / "insta content"
        dest_dir.mkdir(parents=True, exist_ok=True)

        final_video_dest = dest_dir / "viral_reel_video.mp4"
        shutil.copy2(video_path, final_video_dest)

        final_audio_dest = dest_dir / "voiceover_audio.mp3"

        caption_dest = dest_dir / "caption_and_hashtags.txt"
        tags_str = " ".join(hashtags)
        if any(t in final_caption for t in hashtags):
            caption_text_to_save = final_caption
        else:
            caption_text_to_save = f"{final_caption}\n\n{tags_str}"

        with open(caption_dest, "w", encoding="utf-8") as f:
            f.write(caption_text_to_save.strip() + "\n")

        from moviepy import VideoFileClip
        with VideoFileClip(str(final_video_dest)) as v_chk:
            final_duration = round(v_chk.duration, 2)

        playbook = self.learning_engine.load_playbook() if hasattr(self, "learning_engine") else {}
        overview_dest = dest_dir / "content_overview.json"
        overview_data = {
            "topic": topic,
            "niche": niche,
            "voice": active_voice,
            "production_style": "Cinematic Photorealistic B-Roll + Ken Burns Zoom + Lens Leak Blend + Kinetic Subtitles",
            "sound_design": "Sub-bass impact whoosh at 0s + 44.1kHz ambient mystical drone pad (-18 dB)",
            "agent_evolution_level": playbook.get("evolution_level", 1.0) if isinstance(playbook, dict) else 1.0,
            "hook": hook,
            "seo_audit": seo_audit,
            "duration_seconds": final_duration,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "algorithm_phase": algo_state.get("active_phase", "EXPLORE") if isinstance(algo_state, dict) else "EXPLORE",
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
        if dry_run:
            print("\n[STEP 7/7] Dry run mode enabled. Video safely packaged into insta content/ ready for review.")
            res_info["instagram_upload"] = {"status": "dry_run", "message": "Video generated ready for review in insta content/"}
        else:
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

                    # Auto-purge video and intermediate broll from disk to clear space once published
                    if upload_res.get("status") == "PUBLISHED" or upload_res.get("media_id"):
                        print(f"\n[INSTAGRAM SUCCESS] Reel published successfully! Link: {upload_res.get('media_url')}")
                        print("\n[STORAGE AUTO-PURGE] Purging intermediate files to clear space...")
                        try:
                            from app.utils.storage_cleaner import StorageCleaner
                            clean_stats = StorageCleaner.clean_post_publishing_data(keep_latest_reel=True)
                            print(f" -> 🧹 Space Cleared: Reclaimed {clean_stats['freed_mb']} MB across {clean_stats['files_removed']} files.")
                        except Exception as ce:
                            logger.warning(f"Storage purge notice: {ce}")
                    else:
                        print(f"\n[INSTAGRAM NOTICE] Live upload did not return confirmed media_id: {upload_res}")
                        if os.getenv("CI"):
                            raise RuntimeError(f"Instagram upload did not succeed in CI: {upload_res}")
                except Exception as e:
                    print(f" -> ❌ Instagram Upload Error: {e}. Video safely delivered to insta content/.")
                    res_info["instagram_upload_error"] = str(e)
                    if os.getenv("CI"):
                        raise
            else:
                print("\n[STEP 7/7] ⚠️ No live Instagram credentials in .env / Secrets. Video saved ready for manual post or GitHub Actions.")
                if os.getenv("CI"):
                    raise RuntimeError("Missing live Instagram credentials in CI runner.")

        # 8. Autonomous Community Retention & AI Comment Consultation
        print("\n[STEP 8/8] Running AI Comment Consultation & Community Retention Agent...")
        try:
            comment_agent = CommentAgent()
            media_id = res_info.get("instagram_upload", {}).get("media_id")
            uploader_inst = uploader if 'uploader' in locals() else InstagramUploader()
            consultation_replies = comment_agent.process_reel_comments(
                uploader=uploader_inst,
                media_id=media_id,
                topic=topic,
                dry_run=dry_run,
            )
            res_info["comment_consultations"] = len(consultation_replies)
            overview_data["comment_consultations_handled"] = len(consultation_replies)
            with open(overview_dest, "w", encoding="utf-8") as f:
                json.dump(overview_data, f, indent=2, ensure_ascii=False)
            print(f" -> Comment Retention Agent handled {len(consultation_replies)} astrological consultations.")
        except Exception as e:
            logger.warning(f"Comment retention notice: {e}")

        # 9. Real-Time Algorithm Feedback Ingestion & Q-Value Evolution
        print("\n[STEP 9/9] Syncing live Instagram algorithm feedback & evolving Q-learning brain...")
        try:
            fb = self.reinforcement_engine.sync_live_insights_and_reward_brain(
                seo_score=seo_audit["overall_seo_score"],
            )
            print(f" -> Evolved Brain Level: {fb['evolution_level']} (Q-Reward: {fb['reward_score']})")
            overview_data["agent_evolution_level"] = fb["evolution_level"]
            overview_data["q_reward_score"] = fb["reward_score"]
            with open(overview_dest, "w", encoding="utf-8") as f:
                json.dump(overview_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Reinforcement feedback notice: {e}")

        print("\n" + "=" * 75)
        print("  DAILY VIRAL REEL PRODUCTION COMPLETE!")
        print(f"  Topic:    {topic}")
        print(f"  Saved to: {final_video_dest}")
        print(f"  Size:     {res_info['size_mb']} MB")
        print("=" * 75)

        return res_info

    def run_daily_algorithm_cycle(
        self,
        force: bool = False,
        tz: str = TIMEZONE,
        dry_run: bool = False,
        topic: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes today's single video generation and scheduling based on algorithm timing.
        """
        now = get_current_time(tz)
        today_str = now.strftime("%Y-%m-%d")

        if not force and not dry_run and self.has_posted_today(tz=tz):
            secs, win_name, nxt = seconds_until_next_optimal(tz)
            print(f"[DAILY PUBLISHER] Today's video ({today_str}) has ALREADY been published to Instagram.")
            print(f"[DAILY PUBLISHER] Next optimal algorithm window: {nxt.strftime('%Y-%m-%d %H:%M')} ({win_name}) in {secs // 3600}h {(secs % 3600) // 60}m.")
            return {"status": "already_posted_today", "next_post_time": str(nxt)}

        # Check algorithm engagement window and velocity score
        in_peak, peak_name = is_in_optimal_window(tz)
        algo_state = self.algo_brain.get_algorithm_state(tz)
        velocity_score = algo_state.get("algorithm_velocity_score", 50.0)
        active_phase = algo_state.get("active_phase", "General")

        print(f"[DAILY PUBLISHER] Instagram Algorithm Status: {peak_name} (Velocity: {velocity_score}/100, Phase: {active_phase})")

        # Off-peak protection: If scheduled run triggers off-peak and velocity is low, defer to next peak window
        if not force and not dry_run and not in_peak and velocity_score < 75.0:
            secs, win_name, nxt = seconds_until_next_optimal(tz)
            print(f"[DAILY PUBLISHER] ⚠️ Current time is in off-peak indexing window ({active_phase}).")
            print(f"[DAILY PUBLISHER] ⏰ Next high-velocity window: {win_name} at {nxt.strftime('%Y-%m-%d %H:%M %Z')} (in {secs // 3600}h {(secs % 3600) // 60}m).")
            print(f"[DAILY PUBLISHER] Pass --force to override algorithm gating or trigger during scheduled peak.")
            return {
                "status": "off_peak_deferred",
                "current_velocity_score": velocity_score,
                "next_optimal_time": str(nxt),
                "next_window_name": win_name,
            }

        # Produce today's high-retention reel
        result = self.produce_trending_reel(
            dry_run=dry_run,
            topic_override=topic,
            category=category,
        )

        # Record in daily tracker only if live published with confirmed media_id
        if not dry_run and result.get("instagram_upload", {}).get("media_id"):
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
    parser.add_argument("--dry-run", action="store_true", help="Generate and deliver full video package to insta content/ without uploading to Instagram")
    parser.add_argument("--daemon", action="store_true", help="Run 24/7 continuous autonomous server daemon")
    parser.add_argument("--voice-mode", choices=["smart", "hindi", "english"], default=None, help="Smart Voice Switch mode")
    parser.add_argument("--gender", choices=["male", "female"], default=None, help="Voice gender")
    parser.add_argument("--topic", type=str, default=None, help="Specific topic override")
    parser.add_argument("--category", type=str, default=None, help="Specific category override")
    parser.add_argument("--clean-space", action="store_true", help="Clean up intermediate audio chunks, temporary frame renders, and cached files to clear disk space")
    args = parser.parse_args()

    if args.clean_space:
        from app.utils.storage_cleaner import StorageCleaner
        res = StorageCleaner.clean_intermediate_generation_data()
        print(f"\n[STORAGE CLEANER] Successfully cleaned {res['files_removed']} intermediate files, freed {res['freed_mb']} MB.")
        sys.exit(0)

    if args.voice_mode:
        os.environ["VOICE_MODE"] = args.voice_mode
    if args.gender:
        os.environ["VOICE_GENDER"] = args.gender

    publisher = DailyAlgorithmPublisher()
    if args.daemon:
        publisher.run_continuous_daemon()
    else:
        publisher.run_daily_algorithm_cycle(
            force=args.force,
            dry_run=args.dry_run,
            topic=args.topic,
            category=args.category,
        )
