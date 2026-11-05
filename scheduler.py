import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root in sys.path
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
from config.settings import AUTO_POST_INTERVAL_HOURS

logger = logging.getLogger("AutonomousScheduler")


def run_scheduler(
    interval_hours: int = 12,
    niche: str = "Vedic astrology",
    language: str = "Hindi mixed with English",
    theme: str = "cosmic",
    dry_run: bool = False,
    run_immediately: bool = True,
):
    """
    Continuous background daemon that produces and publishes Reels on a set schedule.
    """
    print("\n" + "=" * 70)
    print("      AUTONOMOUS INSTAGRAM REEL SCHEDULER (DAEMON)")
    print("=" * 70)
    print(f"Interval:     Every {interval_hours} hour(s)")
    print(f"Niche:        {niche}")
    print(f"Language:     {language}")
    print(f"Theme:        {theme}")
    print(f"Mode:         {'DRY-RUN (Local Only)' if dry_run else 'LIVE INSTAGRAM PUBLISH'}")
    print("=" * 70 + "\n")

    cycle_count = 0

    while True:
        if run_immediately or cycle_count > 0:
            cycle_count += 1
            print(f"\n[DAEMON CYCLE #{cycle_count}] Starting autonomous reel production...")
            try:
                run_autonomous_reel_cycle(
                    niche=niche,
                    language=language,
                    theme_name=theme,
                    force_dry_run=dry_run,
                )
            except Exception as exc:
                print(f"[ERROR in Cycle #{cycle_count}]: {exc}")
                logger.exception("Autonomous cycle failed")

        next_run = datetime.now() + timedelta(hours=interval_hours)
        print(f"\n[DAEMON] Next scheduled Reel at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[DAEMON] Sleeping for {interval_hours} hours. Press Ctrl+C to stop.\n")

        # Sleep with periodic 1-minute updates
        seconds_to_wait = interval_hours * 3600
        start_wait = time.time()
        try:
            while time.time() - start_wait < seconds_to_wait:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n[DAEMON] Scheduler stopped by user.")
            break


def main():
    parser = argparse.ArgumentParser(description="Autonomous Instagram Reel Scheduler")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=AUTO_POST_INTERVAL_HOURS,
        help="Posting interval in hours (default: 12)",
    )
    parser.add_argument("--niche", "-n", type=str, default="Vedic astrology", help="Content niche")
    parser.add_argument("--lang", "-l", type=str, default="Hindi mixed with English", help="Language")
    parser.add_argument("--theme", "-t", type=str, default="cosmic", help="Visual theme")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no live upload)")
    parser.add_argument("--once", action="store_true", help="Run a single autonomous cycle and exit")

    args = parser.parse_args()

    if args.once:
        print("\nExecuting single autonomous Reel cycle...")
        run_autonomous_reel_cycle(
            niche=args.niche,
            language=args.lang,
            theme_name=args.theme,
            force_dry_run=args.dry_run,
        )
    else:
        run_scheduler(
            interval_hours=args.interval,
            niche=args.niche,
            language=args.lang,
            theme=args.theme,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
