"""
Authoritative Instant Publisher Entrypoint.
Delegates to PublishingService with state machine tracking and dry-run safety.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.publishing.publishing_service import PublishingService
from app.instagram.meta_graph_api import MetaInstagramClient
from app.publishing.state_machine import PublishingState


def main():
    video_path = PROJECT_ROOT / "insta content" / "viral_reel_video.mp4"
    caption_path = PROJECT_ROOT / "insta content" / "caption_and_hashtags.txt"

    if not video_path.exists():
        # Fallback to output/reels if insta content not present
        candidates = list((PROJECT_ROOT / "output" / "reels").glob("*.mp4"))
        if candidates:
            video_path = candidates[0]
        else:
            print(f"Error: Video file not found at {video_path}")
            return

    caption = ""
    if caption_path.exists():
        with open(caption_path, "r", encoding="utf-8") as f:
            caption = f.read()
    else:
        caption = "New AI generated reel! #trending"

    ps = PublishingService()
    meta_client = MetaInstagramClient()

    is_live = ps.is_auto_publish_enabled()
    print("\n" + "=" * 70)
    print("  INSTA-AGENT CENTRALIZED PUBLISHING PIPELINE")
    print("=" * 70)
    print(f"  Target Video:  {video_path}")
    print(f"  Live Publish:  {'ENABLED' if is_live else 'DISABLED (Dry Run Simulation)'}")
    print(f"  Meta Account:  {meta_client.account_id or 'Not Configured'}")
    print("=" * 70)

    try:
        record = ps.publish_reel(
            account_id=meta_client.account_id or "default_account",
            niche_id="general",
            topic="Instant Reel Upload",
            video_path=video_path,
            caption=caption,
            meta_client=meta_client,
            force_dry_run=not is_live,
        )

        print("\n" + "=" * 70)
        print(f"  JOB STATUS:    {record.state.value}")
        print(f"  JOB ID:        {record.job_id}")
        if record.state == PublishingState.PUBLISHED:
            print(f"  MEDIA ID:      {record.instagram_media_id}")
            print(f"  PERMALINK:     {record.instagram_permalink}")
        elif record.state == PublishingState.DRY_RUN:
            print("  SIMULATION COMPLETE: File verified, no external API calls made.")
        print("=" * 70)

    except Exception as exc:
        print(f"\n[ERROR] Publishing failed: {exc}")


if __name__ == "__main__":
    main()
