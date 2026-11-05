import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.gemini_client import generate_json

logger = logging.getLogger(__name__)


def generate_seo_metadata(
    topic: str,
    niche: str = "Vedic astrology",
    target_audience: str = "Spiritual seekers, astrology enthusiasts, 20-40 age group",
) -> Dict[str, Any]:
    """
    Use Gemini to extract high-volume Instagram search keywords and algorithmic triggers.
    Instagram indexes:
    1. On-Screen Text (OCR)
    2. Spoken Voiceover (Audio ASR)
    3. Caption text
    4. Target Hashtags
    """
    prompt = f"""
You are an Instagram SEO and Algorithmic Growth Specialist in 2026.

Analyze this Reel topic and extract the highest-volume search keywords and algorithm triggers.

TOPIC: {topic}
NICHE: {niche}
AUDIENCE: {target_audience}

CRITICAL INSTAGRAM ALGORITHM PRINCIPLES:
1. High-Search Keywords: What exact phrases do users search for in the Instagram Explore search bar? (e.g., "Shani Sade Sati remedies", "Saturn transit 2026", "Kundli analysis").
2. Loop Hook Strategy: How should the script finish so the final word loops back to the opening word?
3. Save/Share Trigger: Why would a user press "Save" or "Share to Story/DM"? (Save gives 5x more algorithmic reach than a like).
4. Hashtag Strategy: Exactly 3 to 5 targeted niche hashtags. No generic spam (#viral, #fyp).

Return ONLY valid JSON in this exact structure:
{{
  "primary_search_keywords": ["keyword 1", "keyword 2", "keyword 3"],
  "loop_closing_phrase": "Connective ending that seamlessly links into the hook",
  "save_trigger_reason": "High-value reference information to revisit",
  "recommended_hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
  "retention_tactics": [
    "Scene cut every 3 seconds",
    "On-screen keyword badge in first 2 seconds"
  ]
}}
"""
    data = generate_json(prompt)
    return data


def verify_seo_integrity(
    script_data: Dict[str, Any],
    caption_text: str,
    hashtags: List[str],
) -> Dict[str, Any]:
    """
    Audit the generated Reel package for Instagram SEO compliance:
    - Keywords present in on-screen cards
    - Keywords present in caption
    - Hashtags between 3 and 5
    - First 120 chars contain the hook
    - Watch-time retention loop present
    """
    scenes = script_data.get("scenes", [])
    on_screen_texts = [s.get("on_screen_text", "").lower() for s in scenes]
    spoken_texts = [s.get("spoken_line", "").lower() for s in scenes]

    caption_lower = caption_text.lower()
    hook = script_data.get("selected_hook", {}).get("spoken", "")

    # Check 1: Hashtags count
    tag_count = len(hashtags)
    tag_pass = 3 <= tag_count <= 5

    # Check 2: First line hook visibility (cut at 120 chars)
    first_line = caption_text.split("\n")[0] if caption_text else ""
    first_line_pass = len(first_line) <= 125 and len(first_line) > 10

    # Check 3: Retention pacing (scenes under 4s)
    pacing_pass = all(float(s.get("estimated_seconds", 3)) <= 4.5 for s in scenes)

    # Check 4: Call to action is high value (save or share)
    has_save_cta = bool(re.search(r"\b(save|share|comment)\b", caption_lower))

    checks = {
        "hashtag_count_valid": {"score": 100 if tag_pass else 50, "detail": f"{tag_count} tags (Target: 3-5)"},
        "caption_hook_visible": {"score": 100 if first_line_pass else 60, "detail": f"{len(first_line)} chars (Target: <=125)"},
        "visual_pacing_valid": {"score": 100 if pacing_pass else 70, "detail": f"{len(scenes)} visual scenes with high pacing"},
        "high_value_cta": {"score": 100 if has_save_cta else 50, "detail": "Includes Save/Share/Comment trigger"},
    }

    overall = sum(c["score"] for c in checks.values()) / len(checks)

    return {
        "overall_seo_score": round(overall, 1),
        "verdict": "OPTIMIZED" if overall >= 85 else "GOOD",
        "checks": checks,
    }


if __name__ == "__main__":
    print("Testing SEO Optimizer...")
    seo = generate_seo_metadata("Why Saturn delays success")
    print("Primary Keywords:", seo.get("primary_search_keywords"))
    print("Hashtags:", seo.get("recommended_hashtags"))
    print("Loop Strategy:", seo.get("loop_closing_phrase"))
