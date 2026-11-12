import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.caption_agent import optimize_caption
from app.agents.gemini_client import check_health
from app.agents.script_agent import generate_reel
from app.analytics.audit_agent import audit_profile
from app.analytics.seo_optimizer import generate_seo_metadata
from app.instagram.uploader import InstagramUploader, upload_or_preview_reel
from app.research.trend_agent import research_viral_ideas
from app.video.cinematic_composer import create_cinematic_reel_video
from app.video.preflight_checker import PreFlightQualityGate, format_preflight_report
from app.video.tts_engine import generate_speech
from app.video.video_composer import create_reel_video
from config.settings import (
    AUDIO_DIR,
    CONTENT_LANGUAGE,
    DEFAULT_GEMINI_MODEL,
    OUTPUT_DIR,
    REELS_DIR,
    SCRIPTS_DIR,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("InstagramAgent")


def run_full_pipeline(
    topic: str,
    niche: str = "Vedic astrology",
    language: str = "Hindi mixed with English",
    duration: int = 30,
    theme_name: str = "cosmic",
    voice: Optional[str] = None,
    upload: bool = False,
    force_dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Execute the complete end-to-end pipeline:
    1. Gemini Script & Hook generation
    2. Neural Text-To-Speech (audio voiceover)
    3. High-retention 1080x1920 video composition
    4. Caption optimization
    5. Instagram publishing or dry-run validation
    """
    print("\n" + "=" * 70)
    print("      INSTAGRAM VIDEO AGENT (POWERED BY GEMINI AI)")
    print("=" * 70)
    print(f"Topic:        {topic}")
    print(f"Niche:        {niche}")
    print(f"Language:     {language}")
    print(f"Target Time:  ~{duration}s")
    print(f"Visual Theme: {theme_name}")
    print(f"Auto-Upload:  {'YES' if upload else 'NO (Local Only)'}")
    print("-" * 70)

    # STEP 1: EXTRACT INSTAGRAM EXPLORE SEO & GENERATE SCRIPT
    print("\n[STEP 1/5] Extracting Instagram Explore SEO keywords & generating script...")
    seo_metadata = generate_seo_metadata(topic=topic, niche=niche)
    keywords = seo_metadata.get("primary_search_keywords", [])
    print(f" -> High-Volume SEO Keywords: {', '.join(keywords) if keywords else 'Auto-indexed'}")
    print(f" -> Retention Loop Hook:      \"{seo_metadata.get('loop_closing_phrase', '')}\"")
    print(f" -> Save/Share Trigger:       \"{seo_metadata.get('save_trigger_reason', '')}\"")

    script_data = generate_reel(
        topic=topic,
        niche=niche,
        language=language,
        duration=duration,
        seo_metadata=seo_metadata,
    )

    hook = script_data["selected_hook"]
    print(f" -> Selected Hook (Formula #{hook.get('formula_id')}: {hook.get('formula_name')})")
    print(f"    Audio:     \"{hook['spoken']}\"")
    print(f"    On-Screen: \"{hook['on_screen']}\"")
    print(f"    Score:     {hook.get('score', 'N/A')}/100 [{hook.get('verdict', 'OK')}]")
    print(f"    Scenes:    {len(script_data['scenes'])} scenes generated")

    # STEP 2: COMPOSE 1080x1920 CINEMATIC REEL (PER-SCENE AUDIO + 4K B-ROLL + SACRED SOUND DESIGN)
    print("\n[STEP 2/5] Composing 1080x1920 Cinematic Reel with frame-synced audio & 4K visuals...")
    video_path = create_cinematic_reel_video(
        script_data=script_data,
        voice=voice,
    )
    print(f" -> Cinematic Video rendered successfully!")
    print(f"    File: {video_path}")

    # STEP 3: OPTIMIZE CAPTION & HASHTAGS
    print("\n[STEP 3/5] Optimizing Instagram caption for maximum reach & SEO indexing...")
    top_kw = keywords[0] if keywords else None
    caption_res = optimize_caption(
        topic=topic,
        script_hook=hook["spoken"],
        draft_caption=script_data["caption"],
        niche=niche,
        target_keyword=top_kw,
        script_data=script_data,
        language=language,
    )
    final_caption = caption_res["full_caption"]
    hashtags = seo_metadata.get("recommended_hashtags") or caption_res["hashtags"]
    print(f" -> Caption ready!")
    print(f"    First line: \"{caption_res['visible_first_line']}\"")
    print(f"    Hashtags:   {' '.join(hashtags)}")

    # STEP 4: PRE-FLIGHT QUALITY VERIFICATION & ALGORITHM TIMING AUDIT
    print("\n[STEP 4/5] Executing Pre-Flight Quality Gate & Algorithm Timing Audit...")
    preflight_report = PreFlightQualityGate.verify_content_package(
        video_path=video_path,
        script_data=script_data,
        caption=final_caption,
        hashtags=hashtags,
    )
    print(format_preflight_report(preflight_report))

    # STEP 5: INSTAGRAM UPLOAD / DRY RUN
    if upload and not force_dry_run:
        print("\n[STEP 5/5] Publishing directly to Instagram...")
        upload_result = upload_or_preview_reel(
            video_path=video_path,
            caption=final_caption,
            force_dry_run=False,
        )
    else:
        print("\n[STEP 5/5] Validating Reel & generating upload manifest (Local / Dry-run mode)...")
        upload_result = upload_or_preview_reel(
            video_path=video_path,
            caption=final_caption,
            force_dry_run=True,
        )

    manifest = {
        "status": "PUBLISHED" if (upload_result and upload_result.get("success") and not upload_result.get("mode") == "DRY_RUN") else "COMPLETED",
        "topic": topic,
        "niche": niche,
        "language": language,
        "video_path": str(video_path),
        "script_summary": {
            "hook": hook["spoken"],
            "on_screen_hook": hook["on_screen"],
            "hook_score": hook.get("score"),
            "scenes": len(script_data["scenes"]),
        },
        "caption": final_caption,
        "preflight_audit": preflight_report,
        "upload_result": upload_result,
    }

    manifest_file = OUTPUT_DIR / "latest_pipeline_result.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("                 PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"Video MP4:      {video_path}")
    print(f"Result JSON:    {manifest_file}")
    if upload_result and upload_result.get("success"):
        print(f"Published ID:   {upload_result.get('media_id')}")
        if upload_result.get("media_url"):
            print(f"Live Reel URL:  {upload_result.get('media_url')}")
    print("=" * 70 + "\n")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Video Generation & Upload Agent (Gemini API Powered)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Agent commands")

    # Command: run (end-to-end pipeline)
    run_parser = subparsers.add_parser("run", help="Run complete generation & upload pipeline")
    run_parser.add_argument("--topic", "-t", type=str, required=True, help="Topic for the Reel")
    run_parser.add_argument("--niche", "-n", type=str, default="Vedic astrology", help="Content niche")
    run_parser.add_argument("--lang", "-l", type=str, default=CONTENT_LANGUAGE, help="Script language")
    run_parser.add_argument("--duration", "-d", type=int, default=30, help="Target duration in seconds")
    run_parser.add_argument(
        "--theme",
        type=str,
        default="3d_space",
        choices=["3d_space", "cosmic", "dark_gold", "neon_cyber", "crimson_fire", "minimalist_dark"],
        help="Visual background theme (supports true 3D procedural space)",
    )
    run_parser.add_argument("--voice", "-v", type=str, default=None, help="TTS Voice ID")
    run_parser.add_argument("--upload", "-u", action="store_true", help="Publish to Instagram after generating")
    run_parser.add_argument("--dry-run", action="store_true", help="Force dry-run validation")

    # Command: script
    script_parser = subparsers.add_parser("script", help="Generate & score Reel script only")
    script_parser.add_argument("--topic", "-t", type=str, required=True)
    script_parser.add_argument("--niche", "-n", type=str, default="Vedic astrology")
    script_parser.add_argument("--duration", "-d", type=int, default=30)

    # Command: research
    research_parser = subparsers.add_parser("research", help="Find viral Reel ideas with Gemini")
    research_parser.add_argument("--niche", "-n", type=str, default="Vedic astrology")
    research_parser.add_argument("--count", "-c", type=int, default=5)

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Audit Instagram profile with 12-item rubric")
    audit_parser.add_argument("--name", type=str, required=True)
    audit_parser.add_argument("--handle", type=str, required=True)
    audit_parser.add_argument("--bio", type=str, required=True)
    audit_parser.add_argument("--link", type=str, default="")

    # Command: test
    subparsers.add_parser("test", help="Test Gemini API and system dependencies")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "run":
        run_full_pipeline(
            topic=args.topic,
            niche=args.niche,
            language=args.lang,
            duration=args.duration,
            theme_name=args.theme,
            voice=args.voice,
            upload=args.upload,
            force_dry_run=args.dry_run,
        )

    elif args.command == "script":
        print(f"\nGenerating script for: {args.topic}...")
        res = generate_reel(args.topic, niche=args.niche, duration=args.duration)
        print("\nWINNING HOOK:", res["selected_hook"]["spoken"])
        print("\nFULL SCRIPT:")
        print(res["full_script"])
        print("\nCAPTION:")
        print(res["caption"])

    elif args.command == "research":
        print(f"\nResearching viral ideas for niche: {args.niche}...")
        ideas = research_viral_ideas(niche=args.niche, count=args.count)
        for idx, idea in enumerate(ideas, 1):
            print(f"\n{idx}. {idea['topic']} [{idea.get('recommended_formula', '')}]")
            print(f"   Hook: {idea['hook_angle']}")
            print(f"   Why:  {idea['why_it_works']}")

    elif args.command == "audit":
        print(f"\nAuditing profile @{args.handle}...")
        res = audit_profile(name=args.name, handle=args.handle, bio=args.bio, link=args.link)
        print(f"\nTOTAL SCORE: {res['total_score']} / 100 ({res['verdict']})")
        print("\nTOP RECOMMENDED FIXES:")
        for fix in res.get("top_three_fixes", []):
            print(f" - {fix}")
        print("\nOPTIMIZED PROFILE REWRITE:")
        for k, v in res.get("recommended_rewrite", {}).items():
            print(f" {k}: {v}")

    elif args.command == "test":
        print("\nChecking Gemini API Health...")
        health = check_health()
        print("Gemini Status:", health)

        print("\nChecking Instagram API Configuration...")
        uploader = InstagramUploader()
        creds = uploader.verify_credentials()
        print("Instagram Status:", creds)


if __name__ == "__main__":
    main()
