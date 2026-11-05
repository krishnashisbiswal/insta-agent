import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.main import main as cli_main, run_full_pipeline
from app.autonomous.autonomous_agent import run_autonomous_reel_cycle
from app.autonomous.autopilot import run_single_autonomous_publish, start_autopilot_daemon
from app.autonomous.content_manager import ContentManager
from app.research.trend_agent import research_viral_ideas
from app.analytics.audit_agent import audit_profile
from app.agents.gemini_client import check_health
from app.analytics.self_learning_engine import SelfLearningEngine
from app.instagram.uploader import InstagramUploader
from config.settings import CONTENT_LANGUAGE, CONTENT_NICHE, CONTENT_THEME
from scheduler import run_scheduler


def interactive_menu():
    print("\n" + "=" * 68)
    print("      AUTONOMOUS INSTAGRAM REEL AGENT (GEMINI AI)")
    print("=" * 68)
    print("1. [AUTONOMOUS] 1-Click Autonomous Reel (Topic -> Video -> Upload)")
    print("2. [SCHEDULER]  Start Background Posting Daemon (Runs every X hours)")
    print("3. [CUSTOM]     Create Video for Specific Topic")
    print("4. [RESEARCH]   Find Viral Reel Angles with Gemini AI")
    print("5. [QUEUE]      View / Refill Autonomous Content Queue")
    print("6. [AUDIT]      Audit Instagram Profile (100-Point Rubric)")
    print("7. [TEST]       Check Gemini API & Instagram Credentials")
    print("8. [TRAIN]      Trigger Daily Self-Upgrade & View Agent Brain Level")
    print("9. Exit")
    print("=" * 68)

    choice = input("\nSelect an option (1-9): ").strip()

    if choice == "1":
        print("\n--- AUTONOMOUS 1-CLICK REEL CREATOR ---")
        niche = input(f"Enter niche [{CONTENT_NICHE}]: ").strip() or CONTENT_NICHE
        lang = input(f"Enter language [{CONTENT_LANGUAGE}]: ").strip() or CONTENT_LANGUAGE
        
        uploader = InstagramUploader()
        has_creds = uploader.has_credentials()
        
        if not has_creds:
            print("\n[NOTE] No Instagram credentials found in .env.")
            print("The agent will autonomously generate the Reel and save the manifest locally.")
            dry_run = True
        else:
            upload_choice = input(f"Publish live to Instagram via {uploader.get_preferred_method()}? (y/N): ").strip().lower()
            dry_run = upload_choice != "y"

        run_autonomous_reel_cycle(niche=niche, language=lang, force_dry_run=dry_run)

    elif choice == "2":
        print("\n--- BACKGROUND POSTING SCHEDULER (DAEMON) ---")
        interval_input = input("Enter posting interval in hours [12]: ").strip() or "12"
        interval = int(interval_input)
        niche = input(f"Enter niche [{CONTENT_NICHE}]: ").strip() or CONTENT_NICHE
        
        uploader = InstagramUploader()
        dry_run = not uploader.has_credentials()
        if dry_run:
            print("\n[NOTE] No credentials configured. Running scheduler in Local Dry-Run mode.")

        run_scheduler(interval_hours=interval, niche=niche, dry_run=dry_run)

    elif choice == "3":
        topic = input("\nEnter Reel topic (e.g. 'Why Saturn delays success'): ").strip()
        if not topic:
            print("Topic cannot be empty.")
            return

        niche = input(f"Enter niche [{CONTENT_NICHE}]: ").strip() or CONTENT_NICHE
        lang = input(f"Enter language [{CONTENT_LANGUAGE}]: ").strip() or CONTENT_LANGUAGE

        print("\nAvailable Themes:")
        print("1. 3D Space & Spatial Objects (3D Rotating Planets, Gold Coins, Cyber Cores)")
        print("2. Cosmic (Dark Indigo / Orbit Rings / Nebula)")
        print("3. Dark Gold (Obsidian / Gold Glow / Luxury)")
        print("4. Neon Cyber (Slate / Cyan Neon / High Contrast)")
        print("5. Crimson Fire (Dark Magma / Red Accent)")
        print("6. Minimalist Dark (Titanium / Clean)")
        theme_choice = input("Select theme (1-6) [1]: ").strip() or "1"
        theme_map = {
            "1": "3d_space",
            "2": "cosmic",
            "3": "dark_gold",
            "4": "neon_cyber",
            "5": "crimson_fire",
            "6": "minimalist_dark",
        }
        theme = theme_map.get(theme_choice, "3d_space")

        upload_choice = input("\nDo you want to upload directly to Instagram? (y/N): ").strip().lower()
        should_upload = upload_choice == "y"

        run_full_pipeline(
            topic=topic,
            niche=niche,
            language=lang,
            theme_name=theme,
            upload=should_upload,
            force_dry_run=not should_upload,
        )

    elif choice == "4":
        niche = input(f"\nEnter niche to research [{CONTENT_NICHE}]: ").strip() or CONTENT_NICHE
        print(f"\nResearching 5 viral angles with Gemini for '{niche}'...")
        ideas = research_viral_ideas(niche=niche, count=5)
        print("\n" + "=" * 65)
        print("VIRAL REEL ANGLES FOUND:")
        print("=" * 65)
        for i, item in enumerate(ideas, 1):
            print(f"\n{i}. {item['topic']} [{item.get('recommended_formula', '')}]")
            print(f"   Hook: {item['hook_angle']}")
            print(f"   Why:  {item['why_it_works']}")

    elif choice == "5":
        cm = ContentManager()
        queue = cm.load_queue()
        print(f"\nCURRENT CONTENT QUEUE ({len(queue)} items):")
        for i, item in enumerate(queue, 1):
            print(f"{i}. {item['topic']} ({item.get('formula_type', 'General')})")

        refill = input("\nDo you want Gemini to brainstorm and add 5 more topics to queue? (y/N): ").strip().lower()
        if refill == "y":
            niche = input(f"Niche [{CONTENT_NICHE}]: ").strip() or CONTENT_NICHE
            cm.refill_queue_with_gemini(niche=niche, batch_size=5)

    elif choice == "6":
        name = input("\nEnter Profile Name field: ").strip()
        handle = input("Enter Instagram @handle: ").strip()
        bio = input("Enter current Bio: ").strip()
        link = input("Enter link (optional): ").strip()

        print(f"\nAuditing @{handle} against 100-point rubric...")
        audit = audit_profile(name=name, handle=handle, bio=bio, link=link)
        print(f"\nTOTAL SCORE: {audit['total_score']} / 100 ({audit['verdict']})")
        print("\nTOP THREE FIXES:")
        for fix in audit.get("top_three_fixes", []):
            print(f" - {fix}")
        print("\nRECOMMENDED REWRITE:")
        for k, v in audit.get("recommended_rewrite", {}).items():
            print(f" {k}: {v}")

    elif choice == "7":
        print("\n--- GEMINI API STATUS ---")
        health = check_health()
        print(health)

        print("\n--- INSTAGRAM PUBLISHING STATUS ---")
        uploader = InstagramUploader()
        creds = uploader.verify_credentials()
        print(creds)

    elif choice == "8":
        print("\n--- AGENT SELF-TRAINING & KNOWLEDGE EVOLUTION ---")
        engine = SelfLearningEngine()
        playbook = engine.load_playbook()
        print(f"Current Agent Level: {playbook.get('evolution_level', 1.0):.1f}")
        print(f"Total Cycles:        {playbook.get('total_training_cycles', 0)}")
        print(f"Last Upgrade:        {playbook.get('last_upgrade_date')}")
        print(f"Winning Hooks Bank:  {len(playbook.get('winning_hooks_bank', []))} templates")

        do_train = input("\nRun meta-learning self-upgrade now with Gemini? (y/N): ").strip().lower()
        if do_train == "y":
            engine.run_daily_self_upgrade(force=True)

    elif choice == "9":
        print("Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ("auto", "autopilot"):
            if "--daemon" in sys.argv:
                start_autopilot_daemon()
            else:
                run_single_autonomous_publish()
        elif cmd == "schedule":
            run_scheduler()
        else:
            cli_main()
    else:
        interactive_menu()
