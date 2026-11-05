import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.gemini_client import generate_json
from config.settings import STORAGE_DIR

logger = logging.getLogger(__name__)


def research_viral_ideas(
    niche: str = "Vedic astrology",
    count: int = 5,
    target_audience: str = "spiritual seekers, millennials interested in astrology and kundli",
) -> List[Dict[str, Any]]:
    """
    Research viral reel topics, outlier angles, and hook ideas using Gemini.
    Replaces Claude's /ig-viral with Gemini intelligence.
    """
    prompt = f"""
You are a viral social media strategist analyzing high-growth Instagram Reels in 2026.

NICHE: {niche}
TARGET AUDIENCE: {target_audience}
NUMBER OF IDEAS NEEDED: {count}

Identify {count} high-leverage Reel ideas that beat account medians by 3x-10x.
Focus on:
- Counter-intuitive truths ("Stop doing X")
- Hidden patterns ("Nobody tells you this")
- Concrete symptoms ("If this happened to you in 2026...")
- Specific life situations (career blocks, relationship karma, financial breakthrough)

For each idea, provide:
1. "topic": Concise topic title.
2. "why_it_works": Psychological trigger that stops scrolling.
3. "hook_angle": The bold opening claim.
4. "recommended_formula": One of (Contrarian, Nobody Tells You, Specific Loss, If You Are, Direct Question).
5. "visual_concept": Faceless visual aesthetic to pair with it.

Return ONLY valid JSON in this exact structure:
{{
  "ideas": [
    {{
      "topic": "Topic Name",
      "why_it_works": "Why it goes viral",
      "hook_angle": "Opening hook sentence",
      "recommended_formula": "Nobody Tells You",
      "visual_concept": "Cosmic planetary alignment"
    }}
  ]
}}
"""
    data = generate_json(prompt)
    ideas = data.get("ideas", [])

    # Save to storage for swipe file history
    swipe_file = STORAGE_DIR / "swipe_ideas.json"
    existing = []
    if swipe_file.exists():
        try:
            with open(swipe_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing.extend(ideas)
    with open(swipe_file, "w", encoding="utf-8") as f:
        json.dump(existing[-50:], f, indent=2, ensure_ascii=False)

    return ideas


if __name__ == "__main__":
    print("Testing Trend Agent with Gemini...")
    res = research_viral_ideas("Vedic Astrology", count=3)
    for i, item in enumerate(res, 1):
        print(f"\n{i}. {item['topic']} ({item['recommended_formula']})")
        print(f"   Hook: {item['hook_angle']}")
        print(f"   Why: {item['why_it_works']}")
