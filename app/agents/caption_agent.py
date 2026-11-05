import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import VENDOR_SKILLS_DIR
from app.agents.gemini_client import generate_json, generate_text

CAPTION_DIR = VENDOR_SKILLS_DIR / "ig-caption"
if str(CAPTION_DIR) not in sys.path:
    sys.path.insert(0, str(CAPTION_DIR))

import caption as caption_lint

logger = logging.getLogger(__name__)


def lint_caption(caption_text: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run the repository's caption.py heuristic checks on a caption.
    Returns:
    - visible_preview (first ~125 characters before Instagram's '... more')
    - checks (length, hashtags, mentions, links, emojis, concrete specifics, asks)
    - passed (boolean)
    """
    kw_list = keywords or []
    try:
        report = caption_lint.analyse(caption_text, keywords=kw_list)
        checks = report.get("checks", [])
        visible = caption_lint.visible_window(caption_text, 125)
        fails = [c for c in checks if c.get("status") == "FAIL"]
        return {
            "visible_preview": visible,
            "passed": len(fails) == 0,
            "checks": checks,
        }
    except Exception as exc:
        logger.warning(f"Caption linting error: {exc}")
        return {
            "visible_preview": caption_text[:125],
            "passed": True,
            "checks": [],
        }


def optimize_caption(
    topic: str,
    script_hook: str,
    draft_caption: str,
    niche: str = "Vedic astrology",
    target_keyword: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use Gemini to craft an Instagram caption engineered for the feed cut.
    Instagram truncates after ~125 chars. The first line must hook the reader.
    """
    prompt = f"""
You are an expert Instagram copywriter.

Optimize this Instagram Reel caption for maximum reach and conversion.

TOPIC: {topic}
NICHE: {niche}
REEL HOOK: {script_hook}
CURRENT DRAFT: {draft_caption}
KEYWORD TO CALL TO ACTION: {target_keyword or "GUIDE"}

CRITICAL INSTAGRAM ALGORITHM RULES:
1. The first line MUST be under 120 characters and act as an irresistible hook before the "... more" cut.
2. Include 1-2 concrete specifics (dates, names, practical steps).
3. Do NOT use fake urgency or cheesy emoji spam (max 2-3 clean emojis total).
4. Exactly 3-5 hyper-targeted niche hashtags (Instagram announced using fewer than 5 targeted hashtags performs best).
5. Add a clear CTA: "Comment {target_keyword or 'GUIDE'} and I'll DM you the breakdown" or "Save this for your next transit".
6. Never put hashtags in the first sentence.

Return ONLY valid JSON in this exact structure:
{{
  "visible_first_line": "Hook under 120 chars that shows before '... more'",
  "caption_body": "Engaging explanation and breakdown...",
  "cta": "Comment GUIDE to get...",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
  "full_caption": "Complete combined caption ready to paste"
}}
"""
    data = generate_json(prompt)
    full = data.get("full_caption", "")
    if not full:
        body = data.get("caption_body", "")
        tags = " ".join(data.get("hashtags", []))
        full = f"{data.get('visible_first_line', '')}\n\n{body}\n\n{data.get('cta', '')}\n\n{tags}"

    lint_result = lint_caption(full)

    return {
        "full_caption": full.strip(),
        "visible_first_line": data.get("visible_first_line", ""),
        "hashtags": data.get("hashtags", [])[:5],
        "cta": data.get("cta", ""),
        "lint": lint_result,
    }


if __name__ == "__main__":
    sample = "Stop doing this with Saturn in 2026. Here is why the planetary transit changes your career."
    print("Testing caption linting...")
    lint = lint_caption(sample)
    print("Visible:", lint["visible_preview"])
    print("Passed:", lint["passed"])
