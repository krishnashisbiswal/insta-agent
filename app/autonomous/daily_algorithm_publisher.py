from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = PROJECT_ROOT / "insta content"
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
from app.publishing.publishing_errors import (
    DuplicatePublishPreventedError,
    PublishingAuthError,
    PublishingConfigError,
    PublishingError,
    PublishingNetworkError,
    PublishingRateLimitError,
    PublishingUncertainOutcomeError,
    PublishingValidationError,
)
from app.publishing.state_machine import compute_video_fingerprint
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

    @classmethod
    def validate_environment(cls, dry_run: bool = False) -> Dict[str, Any]:
        """
        Startup validation to ensure all dependencies, tools, directories,
        configuration, and credentials are valid before publishing.
        Clearly categorizes findings into:
        - CRITICAL ERROR: Blocks execution.
        - WARNING: Sub-optimal configuration that may affect output quality.
        - OPTIONAL COMPONENT UNAVAILABLE: Gracefully degraded non-critical features.
        """
        critical_errors: List[str] = []
        warnings: List[str] = []
        optional_unavailable: List[str] = []

        # 1. Python version verification (>= 3.11 required)
        if sys.version_info < (3, 11):
            critical_errors.append(
                f"Unsupported Python version: {sys.version_info.major}.{sys.version_info.minor}. "
                f"Insta-Agent requires Python >= 3.11."
            )

        # 2. Core Python package dependencies
        required_packages = [
            ("google.genai", "google-genai"),
            ("moviepy", "moviepy"),
            ("PIL", "Pillow"),
            ("imagehash", "imagehash"),
            ("edge_tts", "edge-tts"),
            ("sqlalchemy", "SQLAlchemy"),
            ("pydantic", "pydantic"),
        ]
        for mod_name, pkg_name in required_packages:
            try:
                __import__(mod_name)
            except ImportError as e:
                critical_errors.append(f"Required package '{pkg_name}' is missing ({e}). Run: pip install -r requirements.txt")

        # 3. Centralized FFmpeg binary resolution & execution validation
        from app.utils.ffmpeg_resolver import get_ffmpeg_binary, is_ffmpeg_available, get_ffmpeg_diagnostics
        ffmpeg_available = is_ffmpeg_available()
        if not ffmpeg_available:
            diag = get_ffmpeg_diagnostics()
            evaluated = [c.get("source") for c in diag.get("candidates_evaluated", [])]
            critical_errors.append(
                f"FFmpeg executable not found or failed execution validation (evaluated sources: {evaluated}). "
                f"Video composition will fail."
            )

        # 4. Storage & Output Directory Writable Permissions
        required_dirs = [
            STORAGE_DIR,
            PROJECT_ROOT / "output" / "reels",
            PROJECT_ROOT / "output" / "audio",
            PROJECT_ROOT / "output" / "frames",
            PROJECT_ROOT / "assets" / "generated_broll",
            CONTENT_DIR,
        ]
        for d in required_dirs:
            try:
                d.mkdir(parents=True, exist_ok=True)
                probe = d / f".perm_probe_{os.getpid()}_{int(time.time()*1000)}"
                probe.write_text("probe")
                probe.unlink()
            except Exception as e:
                critical_errors.append(f"Storage path {d} is not writable: {e}")

        # 5. Database & Storage Initialization
        try:
            from app.models.saas_models import init_db
            init_db()
        except Exception as e:
            critical_errors.append(f"Database initialization failed: {e}")

        # 6. LLM Engine (Gemini)
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not gemini_key:
            optional_unavailable.append("GEMINI_API_KEY is not configured; falling back to offline template generation.")

        # 7. Neural Voice Synthesis (Sarvam AI / Edge TTS)
        sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()
        voice_engine = os.getenv("VOICE_ENGINE", "edge_tts").lower().strip()
        if voice_engine == "sarvam" and not sarvam_key:
            warnings.append("VOICE_ENGINE is 'sarvam' but SARVAM_API_KEY is not set; falling back to Edge-TTS neural voices.")

        # 8. Instagram Credentials (mandatory for live publishing; optional in dry-run)
        if not dry_run:
            from app.instagram.uploader import InstagramUploader
            uploader = InstagramUploader()
            if not uploader.has_credentials():
                critical_errors.append(
                    "Production live publishing requires Instagram credentials. "
                    "Provide INSTAGRAM_USER_ID & INSTAGRAM_ACCESS_TOKEN (Meta Graph API, recommended) or "
                    "INSTAGRAM_SESSION_DATA, INSTAGRAM_SESSION_ID, or INSTAGRAM_USERNAME/PASSWORD (Direct). "
                    "Use --dry-run for offline verification."
                )
            else:
                method = uploader.get_preferred_method()
                logger.info(f"Instagram publisher credential check passed: selected method is '{method}'.")
        else:
            optional_unavailable.append("Running in --dry-run mode: Live Instagram network upload is disabled.")

        status_dict = {
            "valid": len(critical_errors) == 0,
            "critical_errors": critical_errors,
            "warnings": warnings,
            "optional_unavailable": optional_unavailable,
            "ffmpeg": ffmpeg_available,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "dry_run": dry_run,
            "issues": critical_errors,  # Backward compatibility alias
        }

        for opt in optional_unavailable:
            logger.info(f"[PREFLIGHT OPTIONAL] {opt}")
        for w in warnings:
            logger.warning(f"[PREFLIGHT WARNING] {w}")
        for err in critical_errors:
            logger.error(f"[PREFLIGHT CRITICAL ERROR] {err}")

        if not status_dict["valid"] and not dry_run:
            raise EnvironmentError(f"Startup validation failed with critical errors: {'; '.join(critical_errors)}")

        return status_dict

    def load_tracker(self) -> Dict[str, Any]:
        from app.storage.safe_store import safe_read_json
        return safe_read_json(
            self.tracker_file,
            default_factory=lambda: {"last_post_date": None, "total_posts": 0, "history": []},
            validate_fn=lambda d: isinstance(d, dict) and "history" in d,
        )

    def save_tracker(self, data: Dict[str, Any]) -> None:
        from app.storage.safe_store import atomic_write_json
        atomic_write_json(self.tracker_file, data, indent=2, make_backup=True)

    def has_posted_today(self, tz: str = TIMEZONE) -> bool:
        """
        Check if today's single video has already been published.
        Multi-layer verification:
        1. Official Meta Graph API check (if configured)
        2. Direct Instagram profile feed inspection (if direct login configured)
        3. Local post tracker JSON fallback
        """
        today_str = get_current_time(tz).strftime("%Y-%m-%d")
        uploader = InstagramUploader()

        # 1. Official Meta Graph API check (preferred)
        if uploader.has_graph_credentials():
            try:
                from app.instagram.meta_graph_api import MetaInstagramClient
                from datetime import datetime
                from app.autonomous.timing_engine import get_tz
                client = MetaInstagramClient(
                    instagram_account_id=uploader.user_id,
                    access_token=uploader.access_token,
                )
                recent = client.get_recent_media(limit=1)
                if recent:
                    latest = recent[0]
                    ts_str = latest.get("timestamp", "")
                    if ts_str:
                        tz_obj = get_tz(tz)
                        clean_ts = ts_str.replace("+0000", "+00:00")
                        dt = datetime.fromisoformat(clean_ts).astimezone(tz_obj)
                        if dt.strftime("%Y-%m-%d") == today_str:
                            logger.info(f"Verified live Reel posted on Instagram via Meta Graph API today: {latest.get('id')} at {dt.strftime('%H:%M:%S')}")
                            tracker = self.load_tracker()
                            tracker["last_post_date"] = today_str
                            tracker["last_media_code"] = latest.get("id")
                            self.save_tracker(tracker)
                            return True
                        else:
                            logger.info(f"Meta Graph API check: No reel posted today ({today_str}). Latest post was on {dt.strftime('%Y-%m-%d')}.")
                            return False
            except Exception as exc:
                logger.debug(f"Meta Graph API profile verification skipped/failed: {exc}")

        # 2. Live direct account check (if direct credentials exist)
        elif uploader.has_direct_credentials():
            try:
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

        # 3. Local tracker fallback
        tracker = self.load_tracker()
        return tracker.get("last_post_date") == today_str

    def record_post_today(self, post_info: Dict[str, Any], tz: str = TIMEZONE) -> None:
        """Record today's completed video ONLY if verified published to Instagram."""
        outcome = post_info.get("publishing_outcome")
        ig_res = post_info.get("instagram_upload", {})
        media_id = ig_res.get("media_id")
        media_code = ig_res.get("media_code", "")
        media_url = ig_res.get("media_url", "")

        # Strictly enforce: ONLY PUBLISHED_VERIFIED with valid media_id can be recorded
        if outcome != "PUBLISHED_VERIFIED" or not media_id or ig_res.get("mode") == "DRY_RUN":
            logger.warning(
                f"[DAILY PUBLISHER] Skipping tracker update: Reel outcome is '{outcome}' "
                f"(not PUBLISHED_VERIFIED with confirmed media_id)."
            )
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
            "media_id": str(media_id),
            "media_code": media_code,
            "media_url": media_url,
            "video_path": str(post_info.get("video_path", "")),
        })
        tracker[today_str] = {
            "published_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "media_id": str(media_id),
            "media_code": media_code,
            "media_url": media_url,
            "topic": post_info.get("topic", ""),
        }
        self.save_tracker(tracker)
        logger.info(f"[DAILY PUBLISHER] Successfully recorded post for {today_str} (Media ID: {media_id})")

    def produce_trending_reel(
        self,
        niche: str = CONTENT_NICHE,
        language: str = CONTENT_LANGUAGE,
        voice: Optional[str] = None,
        dry_run: bool = False,
        topic_override: Optional[str] = None,
        category: Optional[str] = None,
        scene_image_paths: Optional[List[Path]] = None,
    ) -> Dict[str, Any]:
        """
        Executes complete production of a fresh trending viral reel with a strict two-stage process:
        - Self-Learning Daily Upgrade
        - Hot Trend Discovery (anti-fatigue, zero repetition)
        - 5-Beat Viral Retention Script with Replay Loop
        - STAGE 1: Dedicated Script-Driven Image Generation (Visuals generated based on script info)
        - STAGE 2: Frame-Synchronized Editing & Cinematic Composition (MoviePy editing, audio sync, kinetic subtitles)
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

        # Initialize Asset Lifecycle Tracking Job
        from app.storage.asset_lifecycle_manager import AssetLifecycleManager, JobState
        script_id = script_data.get("script_id") or f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        lifecycle_job_id = AssetLifecycleManager.create_job(
            topic=topic,
            script_id=script_id,
            script_data=script_data,
            scene_images=scene_image_paths,
        )

        # 4 & 5. Stage 1: Script-Driven Image Generation & Stage 2: Editing & Composition
        print(f"\n[STEP 4 & 5/6] Generating images based on script info, then executing frame-synchronized editing ({active_voice})...")
        output_filename = f"daily_reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        video_path = create_cinematic_reel_video(
            script_data=script_data,
            voice=active_voice,
            output_filename=output_filename,
            scene_image_paths=scene_image_paths,
        )
        print(f" -> Rendered MP4:     {video_path}")

        # Update lifecycle to VALIDATED
        AssetLifecycleManager.update_job_state(
            job_id=lifecycle_job_id,
            new_state=JobState.VALIDATED,
            message="Video composition and frame sync complete",
            metadata={"video_path": str(video_path)},
        )

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
        final_caption = caption_res.get("full_caption") or caption_res.get("final_caption", "")
        hashtags = caption_res.get("hashtags", [])

        seo_audit = caption_res.get("seo_audit") or verify_seo_integrity(script_data, final_caption, hashtags)
        print(f" -> SEO Score:        {seo_audit['overall_seo_score']}/100 [{seo_audit['verdict']}]")

        dest_dir = CONTENT_DIR
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

        final_duration = float(target_dur)
        try:
            from moviepy import VideoFileClip
            with VideoFileClip(str(final_video_dest)) as v_chk:
                if v_chk.duration:
                    final_duration = round(v_chk.duration, 2)
        except Exception as ve:
            logger.debug(f"Video duration probe notice: {ve}")

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
            uploader = InstagramUploader()
            upload_res = uploader.upload_reel(
                video_path=final_video_dest,
                caption=caption_text_to_save,
                force_dry_run=True,
            )
            res_info["instagram_upload"] = upload_res
            res_info["publishing_outcome"] = "DRY_RUN"
            AssetLifecycleManager.update_job_state(
                job_id=lifecycle_job_id,
                new_state=JobState.COMPLETED,
                message="Dry-run completed. Package preserved in insta content/ for review.",
            )
        else:
            uploader = InstagramUploader()
            if not uploader.has_credentials():
                print("\n[STEP 7/7] ⚠️ No live Instagram credentials configured in .env / GitHub Secrets.")
                print(" -> Required: INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN (Meta Graph API) or INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD / INSTAGRAM_SESSION_DATA (Direct)")
                no_creds_err = "Missing Instagram publishing credentials in production mode"
                res_info["publishing_outcome"] = "NO_CREDENTIALS"
                res_info["instagram_upload"] = {
                    "success": False,
                    "status": "NO_CREDENTIALS",
                    "publishing_outcome": "NO_CREDENTIALS",
                    "error": no_creds_err,
                }
                res_info["instagram_upload_error"] = no_creds_err
                AssetLifecycleManager.mark_failed(
                    job_id=lifecycle_job_id,
                    error_message=no_creds_err,
                )
            else:
                print("\n[STEP 7/7] Publishing Reel to Instagram live account...")
                try:
                    AssetLifecycleManager.update_job_state(
                        job_id=lifecycle_job_id,
                        new_state=JobState.UPLOADING,
                        message="Uploading Reel to Instagram",
                    )
                    full_post_caption = final_caption + "\n\n" + " ".join(hashtags)
                    
                    fingerprint = compute_video_fingerprint(final_video_dest)
                    res_info["video_fingerprint"] = fingerprint

                    upload_res = uploader.upload_reel(
                        video_path=final_video_dest,
                        caption=full_post_caption,
                    )
                    res_info["instagram_upload"] = upload_res
                    media_id = upload_res.get("media_id")
                    status = upload_res.get("status")
                    outcome = upload_res.get("publishing_outcome")

                    if (status in ("PUBLISHED", "PUBLISHED_VERIFIED") or outcome == "PUBLISHED_VERIFIED") and media_id:
                        res_info["publishing_outcome"] = "PUBLISHED_VERIFIED"
                        print(f"\n[INSTAGRAM REEL PUBLISHED AND VERIFIED] Media ID: {media_id} | Link: {upload_res.get('media_url')}")
                        AssetLifecycleManager.record_published(
                            job_id=lifecycle_job_id,
                            media_id=str(media_id),
                            media_code=upload_res.get("media_code", ""),
                            media_url=upload_res.get("media_url", ""),
                        )
                        AssetLifecycleManager.mark_verified(
                            job_id=lifecycle_job_id,
                            verified_source="instagram_upload_response",
                        )

                        print("\n[PERMANENT VISUAL MEMORY & AUTO-CLEANUP] Executing production verified asset lifecycle...")
                        try:
                            clean_stats = AssetLifecycleManager.run_cleanup_job(
                                job_id=lifecycle_job_id,
                                clean_reels=False,  # Keep latest reel in insta content/
                            )
                            print(f" -> 🧹 Reclaimed: {clean_stats['storage_reclaimed_mb']} MB across {clean_stats['assets_deleted_count']} files.")
                            print(f" -> 🧠 Permanent Visual Memory: {clean_stats['fingerprints_retained']} visual fingerprints preserved in durable storage.")
                            res_info["cleanup_report"] = clean_stats
                        except Exception as ce:
                            logger.warning(f"Lifecycle cleanup notice: {ce}")
                    else:
                        failure_reason = upload_res.get("error") or f"Live upload did not return confirmed media_id: {upload_res}"
                        print(f"\n[INSTAGRAM UPLOAD FAILED] {failure_reason}")
                        res_info["publishing_outcome"] = upload_res.get("publishing_outcome", "UPLOAD_FAILED")
                        res_info["instagram_upload_error"] = failure_reason
                        AssetLifecycleManager.mark_failed(
                            job_id=lifecycle_job_id,
                            error_message=failure_reason,
                        )
                except Exception as e:
                    e_str = str(e).lower()
                    if isinstance(e, PublishingAuthError) or "auth" in e_str or "login" in e_str or "checkpoint" in e_str or "challenge" in e_str or "qe/expose" in e_str:
                        outcome = "AUTHENTICATION_FAILED"
                    elif isinstance(e, TimeoutError) or "processing" in e_str or "timeout" in e_str:
                        outcome = "PROCESSING_FAILED"
                    elif isinstance(e, DuplicatePublishPreventedError):
                        outcome = "ALREADY_PUBLISHED"
                    else:
                        outcome = "UPLOAD_FAILED"

                    print(f"\n[INSTAGRAM PUBLISHING FAILED] Stage: {outcome}. Error: {e}. Video safely delivered to insta content/.")
                    res_info["publishing_outcome"] = outcome
                    res_info["instagram_upload_error"] = str(e)
                    AssetLifecycleManager.mark_failed(
                        job_id=lifecycle_job_id,
                        error_message=f"Instagram upload exception ({outcome}): {e}",
                    )

        # 8. Autonomous Community Retention & AI Comment Consultation
        if res_info.get("publishing_outcome") == "PUBLISHED_VERIFIED":
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
        else:
            print(f"\n[STEP 8/8] Skipping comment consultation (Reel was not published: {res_info.get('publishing_outcome')}).")

        # 9. Real-Time Algorithm Feedback Ingestion & Q-Value Evolution
        print("\n[STEP 9/9] Syncing live Instagram algorithm feedback & evolving Q-learning brain...")
        try:
            fb = self.reinforcement_engine.sync_live_insights_and_reward_brain(
                seo_score=seo_audit["overall_seo_score"],
            )
            print(f" -> Evolved Brain Level: {fb['evolution_level']} (Q-Reward: {fb['reward_score']})")
            overview_data["agent_evolution_level"] = fb["evolution_level"]
            overview_data["q_reward_score"] = fb["reward_score"]
            overview_data["publishing_outcome"] = res_info.get("publishing_outcome")
            with open(overview_dest, "w", encoding="utf-8") as f:
                json.dump(overview_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Reinforcement feedback notice: {e}")

        print("\n" + "=" * 75)
        outcome = res_info.get("publishing_outcome", "UNKNOWN")
        if outcome == "PUBLISHED_VERIFIED":
            print("  INSTAGRAM REEL PUBLISHED AND VERIFIED")
            print("  DAILY VIRAL REEL PRODUCTION COMPLETE!")
            print(f"  Topic:    {topic}")
            print(f"  Media ID: {res_info.get('instagram_upload', {}).get('media_id')}")
            print(f"  Link:     {res_info.get('instagram_upload', {}).get('media_url')}")
            print(f"  Saved to: {final_video_dest}")
            print(f"  Size:     {res_info['size_mb']} MB")
        elif outcome == "DRY_RUN":
            print("  DRY RUN COMPLETED — VIDEO GENERATED LOCALLY")
            print(f"  Topic:    {topic}")
            print(f"  Saved to: {final_video_dest}")
            print(f"  Size:     {res_info['size_mb']} MB")
        elif outcome == "NO_CREDENTIALS":
            print("  VIDEO GENERATION COMPLETED — NO PUBLISHING CREDENTIALS CONFIGURED")
            print(f"  Topic:    {topic}")
            print(f"  Saved to: {final_video_dest}")
            print(f"  Size:     {res_info['size_mb']} MB")
        else:
            print("  VIDEO GENERATION COMPLETED — INSTAGRAM PUBLISHING FAILED")
            print(f"  Topic:    {topic}")
            print(f"  Outcome:  {outcome}")
            print(f"  Reason:   {res_info.get('instagram_upload_error', 'Upload failed')}")
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
        # Preflight startup validation for dependencies, storage, and credentials
        self.validate_environment(dry_run=dry_run)

        now = get_current_time(tz)
        today_str = now.strftime("%Y-%m-%d")

        if not force and not dry_run and self.has_posted_today(tz=tz):
            secs, win_name, nxt = seconds_until_next_optimal(tz)
            print(f"[DAILY PUBLISHER] Today's video ({today_str}) has ALREADY been published to Instagram.")
            print(f"[DAILY PUBLISHER] Next optimal algorithm window: {nxt.strftime('%Y-%m-%d %H:%M')} ({win_name}) in {secs // 3600}h {(secs % 3600) // 60}m.")
            return {
                "status": "already_posted_today",
                "publishing_outcome": "ALREADY_PUBLISHED",
                "next_post_time": str(nxt),
            }

        # Check algorithm engagement window and velocity score
        in_peak, peak_name = is_in_optimal_window(tz)
        algo_state = self.algo_brain.get_algorithm_state(tz)
        velocity_score = algo_state.get("algorithm_velocity_score", 50.0)
        active_phase = algo_state.get("active_phase", "General")

        print(f"[DAILY PUBLISHER] Instagram Algorithm Status: {peak_name} (Velocity: {velocity_score}/100, Phase: {active_phase})")

        # Off-peak protection: If scheduled run triggers off-peak and velocity is low, defer to next peak window.
        # However, if running inside a scheduled CI/GitHub Actions job and today has not posted yet, proceed so
        # that runner queue latency (15-30 min delay) never prevents today's reel from being published.
        is_ci_job = bool(os.getenv("GITHUB_ACTIONS") or os.getenv("CI"))
        if not force and not dry_run and not in_peak and velocity_score < 75.0 and not is_ci_job:
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

        # Record in daily tracker ONLY if live published with confirmed media_id and verified outcome
        if not dry_run and result.get("publishing_outcome") == "PUBLISHED_VERIFIED" and result.get("instagram_upload", {}).get("media_id"):
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
    parser.add_argument("--validate", action="store_true", help="Validate runtime environment, tools, and credentials then exit")
    args = parser.parse_args()

    if args.validate:
        status = DailyAlgorithmPublisher.validate_environment(dry_run=args.dry_run)
        print(f"\n[VALIDATION STATUS] Valid: {status['valid']}, FFmpeg: {status['ffmpeg']}, Issues: {len(status['issues'])}, Warnings: {len(status['warnings'])}")
        sys.exit(0 if status["valid"] or args.dry_run else 1)

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
        result = publisher.run_daily_algorithm_cycle(
            force=args.force,
            dry_run=args.dry_run,
            topic=args.topic,
            category=args.category,
        )

        outcome = result.get("publishing_outcome")
        # In non-dry-run mode, publishing must be verified or already published
        if not args.dry_run:
            if outcome in ("UPLOAD_FAILED", "PROCESSING_FAILED", "AUTHENTICATION_FAILED"):
                logger.error(f"[CLI EXIT] Exiting with code 1 due to publishing failure: {outcome}")
                sys.exit(1)
            elif outcome == "NO_CREDENTIALS":
                logger.error("[CLI EXIT] Exiting with code 1: No Instagram credentials configured.")
                sys.exit(1)
            elif outcome not in ("PUBLISHED_VERIFIED", "ALREADY_PUBLISHED"):
                if result.get("status") not in ("already_posted_today", "off_peak_deferred"):
                    logger.error(f"[CLI EXIT] Exiting with code 1: Publication not verified (outcome: {outcome})")
                    sys.exit(1)
