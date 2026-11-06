import os
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent
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

from app.autonomous.autonomous_agent import run_autonomous_reel_cycle
from app.instagram.uploader import InstagramUploader

if __name__ == "__main__":
    uploader = InstagramUploader()
    has_creds = uploader.has_credentials()

    print("\n" + "=" * 70)
    print("      🚀 1-CLICK AUTONOMOUS VIRAL ASTROLOGY REEL ENGINE")
    print("=" * 70)
    print("This engine runs completely hands-free:")
    print("  • Rotates topics automatically across Wealth, Marriage, Career,")
    print("    Psychic Intuition, and Gemstone Cautions (Zero repetition)")
    print("  • Matches distinct, authentic high-res photography per topic")
    print("  • Generates tailored Hindi voiceover & kinetic subtitles")
    print("  • Enforces Comment Placement + DM to Book Consultation (No bio link)")
    print("  • Saves master deliverables directly to 'insta content/'")
    print("=" * 70)

    # If creds exist and auto upload desired, publish; otherwise dry-run save
    dry_run = True
    if has_creds and os.getenv("AUTO_PUBLISH_LIVE", "false").lower() == "true":
        dry_run = False

    run_autonomous_reel_cycle(force_dry_run=dry_run)
