import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.instagram.uploader import InstagramUploader

def main():
    video_path = PROJECT_ROOT / "insta content" / "viral_reel_video.mp4"
    caption_path = PROJECT_ROOT / "insta content" / "caption_and_hashtags.txt"

    if not video_path.exists():
        print(f"Error: Video file not found at {video_path}")
        return

    with open(caption_path, "r", encoding="utf-8") as f:
        caption = f.read()

    uploader = InstagramUploader()
    if not uploader.has_credentials():
        print("\n" + "=" * 70)
        print("  INSTAGRAM CREDENTIALS REQUIRED TO PUBLISH LIVE")
        print("=" * 70)
        print("To post live to your Instagram account (@neodivinestore.in):")
        print("1. Open your .env file")
        print("2. Add your Instagram password:")
        print("   INSTAGRAM_PASSWORD=your_actual_password_here")
        print("   (Or set INSTAGRAM_SESSION_ID=your_sessionid_cookie)")
        print("3. Then run this command again:")
        print("   .venv\\Scripts\\python.exe publish_now.py")
        print("=" * 70)
        return

    print("\n" + "=" * 70)
    print("  UPLOADING REEL LIVE TO INSTAGRAM ACCOUNT")
    print(f"  Target Account: {uploader.username or 'Configured Account'}")
    print(f"  Video Path:     {video_path}")
    print("=" * 70)

    try:
        res = uploader.upload_reel(video_path=video_path, caption=caption)
        if res.get("status") == "PUBLISHED" or res.get("media_id"):
            print("\n" + "=" * 70)
            print("  SUCCESS! Reel is now LIVE on Instagram!")
            print(f"  Media ID:  {res.get('media_id')}")
            print(f"  URL:       {res.get('media_url', 'Check your Instagram profile!')}")
            print("=" * 70)
        else:
            print("\nUpload Response:", res)
    except Exception as e:
        print(f"\nUpload Error: {e}")

if __name__ == "__main__":
    main()
