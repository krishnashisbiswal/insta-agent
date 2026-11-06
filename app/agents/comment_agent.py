import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows UTF-8 safety
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config.settings import STORAGE_DIR
from app.agents.gemini_client import generate_json, generate_text

logger = logging.getLogger("CommentAgent")
COMMENT_STORAGE_FILE = STORAGE_DIR / "comment_replies.json"


class CommentAgent:
    """
    Autonomous AI Community Retention & Comment Consultation Agent.
    - Listens to incoming viewer comments on Instagram Reels.
    - Detects astrological placements, birth details (DOB, Time), or life struggles (wealth, love, career).
    - Crafts 100% authentic, high-empathy personalized Vedic readings with free scriptural remedies.
    - Automatically replies to comments to maximize audience retention, viral algorithm weighting,
      and follower conversion.
    """

    def __init__(self, storage_file: Path = COMMENT_STORAGE_FILE):
        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

    def load_reply_history(self) -> Dict[str, Any]:
        """Loads records of previously answered comment IDs to prevent duplicate replies."""
        if not self.storage_file.exists():
            return {"replied_comments": {}}
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"replied_comments": {}}

    def save_reply_history(self, history: Dict[str, Any]) -> None:
        """Saves replied comment records to disk."""
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def generate_consultation_reply(
        self,
        comment_text: str,
        commenter_name: str = "Friend",
        topic: str = "Vedic Astrology Guidance",
        language: str = "Hindi",
    ) -> Dict[str, Any]:
        """
        Uses Gemini to generate a high-empathy, personalized Vedic astrology consultation reply.
        Strict 2-3 sentence format:
        1. Empathic acknowledgement of their specific placement or birth date.
        2. Accurate astrological insight explaining what is happening karmically.
        3. Zero-cost scriptural remedy + invitation to DM for full chart guidance.
        """
        is_hindi = language.lower() in ["hindi", "hi"] or any(
            ord(c) >= 0x0900 and ord(c) <= 0x097F for c in comment_text
        )

        language_instruction = (
            "LANGUAGE: Write in warm, conversational, respectful HINDI (Devanagari script) with clarifying terms in brackets if helpful. "
            "Use respectful terms like 'नमस्ते जी', 'आपकी कुंडली में...'."
            if is_hindi
            else "LANGUAGE: Write in warm, respectful, eloquent English."
        )

        prompt = f"""
You are the master Vedic astrologer and community mentor for Neo Divine Store (@neodivinestore.in).
A viewer has left a comment on your viral Instagram Reel about "{topic}".

VIEWER'S USERNAME: @{commenter_name}
VIEWER'S COMMENT: "{comment_text}"

{language_instruction}

OBJECTIVES:
1. Parse whatever birth details, zodiac sign, house, or placement they provided (e.g. DOB, Lagna, Rahu in 2nd, Saturn in 8th, etc.).
2. Offer a genuine, accurate, 2-sentence personalized preliminary astrological reading explaining what is occurring karmically.
3. Consultation Conversion (NO UNVERIFIED GENERIC REMEDIES): Explicitly explain that remedies must be customized based on their exact degrees, nakshatras, and Mahadasha to avoid energetic clashes.
4. Retention Call: Urge them to send a Direct Message (DM) to book a consultation for full deep chart analysis. NEVER mention 'link in bio' or 'bio mein link hai'! ONLY DM!
5. Max length: 45 to 65 words (ideal for Instagram comment readability).
6. Never be arrogant or fearmongering; be deeply reassuring, insightful, and spiritually elevating.

Return ONLY valid JSON:
{{
  "detected_placement": "Brief summary of what placement or question was extracted",
  "reply_text": "Complete polished reply ready to post directly on Instagram",
  "consultation_cta": "Clear booking prompt instructing them to DM"
}}
"""
        try:
            data = generate_json(prompt)
            if data and data.get("reply_text"):
                return data
        except Exception as e:
            logger.warning(f"Gemini comment analysis fallback: {e}")

        # Reassuring fallback reply
        if is_hindi:
            reply = f"नमस्ते @{commenter_name}! आपकी कुंडली का यह प्रभाव महत्वपूर्ण संकेत दे रहा है। बिना सटीक डिग्री और महादशा जाने कोई भी सामान्य उपाय न करें। अपने संपूर्ण विश्लेषण और परामर्श बुक करने के लिए हमें तुरंत DM करें। 🙏✨"
        else:
            reply = f"Hello @{commenter_name}! This planetary placement brings key karmic shifts. Because remedies vary by exact degrees and Mahadasha, avoid generic rituals. Send us a DM to book your consultation for full analysis! 🙏✨"

        return {
            "detected_placement": "General chart query",
            "reply_text": reply,
            "recommended_remedy": "Mantra and lamp ritual",
        }

    def process_reel_comments(
        self,
        uploader: Any,
        media_id: Optional[str] = None,
        topic: str = "Vedic Astrology Insights",
        max_comments: int = 10,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Polls Instagram comments for a media item, filters out already-answered comments,
        generates personalized astrological replies, and posts them.
        """
        history = self.load_reply_history()
        replied_map = history.get("replied_comments", {})
        processed: List[Dict[str, Any]] = []

        # If running in live mode with valid direct client
        if not dry_run and uploader and uploader.has_direct_credentials():
            try:
                cl = uploader._init_direct_client()
                if not media_id:
                    # Get latest user media
                    user_id = cl.user_id_from_username(uploader.username)
                    medias = cl.user_medias(user_id, amount=3)
                    if medias:
                        media_id = medias[0].id

                if media_id:
                    comments = cl.media_comments(media_id, amount=max_comments)
                    print(f"[COMMENT AGENT] Found {len(comments)} recent comments on media {media_id}.")
                    for c in comments:
                        c_id = str(c.pk)
                        if c_id in replied_map:
                            continue

                        # Generate reply
                        consultation = self.generate_consultation_reply(
                            comment_text=c.text,
                            commenter_name=c.user.username,
                            topic=topic,
                        )
                        reply_text = consultation["reply_text"]

                        # Post reply via instagrapi
                        cl.media_comment(media_id, reply_text, replied_to_comment_id=int(c_id))
                        replied_map[c_id] = {
                            "username": c.user.username,
                            "comment": c.text,
                            "reply": reply_text,
                            "timestamp": int(time.time()),
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        processed.append(replied_map[c_id])
                        print(f" -> Replied to @{c.user.username}: \"{reply_text[:60]}...\"")
                        time.sleep(2)  # Respect rate limits

                    history["replied_comments"] = replied_map
                    self.save_reply_history(history)
                    return processed
            except Exception as e:
                logger.warning(f"Live comment processing encountered error: {e}")

        # Dry-run / Demonstration mode: Simulate responsive customer retention
        print("[COMMENT AGENT] Running comment engagement simulation (Retention Test)...")
        sample_inquiries = [
            {"username": "rahul_sharma99", "comment": "Mera birth date 14 May 1994 hai, #1 placement hai Rahu in 2nd house. Kya karein?"},
            {"username": "priya_astrology", "comment": "I have Saturn in 8th house in Scorpio lagna, facing massive delays in career."},
            {"username": "vikram_aditya", "comment": "Do I have Kemdrum Dosh? Moon is completely isolated in my 4th house."},
        ]

        for item in sample_inquiries:
            cid = f"mock_{item['username']}"
            if cid in replied_map:
                continue

            consultation = self.generate_consultation_reply(
                comment_text=item["comment"],
                commenter_name=item["username"],
                topic=topic,
            )
            entry = {
                "username": item["username"],
                "comment": item["comment"],
                "detected_placement": consultation.get("detected_placement", ""),
                "reply": consultation["reply_text"],
                "recommended_remedy": consultation.get("recommended_remedy", ""),
                "timestamp": int(time.time()),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            replied_map[cid] = entry
            processed.append(entry)
            print(f" -> [SIMULATED REPLY] @{item['username']}: \"{consultation['reply_text'][:65]}...\"")

        history["replied_comments"] = replied_map
        self.save_reply_history(history)
        return processed


if __name__ == "__main__":
    agent = CommentAgent()
    sample = "Mera birth date 21 Oct 1995 hai, mere 7th house me Ketu hai. Shaadi me delay ho raha hai."
    print("Testing Comment Agent consultation...")
    res = agent.generate_consultation_reply(sample, commenter_name="ananya_v", topic="Marriage Delays")
    print("Detected:", res["detected_placement"])
    print("Reply:\n", res["reply_text"])
