import base64
import json
from pathlib import Path

session_file = Path("storage/instagram_session.json")
if not session_file.exists():
    print("Error: storage/instagram_session.json not found.")
    exit(1)

with open(session_file, "r", encoding="utf-8") as f:
    session_text = f.read().strip()

b64_val = base64.b64encode(session_text.encode("utf-8")).decode("utf-8")

print("=" * 75)
print("  INSTAGRAM SESSION SECRET FOR GITHUB ACTIONS")
print("=" * 75)
print("\nTo enable 100% automated publishing directly from GitHub Actions cloud:")
print("1. Go to: https://github.com/krishnashisbiswal/insta-agent/settings/secrets/actions")
print("2. Click 'New repository secret' (or edit existing)")
print("3. Name:  INSTAGRAM_SESSION_DATA")
print("4. Value: Paste the base64 string below (all one line):\n")
print(b64_val)
print("\n" + "=" * 75)
