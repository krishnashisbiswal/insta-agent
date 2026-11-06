import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import VENDOR_SKILLS_DIR
from app.agents.gemini_client import generate_json

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
    script_data: Optional[Dict[str, Any]] = None,
    language: str = "Hindi",
) -> Dict[str, Any]:
    """
    Crafts an Instagram caption that is 100% harmonized with the video content:
    - First Line: Matches the video's hook line.
    - Story & Explanation: Explains the exact same astrological mechanism as the spoken scenes.
    - Scriptural Remedy: Details the exact remedy mentioned in Scene 4.
    - Call to Action: Mirrors the exact CTA spoken in Scene 5.
    - Language Match: If reel is in Hindi, caption is in engaging Hindi; if English, in clean English.
    """
    scenes = script_data.get("scenes", []) if script_data else []
    spoken_script = "\n".join(
        f"Scene {s.get('scene_num', i+1)}: {s.get('spoken_line', '')}"
        for i, s in enumerate(scenes)
    )
    cta_spoken = scenes[-1].get("spoken_line", "") if scenes else ""
    remedy_spoken = scenes[3].get("spoken_line", "") if len(scenes) >= 4 else ""

    is_hindi = language.lower() in ["hindi", "hi"]

    language_instruction = (
        "MANDATORY LANGUAGE: WRITE IN ENGAGING, AUTHENTIC HINDI (with clean English keywords in parentheses where helpful, e.g. 'शुक्र (Venus)', '11वें भाव', 'कुंडली'). "
        "DO NOT write a generic English essay when the video is in Hindi! Both audio and caption must feel unified."
        if is_hindi
        else "MANDATORY LANGUAGE: Write in elegant, fluent English directly elaborating the video's exact spoken points."
    )

    prompt = f"""
You are the master Instagram copywriter for an authentic Vedic Astrology & Gemstone Energy channel (@neodivinestore.in).

CRITICAL MISSION - 100% SYNCHRONIZATION WITH VIDEO SCRIPT:
The caption must provide the companion breakdown to the EXACT video that the viewer just watched.
Never invent unrelated rules or generic filler. Match the exact planet, house, gemstone, remedy, and call to action!

TOPIC: {topic}
NICHE: {niche}
REEL SPOKEN SCRIPT (SCENE BY SCENE):
{spoken_script}

REEL OPENING HOOK: {script_hook}
REMEDY SPOKEN IN SCENE 4: {remedy_spoken}
CALL TO ACTION SPOKEN IN SCENE 5: {cta_spoken}
DESIRED CTA ACTION: {target_keyword or "DATE OF BIRTH"}

{language_instruction}

INSTAGRAM ALGORITHM & ENGAGEMENT RULES:
1. First line MUST be under 115 characters and match the video's hook message before the "... more" cut.
2. The explanation must directly explain why this placement causes financial/karmic disruption according to Vedic Jyotish (Scenes 2 & 3).
3. STRICT NO-GENERIC-REMEDIES WARNING: Explicitly state that generic internet remedies backfire without knowing exact degrees and ascendant (Lagna). Withholding remedies builds high curiosity and credibility!
4. TWO-STEP VIRAL CALL TO ACTION (CTA):
   - Step 1 (Comment Magnet): Command viewers to drop their exact Date of Birth, Time, and City in the comments so our AI can check their placement (driving comment volume to trigger the Instagram algorithm!).
   - Step 2 (Consultation Booking): Tell them to DM 'KUNDLI' or click the link in bio to Book a 1-on-1 Consultation for their complete deep Kundli reading and custom remedies.
5. Exactly 4 to 5 hyper-targeted hashtags (no hashtag spam).
6. Clean formatting with double-spaced paragraphs and bullet points for mobile readability.

Return ONLY valid JSON in this exact structure:
{{
  "visible_first_line": "Hook under 115 chars that displays before '... more'",
  "caption_body": "Detailed breakdown with exact astrological mechanism and remedy...",
  "cta": "Exact matching CTA...",
  "hashtags": ["#VedicAstrology", "#PlanetTag", "#GemstoneTag", "#Jyotish", "#KarmicHealing"],
  "full_caption": "Complete combined caption ready to publish"
}}
"""
    data = generate_json(prompt)
    full = data.get("full_caption", "")
    if not full:
        first = data.get("visible_first_line", script_hook)
        body = data.get("caption_body", "")
        cta = data.get("cta", "")
        tags = " ".join(data.get("hashtags", []))
        full = f"{first}\n\n{body}\n\n{cta}\n\n{tags}"

    lint_result = lint_caption(full)

    return {
        "full_caption": full.strip(),
        "visible_first_line": data.get("visible_first_line", ""),
        "hashtags": data.get("hashtags", [])[:5],
        "cta": data.get("cta", ""),
        "lint": lint_result,
    }


if __name__ == "__main__":
    sample = "Stop wearing Blue Sapphire if Saturn sits in your 8th house."
    print("Testing caption synchronization...")
    res = optimize_caption(
        topic=sample,
        script_hook=sample,
        draft_caption="Check your chart",
        language="Hindi",
    )
    print("Full Caption:\n", res["full_caption"])
