import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.gemini_client import generate_json
from config.settings import VENDOR_SKILLS_DIR

logger = logging.getLogger(__name__)

RUBRIC_FILE = VENDOR_SKILLS_DIR / "ig-profile" / "rubric.json"


def load_profile_rubric() -> Dict[str, Any]:
    with open(RUBRIC_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def audit_profile(
    name: str,
    handle: str,
    bio: str,
    link: Optional[str] = None,
    pinned_posts: Optional[str] = None,
    niche: str = "Vedic astrology",
) -> Dict[str, Any]:
    """
    Score and audit an Instagram profile against the 12-part rubric using Gemini.
    Replaces Claude's /ig-profile skill.
    """
    rubric_data = load_profile_rubric()

    prompt = f"""
You are an expert Instagram growth auditor evaluating an Instagram account profile against a 100-point rubric.

ACCOUNT DETAILS:
Name field: {name}
Handle: {handle}
Bio: {bio}
Link: {link or 'None'}
Pinned posts: {pinned_posts or 'None'}
Niche: {niche}

RUBRIC ITEMS TO EVALUATE:
{json.dumps(rubric_data['items'], ensure_ascii=False, indent=2)}

INSTRUCTIONS:
1. Score each rubric item honestly based on the criteria in "full_marks" and "common_fail".
2. Calculate the total score out of 100.
3. Provide prioritized, high-impact fixes in order of points lost.
4. Rewrite the Name Field, Bio First Line, and Bio Body to achieve 100/100 points.

Return ONLY valid JSON in this exact structure:
{{
  "total_score": 48,
  "verdict": "NEEDS_OPTIMIZATION",
  "scores": [
    {{
      "id": "name_field",
      "score": 6,
      "max_points": 12,
      "critique": "Wasted search opportunity"
    }}
  ],
  "top_three_fixes": [
    "Fix 1",
    "Fix 2",
    "Fix 3"
  ],
  "recommended_rewrite": {{
    "name_field": "Optimized Name | Niche keywords (under 30 chars)",
    "bio_line_1": "Who it's for & outcome",
    "bio_line_2": "Proof or offer",
    "cta_line": "Call to action pointing to link"
  }}
}}
"""
    result = generate_json(prompt)
    return result


if __name__ == "__main__":
    print("Testing Profile Audit Agent...")
    res = audit_profile(
        name="Astro Krishna",
        handle="astro_krishna",
        bio="Astrologer | Coffee lover | DM for readings",
        link="linktr.ee/krishna123",
        niche="Vedic astrology",
    )
    print("Total Score:", res["total_score"], "/ 100")
    print("Verdict:", res["verdict"])
    print("Rewrites:", res["recommended_rewrite"])
