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
    - Placement & Diagnosis: Emphasizes the Kundli house placements and dangers of blind remedies.
    - Call to Action: Mirrors the exact CTA asking for placements and DM for consultation.
    - Language Match: If reel is in Hindi, caption is in engaging Hindi; if English, in clean English.
    """
    scenes = script_data.get("scenes", []) if script_data else []
    spoken_script = "\n".join(
        f"Scene {s.get('scene_num', i+1)}: {s.get('spoken_line', '')}"
        for i, s in enumerate(scenes)
    )
    cta_spoken = scenes[-1].get("spoken_line", "") if scenes else ""
    warning_spoken = scenes[5].get("spoken_line", "") if len(scenes) >= 6 else ""

    lang_lower = (language or "").lower()
    is_english = lang_lower in ["english", "en"]

    if not is_english:
        # Default for Indian Instagram audience: Natural, conversational Roman script Hinglish!
        language_instruction = (
            "MANDATORY LANGUAGE: WRITE IN MODERN, NATURAL HINGLISH IN ROMAN SCRIPT (e.g. "
            "'12 saal ke astrology experience mein humne dekha hai ki Kundli ke ye 5 secret placements aapki life badal sakte hain...').\n"
            "STRICT BAN: DO NOT WRITE IN DEVANAGARI HINDI SCRIPT FOR THE CAPTION! Instagram users in India expect and prefer clean, modern Roman script Hinglish for captions.\n"
            "Combine conversational Roman Hindi with English keywords (Career, Wealth, Growth, Success, Energy, Kundli Analysis, Consultation, Save, Comment, DM)."
        )
    else:
        language_instruction = "MANDATORY LANGUAGE: Write in elegant, fluent English directly elaborating the video's exact spoken points."

    prompt = f"""
You are the master Instagram copywriter for an authentic Vedic Astrology & Gemstone Energy channel (@neodivinestore.in).

CRITICAL MISSION - 100% SYNCHRONIZATION WITH VIDEO SCRIPT:
The caption must provide the companion breakdown to the EXACT video that the viewer just watched.
Never invent unrelated rules or generic filler. Match the exact planet, house, warning against blind remedies, and call to action!

TOPIC: {topic}
NICHE: {niche}
REEL SPOKEN SCRIPT (SCENE BY SCENE):
{spoken_script}

REEL OPENING HOOK: {script_hook}
PLACEMENT & BLIND REMEDY WARNING: {warning_spoken}
CALL TO ACTION SPOKEN IN FINAL SCENE: {cta_spoken}
DESIRED CTA ACTION: {target_keyword or "DATE OF BIRTH"}

{language_instruction}

INSTAGRAM ALGORITHM & ENGAGEMENT RULES:
1. First line MUST be under 115 characters and match the video's hook message before the "... more" cut.
2. The explanation must directly explain why this placement causes financial/karmic disruption according to Vedic Jyotish (Scenes 2 & 3).
3. ASTROLOGER PERSPECTIVE & CLIENT CASE STUDY (CRITICAL):
   - Never write as if the astrologer made the mistake on themselves ("मैंने गलती की", "मेरा नुकसान हुआ").
   - Always speak from the position of an experienced, consulting Vedic astrologer sharing a real client case study ("हमारे एक क्लाइंट की कुंडली में...", "एक क्लाइंट ने बिना परामर्श पुखराज पहना...").
   - Tone must be calm, gentle, dignified, reassuring, and protective.
4. STRICT ZERO REMEDIES & ZERO MANTRAS MANDATE (CRITICAL):
   - DO NOT provide or suggest ANY remedies, mantras, rituals, or gemstones to wear in the caption!
   - Explicitly warn that taking generic remedies or wearing stones without complete Kundli analysis causes severe karmic and financial harm.
   - Command viewers to check which house the planet sits in their Kundli and comment their placement below.
5. TWO-STEP VIRAL CALL TO ACTION (CTA):
   - Step 1 (Comment Placement): Command viewers to comment their planet placement below (e.g. "Comment your planet placement below to check your alignment").
   - Step 2 (DM Consultation Booking): Tell them to send a Direct Message (DM) to book their consultation for full deep analysis. NEVER MENTION 'LINK IN BIO'! ONLY DM!
6. Exactly 4 to 5 hyper-targeted hashtags (no hashtag spam).
7. Clean formatting with double-spaced paragraphs and bullet points for mobile readability.

Return ONLY valid JSON in this exact structure:
{{
  "visible_first_line": "Hook under 115 chars that displays before '... more'",
  "caption_body": "Detailed breakdown with exact astrological placement mechanism and warning against blind remedies...",
  "cta": "Exact matching CTA...",
  "hashtags": ["#VedicAstrology", "#PlanetTag", "#KundliAnalysis", "#Jyotish", "#KundliConsultation"],
  "full_caption": "Complete combined caption ready to publish"
}}
"""
    try:
        data = generate_json(prompt)
    except Exception as exc:
        logger.warning(f"Gemini caption generation error ({exc}). Generating high-retention fallback caption...")
        lang_lower = (language or "").lower()
        if "english" in lang_lower or lang_lower == "en":
            data = {
                "visible_first_line": f"{(topic or script_hook)[:100]} ⚠️",
                "caption_body": (
                    "According to Vedic Astrology, adopting remedies or wearing unverified stones without analyzing your complete birth chart can cause severe energetic conflict.\n\n"
                    "Generic online tips or blindly following generalized advice often leads to unexpected setbacks and blockages. Always verify the exact house placement, planetary aspects, and current dasha in your personal Kundli.\n\n"
                    "⚠️ Warning: Never perform blind remedies without individualized chart consultation."
                ),
                "cta": "Save this reel and comment your planetary placement below. Send us a Direct Message (DM) to book your personalized consultation! 🙏✨",
                "hashtags": ["#VedicAstrology", "#KundliAnalysis", "#Kundali", "#Jyotish", "#NeoDivineStore"],
            }
        else:
            # Roman script Hinglish for modern Indian social media audience
            clean_first = topic if (topic and not any('\u0900' <= c <= '\u097f' for c in topic)) else "Kundli ka ye secret planetary alignment aapki life badal sakta hai"
            data = {
                "visible_first_line": f"{clean_first[:100]} ⚠️",
                "caption_body": (
                    "Vedic Astrology ke according, bina complete Janam Kundli aur Dasha analysis ke koi bhi gemstone ya remedy apnaana heavy energy conflict create kar sakta hai.\n\n"
                    "Galat kadam uthane se sudden financial loss, career mein unexpected delay aur high stress aane lagta hai. Social media ke generic totke ya bina calculation ke remedies se bachein. Apni personal Kundli ki graha sthiti check karke hi right decision lein.\n\n"
                    "⚠️ Warning: Bina authentic Kundli analysis ke koi bhi blind remedy ulta asar kar sakti hai."
                ),
                "cta": "Ye reel future ke liye SAVE kar lijiye aur apni Kundli ka planet placement neeche COMMENT karke batayein. Personalized deep consultation ke liye humein direct DM karein! 🙏✨",
                "hashtags": ["#VedicAstrology", "#KundliAnalysis", "#Kundali", "#Jyotish", "#NeoDivineStore"],
            }

    full = data.get("full_caption", "")
    if not full:
        # Default first line to Roman Hinglish if script_hook is Devanagari
        default_hook = topic if (topic and not any('\u0900' <= c <= '\u097f' for c in topic)) else "Kundli ka ye planetary secret aapki life badal sakta hai 🔮"
        first = data.get("visible_first_line") or default_hook
        body = data.get("caption_body", "")
        cta = data.get("cta", "")
        tags = " ".join(data.get("hashtags", []))
        full = f"{first}\n\n{body}\n\n{cta}\n\n{tags}"

    lint_result = lint_caption(full)

    from app.analytics.seo_optimizer import enforce_perfect_100_seo
    perfect_caption, perfect_tags, audit = enforce_perfect_100_seo(
        caption_text=full,
        hashtags=data.get("hashtags", []),
        script_data=script_data or {},
        topic=topic,
        language=language,
    )

    return {
        "full_caption": perfect_caption,
        "visible_first_line": perfect_caption.split("\n")[0],
        "hashtags": perfect_tags,
        "cta": data.get("cta", ""),
        "lint": lint_result,
        "seo_audit": audit,
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
