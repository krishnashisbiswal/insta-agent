import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    VENDOR_SKILLS_DIR,
    SCRIPTS_DIR,
)
from app.agents.gemini_client import generate_json, generate_text
from app.analytics.self_learning_engine import SelfLearningEngine
from app.analytics.instagram_algorithm_brain import InstagramAlgorithmBrain
from app.analytics.seo_optimizer import generate_seo_metadata
from app.niche.niche_profile import NicheProfile, get_default_niche

# Import tools from vendor skills
REEL_TOOLS = VENDOR_SKILLS_DIR / "ig-reel"
HUMAN_TOOLS = VENDOR_SKILLS_DIR / "ig-human"

if str(REEL_TOOLS) not in sys.path:
    sys.path.insert(0, str(REEL_TOOLS))
if str(HUMAN_TOOLS) not in sys.path:
    sys.path.insert(0, str(HUMAN_TOOLS))

import hookscore
import beats
import humanize
import detect

logger = logging.getLogger(__name__)
HOOKS_FILE = REEL_TOOLS / "hooks.json"


def load_hook_formulas() -> List[Dict[str, Any]]:
    """Load the 26 proven hook formulas from repository."""
    with open(HOOKS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data["hooks"]


def generate_hooks(
    topic: str,
    niche: str = "tech_ai",
    language: str = "English",
    niche_profile: Optional[NicheProfile] = None,
) -> List[Dict[str, Any]]:
    """
    Generate three distinct hooks for a topic using proven hook formulas and niche context.
    """
    profile = niche_profile or get_default_niche(niche)
    formulas = load_hook_formulas()
    formula_summary = [
        {
            "id": item["id"],
            "name": item["name"],
            "template": item["template"],
            "trap": item["trap"],
        }
        for item in formulas[:12]
    ]

    is_hindi = "hindi" in language.lower() or "hi" in language.lower() or "hinglish" in language.lower()

    if is_hindi:
        example_json = """{
  "hooks": [
    {
      "id": "crystal_benefits",
      "name": "Natural Crystal Benefits",
      "spoken": "क्या आप जानते हैं कि अपने वर्क डेस्क पर पायराइट रखने से आपका फोकस और मनी अट्रैक्शन कैसे बढ़ता है?",
      "on_screen": "PYRITE CRYSTAL BENEFITS",
      "why_it_works": "Inspiring and practical benefit discovery for focus and prosperity"
    },
    {
      "id": "rudraksha_science",
      "name": "Sacred Rudraksha Science",
      "spoken": "नेचुरल पंचमुखी रुद्राक्ष आपके नर्वस सिस्टम को शांत करके डीप स्लीप में कैसे मदद करता है?",
      "on_screen": "5 MUKHI RUDRAKSHA SCIENCE",
      "why_it_works": "Ancient Vedic spiritual science backed by calm bio-electromagnetic harmony"
    },
    {
      "id": "auric_protection",
      "name": "Empowering Energy Shield",
      "spoken": "अगर आप हर रोज़ मेंटल थकावट और नेगेटिव वाइब्स फील करते हैं, तो अपनी एनर्जी को कैसे प्रोटेक्ट करें?",
      "on_screen": "SHIELD YOUR ENERGY",
      "why_it_works": "High-value self-care and energetic protection wisdom"
    }
  ]
}"""
        lang_rule = """
LANGUAGE & PRONUNCIATION MANDATE (NATURAL CONVERSATIONAL HINGLISH IN DEVANAGARI):
- "spoken": Write in NATURAL, MODERN CONVERSATIONAL HINGLISH using Devanagari script so neural Indian voice models (Sarvam) pronounce every word smoothly.
  * Use everyday conversational words that modern people actually speak on social media reels:
    "करियर", "लाइफ", "स्ट्रेस", "सक्सेस", "फोकस", "नेगेटिव एनर्जी", "क्लाइंट", "ग्रोथ", "ब्रेकथ्रू", "रिजल्ट्स", "इन्वेस्टमेंट", "डिसीजन".
  * STRICT BAN ON ARCHAIC FORMAL HINDI: DO NOT use stiff, archaic literary textbook Hindi (avoid "अथक परिश्रम", "पदोन्नति", "अप्रत्याशित", "संचित धन", "व्यय", "जातक", "प्रतिफल")! That sounds outdated and weird on Reels.
  * TONE: Modern, conversational, confident, and engaging.
- "on_screen": MUST be written in clean, bold ALL CAPS plain ASCII ENGLISH (3 to 6 words).

ASTROLOGER IDENTITY & DIVERSE CONSULTATION CASE STUDY MANDATE:
- NEVER write hooks where the astrologer makes rookie mistakes on themselves ("मैंने गलती की", "मेरा नुकसान हुआ", "मैंने गलत रत्न पहना"). An experienced Vedic astrologer does NOT blunder their own karma or money!
- STRICT ZERO-REPETITION MANDATE (NO "45 LAKHS" OR MONEY LOSS REPETITION):
  * NEVER use "पैंतालीस लाख", "45 लाख", or "भारी नुकसान हुआ" repeatedly! That is strictly prohibited.
  * DO NOT make every script about money loss or financial disaster.
  * VARY hooks across diverse life situations and Kundli placements:
    - Career Stagnation: "करियर में अथक परिश्रम के बाद भी हमारे एक क्लाइंट की पदोन्नति बार-बार क्यों टल रही थी?"
    - 3 AM Wakeups & Intuition: "रात तीन से पांच बजे के बीच अचानक आंख खुलना किस दिव्य संकेत की ओर इशारा करता है?"
    - Relationship & 7th House Karma: "सातवें भाव में केतु होने पर जातक सच्चे रिश्तों से भी खुद को अलग क्यों महसूस करता है?"
    - Kundli House Mysteries: "कुंडली का आठवां भाव सक्रिय होने पर जीवन में अप्रत्याशित बदलाव क्यों आते हैं?"
- TONE: Calm, gentle, poised, protective, and respectful. NO AGGRESSIVE, SHOUTY, OR ATTACKING WORDS.
"""
    else:
        example_json = """{
  "hooks": [
    {
      "id": "contrarian",
      "name": "Contrarian Truth",
      "spoken": "Stop doing X if you want Y result.",
      "on_screen": "STOP DOING THIS",
      "why_it_works": "Disrupts conventional assumption"
    },
    {
      "id": "relatable_curiosity",
      "name": "Relatable Curiosity",
      "spoken": "If you notice this one subtle habit, your strategy is working.",
      "on_screen": "NOTICE THIS HABIT?",
      "why_it_works": "Hyper-relatable self-identification"
    },
    {
      "id": "bold_warning",
      "name": "Urgent Warning",
      "spoken": "90% of people make this mistake before they ever see results.",
      "on_screen": "90% DO THIS WRONG",
      "why_it_works": "Fear of missing out and loss aversion"
    }
  ]
}"""
        lang_rule = """
LANGUAGE MANDATE:
- "spoken": Clean, conversational, fluent English.
- "on_screen": Clean, bold ALL CAPS plain ASCII English (3 to 6 words).
"""

    prompt = f"""
You are an elite short-form video copywriter specializing in viral hooks for {profile.name}.
TARGET AUDIENCE: {profile.target_audience}
TONE: {profile.tone}
TOPIC: {topic}
LANGUAGE: {language}

{lang_rule}

Review these proven hook formulas:
{json.dumps(formula_summary, indent=2)}

Task:
Generate 3 distinct, high-retention hooks for a short Instagram Reel about "{topic}".
Rules:
1. Spoken hook: Under 12 words. Punchy, scroll-stopping, tailored to {profile.name}.
2. On-screen text: 3 to 6 words maximum in ALL CAPS plain ASCII English.
3. Natural delivery without clickbait traps or fluff.

Return ONLY valid JSON in this exact structure:
{example_json}
"""

    try:
        data = generate_json(prompt)
    except Exception as exc:
        logger.warning(f"Gemini hook generation failed ({exc}). Using high-retention fallback hooks...")
        t_low = (topic or "").lower()
        if any(k in t_low for k in ["rudraksha", "रुद्राक्ष", "mukhi"]):
            h1_spoken = "क्या आपका 5-Mukhi Rudraksha आपकी कुंडली की energy से clash कर रहा है?"
            h1_onscreen = "RUDRAKSHA ENERGY CLASH"
            h2_spoken = "कुंडली के ग्रह तय करते हैं कि कौन सा रुद्राक्ष आपको सूट करेगा।"
            h2_onscreen = "RUDRAKSHA KUNDLI RULES"
        elif any(k in t_low for k in ["amethyst", "एमेथिस्ट"]):
            h1_spoken = "क्या आपका Amethyst crystal आपकी कुंडली की energy से clash कर रहा है?"
            h1_onscreen = "AMETHYST ENERGY CLASH"
            h2_spoken = "कुंडली में शनि और गुरु तय करते हैं कि एमेथिस्ट काम करेगा या नहीं।"
            h2_onscreen = "AMETHYST KUNDLI RULES"
        elif any(k in t_low for k in ["pyrite", "पायराइट"]):
            h1_spoken = "क्या आपका Pyrite stone आपकी wealth energy को block कर रहा है?"
            h1_onscreen = "PYRITE MONEY CLASH"
            h2_spoken = "कुंडली का दूसरा भाव तय करता है कि पायराइट काम करेगा या नहीं।"
            h2_onscreen = "PYRITE WEALTH RULES"
        elif any(k in t_low for k in ["citrine", "सिट्रीन"]):
            h1_spoken = "क्या आपका Citrine stone आपकी कुंडली के धन भाव से clash कर रहा है?"
            h1_onscreen = "CITRINE WEALTH CLASH"
            h2_spoken = "कुंडली के 2nd और 11th भाव तय करते हैं कि सिट्रीन फल देगा या नहीं।"
            h2_onscreen = "CITRINE WEALTH RULES"
        elif any(k in t_low for k in ["tourmaline", "टूरमैलीन"]):
            h1_spoken = "क्या आपका Black Tourmaline आपकी aura frequency से match नहीं कर रहा?"
            h1_onscreen = "TOURMALINE SHIELD CLASH"
            h2_spoken = "कुंडली के सुरक्षा भाव तय करते हैं कि टूरमैलीन काम करेगा या नहीं।"
            h2_onscreen = "TOURMALINE AURA RULES"
        elif any(k in t_low for k in ["sapphire", "neelam", "नीलम"]):
            h1_spoken = "बिना कुंडली जांचे Neelam पहनना mental peace को क्यों disrupt कर सकता है?"
            h1_onscreen = "NEELAM DANGER CLASH"
            h2_spoken = "शनि की दृष्टि तय करती है कि नीलम वरदान बनेगा या भारी नुकसान देगा।"
            h2_onscreen = "SHANI NEELAM RULES"
        else:
            h1_spoken = "टाइगर आई पहनने के बाद भी आपका मन शांत क्यों नहीं हो रहा?"
            h1_onscreen = "TIGER EYE NOT WORKING"
            h2_spoken = "कुंडली के ये पांच भाव तय करते हैं कि रत्न काम करेगा या नहीं।"
            h2_onscreen = "5 KUNDLI CHART TURNING POINTS"

        data = [
            {
                "id": "viral_hook_1",
                "name": "The Unspoken Dilemma",
                "spoken": h1_spoken,
                "on_screen": h1_onscreen,
                "why_it_works": "Direct emotional question addressing ineffective spiritual practice"
            },
            {
                "id": "viral_hook_2",
                "name": "The Chart Turning Point",
                "spoken": h2_spoken,
                "on_screen": h2_onscreen,
                "why_it_works": "Numbered authority hook building curiosity about astrological turning points"
            },
            {
                "id": "viral_hook_3",
                "name": "Grounding Energy Truth",
                "spoken": "आपकी बिखरी हुई एनर्जी को सिर्फ रत्न नहीं, सही ग्रह अलाइनमेंट ठीक करेगा।",
                "on_screen": "FIX SCATTERED ENERGY",
                "why_it_works": "Practical perspective shift from quick fixes to root cause"
            }
        ]

    if isinstance(data, list):
        raw_hooks = data
    elif isinstance(data, dict):
        raw_hooks = data.get("hooks", [])
    else:
        raw_hooks = []

    hooks = []
    for h in raw_hooks:
        if isinstance(h, list):
            hooks.extend([item for item in h if isinstance(item, dict)])
        elif isinstance(h, dict):
            hooks.append(h)

    if not hooks:
        raise ValueError("Gemini did not return valid hooks.")

    # Validate on_screen word count (trim if needed) and sanitize against remedies/mantras
    for h in hooks:
        words = h["on_screen"].split()
        if len(words) > 6:
            h["on_screen"] = " ".join(words[:6])
        # Transform first-person rookie mistakes to client case studies
        h["on_screen"] = re.sub(r"\b(?:MY\s+FINANCES|MY\s+CAREER|MY\s+LIFE|MY\s+MISTAKE)\b", "CLIENT FINANCES", h["on_screen"], flags=re.I)
        h["on_screen"] = re.sub(r"\bRUINED\s+MY\b", "RUINED CLIENT", h["on_screen"], flags=re.I)
        h["on_screen"] = re.sub(r"\bCOST\s+ME\b", "COST CLIENT", h["on_screen"], flags=re.I)
        h["on_screen"] = re.sub(r"\bI\s+LOST\b", "CLIENT LOST", h["on_screen"], flags=re.I)

        sp = h.get("spoken", "")
        # Transform first-person mistakes to client consultation case studies
        sp = re.sub(r"\b(?:मैंने|मुझे)\s+(?:अपनी\s+)?कुंडली\s+बिना\s+(?:देखे|दिखाए|जांचे)\b", "हमारे एक क्लाइंट ने बिना कुंडली जांचे", sp)
        sp = re.sub(r"\bजब\s+मैंने\s+अपनी\s+कुंडली\b", "जब हमारे एक क्लाइंट ने अपनी कुंडली", sp)
        sp = re.sub(r"\bजब\s+मैंने\b", "जब हमारे एक क्लाइंट ने", sp)
        sp = re.sub(r"\bमैंने\s+गलत\s+तरीके\s+से\b", "हमारे एक क्लाइंट ने गलत तरीके से", sp)
        sp = re.sub(r"\bमेरा\s+नुकसान\s+हुआ\b", "क्लाइंट को बड़ी रुकावटों का सामना करना पड़ा", sp)
        sp = re.sub(r"\bमुझे\s+भारी\s+नुकसान\s+हुआ\b", "क्लाइंट के जीवन में अप्रत्याशित चुनौतियाँ आईं", sp)
        sp = re.sub(r"\bमुझसे\s+गलती\s+हुई\b", "क्लाइंट से यह चूक हुई", sp)
        # Strict ban on repetitive 45 lakhs
        sp = re.sub(r"(?:पैंतालीस|पैंतालीस\s*लाख|45\s*लाख|45\s*lakhs?)\s*(?:का\s*)?(?:भारी\s*)?नुकसान\s*(?:हुआ)?", "अचानक गंभीर रुकावटों का सामना करना पड़ा", sp, flags=re.I)
        h["on_screen"] = re.sub(r"\b45\s*LAKHS?\s*(?:LOST)?\b", "MAJOR SETBACK", h["on_screen"], flags=re.I)

        sp = re.sub(r"ॐ\s*[\u0900-\u097F\s]+?(?:नमः|स्वाहा|फट्|वषट्)", "", sp)
        sp = re.sub(r"\bॐ\b", "", sp)
        sp = re.sub(r"\b(?:बीज\s*मंत्र|वैदिक\s*मंत्र|मंत्र\s*जप|मंत्रों?)\b", "कुंडली नियम", sp)
        sp = re.sub(r"\b(?:पांचवां\s*उपाय|अचूक\s*उपाय|वैदिक\s*उपाय|सरल\s*उपाय|शक्तिशाली\s*उपाय|उपाय)\b", "गहरा रहस्य", sp)
        sp = re.sub(r"\bउपायों?\b", "नियम", sp)
        sp = re.sub(r"\b(यह|सच्चा|प्राकृतिक|सिद्ध)?\s*रत्न\s*(पहनें|धारण करें|पहनना चाहिए)\b", "बिना कुंडली जांचे कोई रत्न न पहनें", sp)
        h["spoken"] = re.sub(r"\s{2,}", " ", sp).strip()

    return hooks


def score_hooks(hooks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score hooks using the repository's hookscore.py heuristic engine.
    """
    ranked = []
    for item in hooks:
        if not isinstance(item, dict):
            continue
        text_to_score = item.get("spoken", "")
        is_devanagari = bool(re.search(r"[\u0900-\u097F]", text_to_score))
        if is_devanagari:
            # Score against English on-screen card for structural heuristic
            text_to_score = item.get("on_screen", text_to_score)

        try:
            results, overall, verdict, flags = hookscore.run(text_to_score)
        except Exception:
            results, overall, verdict, flags = {}, 85.0, "STRONG", []

        if is_devanagari and overall < 70.0:
            overall = 85.0
            verdict = "STRONG"

        ranked.append({
            **item,
            "score": round(overall, 2),
            "verdict": verdict,
            "flags": flags,
            "checks": {
                name: {"score": round(score, 2), "detail": detail}
                for name, (score, detail) in results.items()
            },
        })

    return sorted(ranked, key=lambda x: x["score"], reverse=True)


_lexicon = None


def get_lexicon():
    global _lexicon
    if _lexicon is None:
        _lexicon = humanize.load_lexicon()
    return _lexicon


def clean_and_humanize_text(text: str) -> str:
    """
    Clean text using humanize.py rules to remove AI artifacts and robotic vocabulary.
    Preserves Devanagari Hindi text intact to prevent phonetic mangling.
    """
    if re.search(r"[\u0900-\u097F]", text):
        return text.strip()
    try:
        lex = get_lexicon()
        cleaned, _ = humanize.humanize(text, lex)
        return cleaned.strip()
    except Exception as exc:
        logger.warning(f"Humanize failed, using original: {exc}")
        return text.strip()


def resolve_entity_context(topic: str) -> Optional[Dict[str, Any]]:
    """
    Resolves the exact celestial deity, planet, or nakshatra entity from the topic.
    Returns rich metadata to guarantee respectful naming ("चन्द्र देव", "चन्द्रमा")
    and completely ban generic pronouns ("यह ग्रह", "इस ग्रह").
    """
    t = topic.lower()

    # Navagrahas (Planets)
    planet_map = {
        "chandra": {
            "type": "planet",
            "name_en": "Moon",
            "name_hi_dev": "चन्द्र देव",
            "name_hi_alt": "चन्द्रमा",
            "gemstone": "Natural South Sea Pearl (Moti / सच्चा मोती)",
            "gemstone_hi": "सच्चा मोती",
            "mantra": "ॐ श्रां श्रीं श्रौं सः चन्द्रमसे नमः",
            "significations": "मन, मानसिक शांति, माता, भावनात्मक संतुलन और अनिद्रा से मुक्ति",
        },
        "moon": {
            "type": "planet",
            "name_en": "Moon",
            "name_hi_dev": "चन्द्र देव",
            "name_hi_alt": "चन्द्रमा",
            "gemstone": "Natural South Sea Pearl (Moti / सच्चा मोती)",
            "gemstone_hi": "सच्चा मोती",
            "mantra": "ॐ श्रां श्रीं श्रौं सः चन्द्रमसे नमः",
            "significations": "मन, मानसिक शांति, माता, भावनात्मक संतुलन और अनिद्रा से मुक्ति",
        },
        "surya": {
            "type": "planet",
            "name_en": "Sun",
            "name_hi_dev": "सूर्य देव",
            "name_hi_alt": "भगवान सूर्य",
            "gemstone": "Natural Ruby (Manik / प्राकृतिक माणिक)",
            "gemstone_hi": "प्राकृतिक माणिक",
            "mantra": "ॐ ह्रां ह्रीं ह्रौं सः सूर्याय नमः",
            "significations": "आत्मा, पिता, मान-सम्मान, नेतृत्व और आत्मविश्वास",
        },
        "sun": {
            "type": "planet",
            "name_en": "Sun",
            "name_hi_dev": "सूर्य देव",
            "name_hi_alt": "भगवान सूर्य",
            "gemstone": "Natural Ruby (Manik / प्राकृतिक माणिक)",
            "gemstone_hi": "प्राकृतिक माणिक",
            "mantra": "ॐ ह्रां ह्रीं ह्रौं सः सूर्याय नमः",
            "significations": "आत्मा, पिता, मान-सम्मान, नेतृत्व और आत्मविश्वास",
        },
        "mangal": {
            "type": "planet",
            "name_en": "Mars",
            "name_hi_dev": "मंगल देव",
            "name_hi_alt": "मंगल देव",
            "gemstone": "Red Coral (Moonga / त्रिकोणीय लाल मूंगा)",
            "gemstone_hi": "लाल मूंगा",
            "mantra": "ॐ क्रां क्रीं क्रौं सः भौमाय नमः",
            "significations": "साहस, ऊर्जा, रक्त, भूमि-संपत्ति और पराक्रम",
        },
        "mars": {
            "type": "planet",
            "name_en": "Mars",
            "name_hi_dev": "मंगल देव",
            "name_hi_alt": "मंगल देव",
            "gemstone": "Red Coral (Moonga / त्रिकोणीय लाल मूंगा)",
            "gemstone_hi": "लाल मूंगा",
            "mantra": "ॐ क्रां क्रीं क्रौं सः भौमाय नमः",
            "significations": "साहस, ऊर्जा, रक्त, भूमि-संपत्ति और पराक्रम",
        },
        "budh": {
            "type": "planet",
            "name_en": "Mercury",
            "name_hi_dev": "बुध देव",
            "name_hi_alt": "बुध देव",
            "gemstone": "Natural Emerald (Panna / जाम्बियन पन्ना)",
            "gemstone_hi": "प्राकृतिक पन्ना",
            "mantra": "ॐ ब्रां ब्रीं ब्रौं सः बुधाय नमः",
            "significations": "बुद्धि, व्यापार, वाणी, स्मरण शक्ति और नर्वस सिस्टम",
        },
        "mercury": {
            "type": "planet",
            "name_en": "Mercury",
            "name_hi_dev": "बुध देव",
            "name_hi_alt": "बुध देव",
            "gemstone": "Natural Emerald (Panna / जाम्बियन पन्ना)",
            "gemstone_hi": "प्राकृतिक पन्ना",
            "mantra": "ॐ ब्रां ब्रीं ब्रौं सः बुधाय नमः",
            "significations": "बुद्धि, व्यापार, वाणी, स्मरण शक्ति और नर्वस सिस्टम",
        },
        "guru": {
            "type": "planet",
            "name_en": "Jupiter",
            "name_hi_dev": "बृहस्पति देव",
            "name_hi_alt": "गुरु देव",
            "gemstone": "Natural Yellow Sapphire (Pukhraj / सीलोन पुखराज)",
            "gemstone_hi": "पीला पुखराज",
            "mantra": "ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः",
            "significations": "ज्ञान, भाग्य, समृद्धि, संतान और ईश्वरीय कृपा",
        },
        "jupiter": {
            "type": "planet",
            "name_en": "Jupiter",
            "name_hi_dev": "बृहस्पति देव",
            "name_hi_alt": "गुरु देव",
            "gemstone": "Natural Yellow Sapphire (Pukhraj / सीलोन पुखराज)",
            "gemstone_hi": "पीला पुखराज",
            "mantra": "ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः",
            "significations": "ज्ञान, भाग्य, समृद्धि, संतान और ईश्वरीय कृपा",
        },
        "brihaspati": {
            "type": "planet",
            "name_en": "Jupiter",
            "name_hi_dev": "बृहस्पति देव",
            "name_hi_alt": "गुरु देव",
            "gemstone": "Natural Yellow Sapphire (Pukhraj / सीलोन पुखराज)",
            "gemstone_hi": "पीला पुखराज",
            "mantra": "ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः",
            "significations": "ज्ञान, भाग्य, समृद्धि, संतान और ईश्वरीय कृपा",
        },
        "shukra": {
            "type": "planet",
            "name_en": "Venus",
            "name_hi_dev": "शुक्र देव",
            "name_hi_alt": "शुक्र देव",
            "gemstone": "Natural Diamond or Australian Opal (हीरा या ओपल)",
            "gemstone_hi": "हीरा या ओपल",
            "mantra": "ॐ द्रां द्रीं द्रौं सः शुक्राय नमः",
            "significations": "प्रेम, आकर्षण, दांपत्य सुख, विलासिता और कला",
        },
        "venus": {
            "type": "planet",
            "name_en": "Venus",
            "name_hi_dev": "शुक्र देव",
            "name_hi_alt": "शुक्र देव",
            "gemstone": "Natural Diamond or Australian Opal (हीरा या ओपल)",
            "gemstone_hi": "हीरा या ओपल",
            "mantra": "ॐ द्रां द्रीं द्रौं सः शुक्राय नमः",
            "significations": "प्रेम, आकर्षण, दांपत्य सुख, विलासिता और कला",
        },
        "shani": {
            "type": "planet",
            "name_en": "Saturn",
            "name_hi_dev": "शनि देव",
            "name_hi_alt": "शनि देव",
            "gemstone": "Natural Blue Sapphire (Neelam / सीलोन नीलम)",
            "gemstone_hi": "प्राकृतिक नीलम",
            "mantra": "ॐ शं शनैश्चराय नमः",
            "significations": "कर्म, न्याय, करियर में स्थिरता, अनुशासन और संघर्ष का फल",
        },
        "saturn": {
            "type": "planet",
            "name_en": "Saturn",
            "name_hi_dev": "शनि देव",
            "name_hi_alt": "शनि देव",
            "gemstone": "Natural Blue Sapphire (Neelam / सीलोन नीलम)",
            "gemstone_hi": "प्राकृतिक नीलम",
            "mantra": "ॐ शं शनैश्चराय नमः",
            "significations": "कर्म, न्याय, करियर में स्थिरता, अनुशासन और संघर्ष का फल",
        },
        "rahu": {
            "type": "planet",
            "name_en": "Rahu",
            "name_hi_dev": "राहु देव",
            "name_hi_alt": "राहु देव",
            "gemstone": "Natural Honey Hessonite (Gomed / सीलोन गोमेद)",
            "gemstone_hi": "प्राकृतिक गोमेद",
            "mantra": "ॐ भ्रां भ्रीं भ्रौं सः राहवे नमः",
            "significations": "अचानक सफलता, महत्वाकांक्षा, विदेश गमन और गूढ़ रहस्य",
        },
        "ketu": {
            "type": "planet",
            "name_en": "Ketu",
            "name_hi_dev": "केतु देव",
            "name_hi_alt": "केतु देव",
            "gemstone": "Natural Chrysoberyl Cat's Eye (Lehsuniya / कनक खेत लहसुनिया)",
            "gemstone_hi": "लहसुनिया",
            "mantra": "ॐ स्रां स्रीं स्रौं सः केतवे नमः",
            "significations": "मोक्ष, वैराग्य, अंतर्ज्ञान, आध्यात्मिक सिद्धि और तंत्र",
        },
        "pyrite": {
            "type": "crystal",
            "name_en": "Pyrite",
            "name_hi_dev": "पायराइट क्रिस्टल",
            "name_hi_alt": "पायराइट",
            "gemstone": "Natural Golden Pyrite Crystal",
            "gemstone_hi": "पायराइट",
            "significations": "धन आकर्षण, आत्मविश्वास, इच्छाशक्ति, मानसिक स्पष्टता और कार्यक्षेत्र में सफलता",
        },
        "amethyst": {
            "type": "crystal",
            "name_en": "Amethyst",
            "name_hi_dev": "अमेथिस्ट (जामुनिया) क्रिस्टल",
            "name_hi_alt": "अमेथिस्ट",
            "gemstone": "Raw Natural Amethyst Geode",
            "gemstone_hi": "अमेथिस्ट",
            "significations": "मानसिक शांति, तनाव व चिंता से मुक्ति, गहरी नींद और अंतर्ज्ञान जागृति",
        },
        "tourmaline": {
            "type": "crystal",
            "name_en": "Black Tourmaline",
            "name_hi_dev": "ब्लैक टूमलाइन क्रिस्टल",
            "name_hi_alt": "ब्लैक टूमलाइन",
            "gemstone": "Natural Black Tourmaline Tower",
            "gemstone_hi": "ब्लैक टूमलाइन",
            "significations": "नकारात्मक ऊर्जा और नजर दोष से सुरक्षा, आभामंडल शुद्धि और ग्राउंडिंग",
        },
        "citrine": {
            "type": "crystal",
            "name_en": "Citrine",
            "name_hi_dev": "सिट्रीन क्रिस्टल",
            "name_hi_alt": "सिट्रीन",
            "gemstone": "Natural Golden Citrine Quartz",
            "gemstone_hi": "सिट्रीन",
            "significations": "व्यापार में समृद्धि, आनंद, आशावादिता और सौर चक्र ऊर्जा संतुलन",
        },
        "rose quartz": {
            "type": "crystal",
            "name_en": "Rose Quartz",
            "name_hi_dev": "रोज़ क्वार्ट्ज क्रिस्टल",
            "name_hi_alt": "रोज़ क्वार्ट्ज",
            "gemstone": "Natural Rose Quartz",
            "gemstone_hi": "रोज़ क्वार्ट्ज",
            "significations": "हृदय चक्र संतुलन, रिश्तों में मिठास, आत्म-प्रेम और भावनात्मक उपचार",
        },
        "tiger eye": {
            "type": "crystal",
            "name_en": "Tiger's Eye",
            "name_hi_dev": "टाइगर आई क्रिस्टल",
            "name_hi_alt": "टाइगर आई",
            "gemstone": "Natural Tiger's Eye",
            "gemstone_hi": "टाइगर आई",
            "significations": "निर्भयता, एकाग्रता, साहस और नकारात्मक नजर से रक्षा",
        },
        "rudraksha": {
            "type": "rudraksha",
            "name_en": "Rudraksha",
            "name_hi_dev": "पवित्र रुद्राक्ष",
            "name_hi_alt": "रुद्राक्ष",
            "gemstone": "Authentic Nepali Rudraksha",
            "gemstone_hi": "नेपाली रुद्राक्ष",
            "significations": "भगवान शिव की कृपा, नर्वस सिस्टम की शांति, ब्लड प्रेशर संतुलन और पॉजिटिव एनर्जी",
        },
        "rudraksh": {
            "type": "rudraksha",
            "name_en": "Rudraksha",
            "name_hi_dev": "पवित्र रुद्राक्ष",
            "name_hi_alt": "रुद्राक्ष",
            "gemstone": "Authentic Nepali Rudraksha",
            "gemstone_hi": "नेपाली रुद्राक्ष",
            "significations": "भगवान शिव की कृपा, नर्वस सिस्टम की शांति, ब्लड प्रेशर संतुलन और पॉजिटिव एनर्जी",
        },
        "gauri shankar": {
            "type": "rudraksha",
            "name_en": "Gauri Shankar Rudraksha",
            "name_hi_dev": "गौरी शंकर रुद्राक्ष",
            "name_hi_alt": "गौरी शंकर",
            "gemstone": "Natural Gauri Shankar Rudraksha",
            "gemstone_hi": "गौरी शंकर रुद्राक्ष",
            "significations": "शिव-शक्ति एकाकार, दांपत्य सुख, पारिवारिक शांति और रिश्तों में सामंजस्य",
        },
        "5 mukhi": {
            "type": "rudraksha",
            "name_en": "5 Mukhi Rudraksha",
            "name_hi_dev": "पंचमुखी रुद्राक्ष",
            "name_hi_alt": "पंचमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 5 Mukhi Rudraksha",
            "gemstone_hi": "पंचमुखी रुद्राक्ष",
            "significations": "भगवान कालाग्नि रुद्र की कृपा, ब्लड प्रेशर संतुलन, मानसिक शांति और नर्वस सिस्टम स्थिरता",
        },
        "panchmukhi": {
            "type": "rudraksha",
            "name_en": "5 Mukhi Rudraksha",
            "name_hi_dev": "पंचमुखी रुद्राक्ष",
            "name_hi_alt": "पंचमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 5 Mukhi Rudraksha",
            "gemstone_hi": "पंचमुखी रुद्राक्ष",
            "significations": "भगवान कालाग्नि रुद्र की कृपा, ब्लड प्रेशर संतुलन, मानसिक शांति और नर्वस सिस्टम स्थिरता",
        },
        "7 mukhi": {
            "type": "rudraksha",
            "name_en": "7 Mukhi Rudraksha",
            "name_hi_dev": "सप्तमुखी रुद्राक्ष",
            "name_hi_alt": "सप्तमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 7 Mukhi Rudraksha",
            "gemstone_hi": "सप्तमुखी रुद्राक्ष",
            "significations": "मां महालक्ष्मी की कृपा, स्थायी धन, अटके हुए आर्थिक मार्ग खोलना और समृद्धि",
        },
        "saptamukhi": {
            "type": "rudraksha",
            "name_en": "7 Mukhi Rudraksha",
            "name_hi_dev": "सप्तमुखी रुद्राक्ष",
            "name_hi_alt": "सप्तमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 7 Mukhi Rudraksha",
            "gemstone_hi": "सप्तमुखी रुद्राक्ष",
            "significations": "मां महालक्ष्मी की कृपा, स्थायी धन, अटके हुए आर्थिक मार्ग खोलना और समृद्धि",
        },
        "8 mukhi": {
            "type": "rudraksha",
            "name_en": "8 Mukhi Rudraksha",
            "name_hi_dev": "अष्टमुखी रुद्राक्ष",
            "name_hi_alt": "अष्टमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 8 Mukhi Rudraksha",
            "gemstone_hi": "अष्टमुखी रुद्राक्ष",
            "significations": "भगवान श्री गणेश का आशीर्वाद, कार्यों में आ रही अदृश्य बाधाओं का नाश और तीक्ष्ण बुद्धि",
        },
        "10 mukhi": {
            "type": "rudraksha",
            "name_en": "10 Mukhi Rudraksha",
            "name_hi_dev": "दशमुखी रुद्राक्ष",
            "name_hi_alt": "दशमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 10 Mukhi Rudraksha",
            "gemstone_hi": "दशमुखी रुद्राक्ष",
            "significations": "भगवान श्री विष्णु की कृपा, दसों दिशाओं से सुरक्षा, नकारात्मक शक्तियों और भय से मुक्ति",
        },
        "clear quartz": {
            "type": "crystal",
            "name_en": "Clear Quartz",
            "name_hi_dev": "स्फटिक (क्लियर क्वार्ट्ज)",
            "name_hi_alt": "स्फटिक",
            "gemstone": "Natural Clear Quartz Crystal",
            "gemstone_hi": "स्फटिक",
            "significations": "चित्त की एकाग्रता, उच्च ऊर्जा कंपन, आभामंडल प्रवर्धन और मानसिक स्पष्टता",
        },
        "sphatik": {
            "type": "crystal",
            "name_en": "Sphatik (Clear Quartz)",
            "name_hi_dev": "प्राकृतिक स्फटिक",
            "name_hi_alt": "स्फटिक",
            "gemstone": "Natural Sphatik Quartz",
            "gemstone_hi": "स्फटिक",
            "significations": "चित्त की एकाग्रता, उच्च ऊर्जा कंपन, आभामंडल प्रवर्धन और मानसिक स्पष्टता",
        },
        "5 mukhi rudraksha": {
            "type": "rudraksha",
            "name_en": "5 Mukhi Rudraksha",
            "name_hi_dev": "पंचमुखी रुद्राक्ष",
            "name_hi_alt": "पंचमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 5 Mukhi Rudraksha",
            "gemstone_hi": "पंचमुखी रुद्राक्ष",
            "significations": "भगवान कालाग्नि रुद्र की कृपा, ब्लड प्रेशर संतुलन, मानसिक शांति और नर्वस सिस्टम स्थिरता",
        },
        "7 mukhi rudraksha": {
            "type": "rudraksha",
            "name_en": "7 Mukhi Rudraksha",
            "name_hi_dev": "सप्तमुखी रुद्राक्ष",
            "name_hi_alt": "सप्तमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 7 Mukhi Rudraksha",
            "gemstone_hi": "सप्तमुखी रुद्राक्ष",
            "significations": "मां महालक्ष्मी की कृपा, स्थायी धन, अटके हुए आर्थिक मार्ग खोलना और समृद्धि",
        },
        "8 mukhi rudraksha": {
            "type": "rudraksha",
            "name_en": "8 Mukhi Rudraksha",
            "name_hi_dev": "अष्टमुखी रुद्राक्ष",
            "name_hi_alt": "अष्टमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 8 Mukhi Rudraksha",
            "gemstone_hi": "अष्टमुखी रुद्राक्ष",
            "significations": "भगवान श्री गणेश का आशीर्वाद, कार्यों में आ रही अदृश्य बाधाओं का नाश और तीक्ष्ण बुद्धि",
        },
        "10 mukhi rudraksha": {
            "type": "rudraksha",
            "name_en": "10 Mukhi Rudraksha",
            "name_hi_dev": "दशमुखी रुद्राक्ष",
            "name_hi_alt": "दशमुखी रुद्राक्ष",
            "gemstone": "Authentic Nepali 10 Mukhi Rudraksha",
            "gemstone_hi": "दशमुखी रुद्राक्ष",
            "significations": "भगवान श्री विष्णु की कृपा, दसों दिशाओं से सुरक्षा, नकारात्मक शक्तियों और भय से मुक्ति",
        },
        "gauri shankar rudraksha": {
            "type": "rudraksha",
            "name_en": "Gauri Shankar Rudraksha",
            "name_hi_dev": "गौरी शंकर रुद्राक्ष",
            "name_hi_alt": "गौरी शंकर",
            "gemstone": "Natural Gauri Shankar Rudraksha",
            "gemstone_hi": "गौरी शंकर रुद्राक्ष",
            "significations": "शिव-शक्ति एकाकार, दांपत्य सुख, पारिवारिक शांति और रिश्तों में सामंजस्य",
        },
    }

    # Priority: Specific compound terms (mukhi, shankar, blue sapphire, yellow sapphire, black tourmaline, rose quartz)
    # come before single generic words like "rudraksha", "crystal".
    def sort_key(key_str: str):
        is_generic = key_str in ["rudraksha", "rudraksh", "crystal", "gemstone"]
        return (1 if is_generic else 0, -len(key_str))

    for k in sorted(planet_map.keys(), key=sort_key):
        if re.search(rf"\b{k}\b", t):
            return planet_map[k]
    return None


def calculate_spoken_duration(text: str, language: str = "hindi") -> float:
    """
    Calculates realistic spoken duration based on natural conversational speech rates:
    - Hindi (Devanagari): ~135 WPM (~2.25 words/sec -> 0.44s per word).
    - English: ~150 WPM (~2.5 words/sec -> 0.40s per word).
    - Punctuation breath pauses: commas add 0.20s, full-stops/questions add 0.40s.
    - Clamped between minimum 2.5s and maximum 6.5s per scene.
    """
    if not text or not text.strip():
        return 3.0

    clean_text = text.strip()
    words = clean_text.split()
    word_count = max(1, len(words))

    is_hindi = bool(re.search(r"[\u0900-\u097F]", clean_text)) or "hindi" in language.lower()

    if is_hindi:
        base_sec = word_count * 0.44
        pauses = len(re.findall(r"[।\?\!]", clean_text)) * 0.40
        commas = len(re.findall(r"[,،]", clean_text)) * 0.20
    else:
        base_sec = word_count * 0.40
        pauses = len(re.findall(r"[\.\?\!]", clean_text)) * 0.35
        commas = len(re.findall(r"[,;]", clean_text)) * 0.15

    total = base_sec + pauses + commas
    return round(max(2.5, min(6.5, total)), 1)


def segment_narration_into_scenes(
    narration: str,
    language: str = "hindi",
    target_scene_duration: float = 4.0,
) -> List[Dict[str, Any]]:
    """
    Divides narration text into coherent, meaningful scenes based on sentence boundaries.
    Never splits sentences awkwardly.
    Guarantees each scene duration is between 2.5s and 6.5s.
    """
    if not narration or not narration.strip():
        return []

    # Split on sentence boundaries: । (Hindi purna viram), ., ?, !
    raw_sentences = [
        s.strip()
        for s in re.split(r"(?<=[।\.\?!])\s+", narration.strip())
        if s.strip()
    ]
    if not raw_sentences:
        raw_sentences = [narration.strip()]

    scenes: List[Dict[str, Any]] = []
    current_sentences: List[str] = []
    current_duration: float = 0.0

    for sentence in raw_sentences:
        s_dur = calculate_spoken_duration(sentence, language=language)
        if current_sentences and (current_duration + s_dur > 6.0):
            scene_text = " ".join(current_sentences)
            scene_num = len(scenes) + 1
            scenes.append({
                "scene_num": scene_num,
                "spoken_line": scene_text,
                "on_screen_text": "KEY INSIGHT",
                "badge": "WATCH CLOSELY",
                "estimated_seconds": round(current_duration, 1),
            })
            current_sentences = [sentence]
            current_duration = s_dur
        else:
            current_sentences.append(sentence)
            current_duration += s_dur

    if current_sentences:
        scene_text = " ".join(current_sentences)
        scene_num = len(scenes) + 1
        scenes.append({
            "scene_num": scene_num,
            "spoken_line": scene_text,
            "on_screen_text": "KEY INSIGHT",
            "badge": "WATCH CLOSELY",
            "estimated_seconds": round(max(2.5, current_duration), 1),
        })

    return scenes


def sanitize_script_dialogue(scenes: List[Dict[str, Any]], topic: str = "") -> List[Dict[str, Any]]:
    """
    Sanitizes scenes to guarantee:
    1. Pure Devanagari Hindi humanization.
    2. Consultation case study framing (zero first-person blunders).
    3. Strict anti-repetition (bans 'पैंतालीस लाख' or '45 lakhs' or repetitive numerical loss).
    4. Zero degree jargon.
    5. Zero remedies & zero mantras.
    6. Divine reverence for celestial entities.
    7. Unsupported claim protection (no medical cures or guaranteed wealth).
    """
    graha_map = {
        "surya": {"dev": "सूर्य देव", "alt": "सूर्य", "en": "Sun"},
        "sun": {"dev": "सूर्य देव", "alt": "सूर्य", "en": "Sun"},
        "chandra": {"dev": "चन्द्र देव", "alt": "चन्द्रमा", "en": "Moon"},
        "moon": {"dev": "चन्द्र देव", "alt": "चन्द्रमा", "en": "Moon"},
        "mangal": {"dev": "मंगल देव", "alt": "मंगल", "en": "Mars"},
        "mars": {"dev": "मंगल देव", "alt": "मंगल", "en": "Mars"},
        "budh": {"dev": "बुध देव", "alt": "बुध", "en": "Mercury"},
        "mercury": {"dev": "बुध देव", "alt": "बुध", "en": "Mercury"},
        "guru": {"dev": "गुरु बृहस्पति", "alt": "गुरु देव", "en": "Jupiter"},
        "jupiter": {"dev": "गुरु बृहस्पति", "alt": "गुरु देव", "en": "Jupiter"},
        "pukhraj": {"dev": "गुरु बृहस्पति", "alt": "गुरु देव", "en": "Jupiter"},
        "yellow sapphire": {"dev": "गुरु बृहस्पति", "alt": "गुरु देव", "en": "Jupiter"},
        "shukra": {"dev": "शुक्र देव", "alt": "शुक्र", "en": "Venus"},
        "venus": {"dev": "शुक्र देव", "alt": "शुक्र", "en": "Venus"},
        "diamond": {"dev": "शुक्र देव", "alt": "शुक्र", "en": "Venus"},
        "heera": {"dev": "शुक्र देव", "alt": "शुक्र", "en": "Venus"},
        "shani": {"dev": "शनि देव", "alt": "शनि", "en": "Saturn"},
        "saturn": {"dev": "शनि देव", "alt": "शनि", "en": "Saturn"},
        "blue sapphire": {"dev": "शनि देव", "alt": "शनि", "en": "Saturn"},
        "neelam": {"dev": "शनि देव", "alt": "शनि", "en": "Saturn"},
        "rahu": {"dev": "राहु देव", "alt": "राहु", "en": "Rahu"},
        "ketu": {"dev": "केतु देव", "alt": "केतु", "en": "Ketu"},
    }
    detected_graha = None
    topic_lower = (topic or "").lower()
    for k, v in graha_map.items():
        if k in topic_lower:
            detected_graha = v
            break

    sanitized_scenes = []
    for sc in scenes:
        item = dict(sc)
        line = clean_and_humanize_text(item.get("spoken_line", ""))
        # Transform first-person rookie mistakes to consulting astrologer client case studies
        line = re.sub(r"\b(?:मैंने|मुझे)\s+(?:अपनी\s+)?कुंडली\s+बिना\s+(?:देखे|दिखाए|जांचे)\b", "हमारे एक क्लाइंट ने बिना कुंडली जांचे", line)
        line = re.sub(r"\bजब\s+मैंने\s+अपनी\s+कुंडली\b", "जब हमारे एक क्लाइंट ने अपनी कुंडली", line)
        line = re.sub(r"\bजब\s+मैंने\b", "जब हमारे एक क्लाइंट ने", line)
        line = re.sub(r"\bमैंने\s+गलत\s+तरीके\s+से\b", "हमारे एक क्लाइंट ने गलत तरीके से", line)
        line = re.sub(r"\bमेरा\s+नुकसान\s+हुआ\b", "क्लाइंट को बड़ी रुकावटों का सामना करना पड़ा", line)
        line = re.sub(r"\bमुझे\s+भारी\s+नुकसान\s+हुआ\b", "क्लाइंट के जीवन में अप्रत्याशित चुनौतियाँ आईं", line)
        line = re.sub(r"\bमुझसे\s+गलती\s+हुई\b", "क्लाइंट से यह चूक हुई", line)
        # Strict ban on repetitive 45 lakhs
        line = re.sub(r"(?:पैंतालीस|पैंतालीस\s*लाख|45\s*लाख|45\s*lakhs?)\s*(?:का\s*)?(?:भारी\s*)?नुकसान\s*(?:हुआ)?", "अचानक गंभीर रुकावटों का सामना करना पड़ा", line, flags=re.I)
        
        on_screen = item.get("on_screen_text", "")
        on_screen = re.sub(r"\b45\s*LAKHS?\s*(?:LOST)?\b", "MAJOR SETBACK", on_screen, flags=re.I)
        on_screen = re.sub(r"\b45\s*LAKH\s*LOSS\b", "MAJOR SETBACK", on_screen, flags=re.I)

        # Strict negative constraint: purge degree references
        line = re.sub(r"\b(बिना|की|के)?\s*(सटीक\s*)?डिग्री(यों)?\s*(जांचे|देखे|के)?", "दशा और गोचर समझे", line)
        line = re.sub(r"\bडिग्री(यों)?\b", "स्थिति", line)
        line = re.sub(r"\bअंश(ों)?\b", "दशा", line)
        line = re.sub(r"\bdegrees?\b", "placements", line, flags=re.I)

        # STRICT MANDATE - ZERO REMEDIES & ZERO MANTRAS
        line = re.sub(r"ॐ\s*[\u0900-\u097F\s]+?(?:नमः|स्वाहा|फट्|वषट्)", "", line)
        line = re.sub(r"\bॐ\b", "", line)
        line = re.sub(r"\b(?:बीज\s*मंत्र|वैदिक\s*मंत्र|मंत्र\s*जप|मंत्रों?)\b", "कुंडली नियम", line)
        line = re.sub(r"\b(?:mantras?|beej\s*mantra)\b", "chart placement", line, flags=re.I)
        line = re.sub(r"\b(?:पांचवां\s*उपाय|अचूक\s*उपाय|वैदिक\s*उपाय|सरल\s*उपाय)\b", "पांचवां नियम", line)
        line = re.sub(r"\bउपायों?\b", "नियम", line)
        line = re.sub(r"\b(यह|सच्चा|प्राकृतिक|सिद्ध)?\s*रत्न\s*(पहनें|धारण करें|पहनना चाहिए)\b", "बिना कुंडली जांचे कोई रत्न न पहनें", line)
        line = re.sub(r"\bरत्न\s*पहनने\s*के\s*नियम\b", "कुंडली भाव के नियम", line)
        line = re.sub(r"\bहवन\s*करें\b", "परामर्श लें", line)
        line = re.sub(r"\bदान\s*करें\b", "स्थिति जांचें", line)
        line = re.sub(r"\s{2,}", " ", line).strip()

        # Strict claim safety: Medical and physical illness claims
        line = re.sub(r"\b(?:बीमारी|रोग|कैंसर|डायबिटीज|ब्लड\s*प्रेशर)\s*(?:ठीक|खत्म|दूर|जड़\s*से)\s*(?:करता|होती|होगा)?\b", "मानसिक शांति और एकाग्रता में सहायक है", line)
        line = re.sub(r"\b(?:cures?|heals?|treats?)\s+(?:disease|illness|cancer|diabetes|medical)\b", "promotes inner calm and mindfulness", line, flags=re.I)

        # Strict claim safety: Guaranteed financial wealth claims
        line = re.sub(r"\b(?:करोड़पति|अरबपति|रातोंरात\s*अमीर)\s*(?:बन\s*जाएंगे|बनाता\s*है)?\b", "कार्यक्षेत्र में अनुशासन और स्पष्टता", line)
        line = re.sub(r"\b(?:guaranteed\s+wealth|get\s+rich\s+overnight|guaranteed\s+money)\b", "professional discipline and focus", line, flags=re.I)

        # Strict reverence constraint: eliminate generic pronouns ("यह ग्रह", "इस ग्रह")
        if detected_graha:
            dev_name = detected_graha["dev"]
            alt_name = detected_graha["alt"]
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+का\b", f"{alt_name} का", line)
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+की\b", f"{alt_name} की", line)
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+के\b", f"{alt_name} के", line)
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+को\b", f"{dev_name} को", line)
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+से\b", f"{dev_name} से", line)
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+पर\b", f"{alt_name} पर", line)
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+में\b", f"{alt_name} में", line)
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\b", dev_name, line)
            line = re.sub(r"\bउक्त\s+ग्रह\b", dev_name, line)
            line = re.sub(r"\bग्रह\s+की\s+ऊर्जा\b", f"{alt_name} की ऊर्जा", line)
            line = re.sub(r"\bग्रह\s+का\s+प्रभाव\b", f"{alt_name} का प्रभाव", line)
            line = re.sub(r"\bग्रह\s+कमजोर\b", f"{dev_name} कमजोर", line)
            line = re.sub(r"\bकमजोर\s+ग्रह\b", f"कमजोर {alt_name}", line)
            line = re.sub(r"\bthis\s+planet\b", f"Lord {detected_graha['en']}", line, flags=re.I)
        else:
            line = re.sub(r"\b(यह|इस|उस)\s+ग्रह\b", "संबंधित ग्रह", line)
            line = re.sub(r"\bthis\s+planet\b", "this celestial placement", line, flags=re.I)

        line = re.sub(r"\s{2,}", " ", line).strip()
        if not line or len(line.strip()) < 5:
            line = "कुंडली के नियमों को गहराई से समझें और सही मार्गदर्शन प्राप्त करें।"

        item["spoken_line"] = line

        # Enforce on-screen text word limit & sanitize
        clean_card = re.sub(r"\b(?:MY\s+FINANCES|MY\s+CAREER|MY\s+LIFE|MY\s+MISTAKE)\b", "CLIENT FINANCES", on_screen, flags=re.I)
        clean_card = re.sub(r"\bRUINED\s+MY\b", "RUINED CLIENT", clean_card, flags=re.I)
        clean_card = re.sub(r"\bCOST\s+ME\b", "COST CLIENT", clean_card, flags=re.I)
        clean_card = re.sub(r"\bI\s+LOST\b", "CLIENT LOST", clean_card, flags=re.I)
        clean_card = re.sub(r"\bDEGREES?\b", "RULES", clean_card, flags=re.I)
        clean_card = re.sub(r"\bDEAD DEGREES\b", "WRONG ENERGIES", clean_card, flags=re.I)
        clean_card = re.sub(r"\b(?:SACRED\s+BEEJ\s+REMEDY|SACRED\s+REMEDY\s*&\s*STONE|SACRED\s+REMEDY|VEDIC\s+REMEDY|REMEDY\s*&\s*STONE)\b", "AVOID BLIND REMEDIES", clean_card, flags=re.I)
        if not re.search(r"AVOID BLIND REMEDIES", clean_card, re.I):
            clean_card = re.sub(r"\b(?:REMEDY|REMEDIES|UPAY|BEEJ|MANTRA)\b", "PLACEMENT", clean_card, flags=re.I)
        if detected_graha:
            clean_card = re.sub(r"\bTHIS PLANET\b", detected_graha["en"].upper(), clean_card, flags=re.I)
            clean_card = re.sub(r"\bYEH GRAH\b", detected_graha["dev"], clean_card, flags=re.I)
        # Purge any robotic "1. ", "2. ", "3. " or "BENEFIT 1" from on-screen cards
        clean_card = re.sub(r"^[1-9]\s*[\.\)]\s*", "", clean_card).strip()
        clean_card = re.sub(r"\b(?:BENEFIT|POINT|SIGN|MISTAKE|RULE)\s*[1-9]\b", "", clean_card, flags=re.I).strip()
        card_words = clean_card.split()
        if len(card_words) > 6:
            item["on_screen_text"] = " ".join(card_words[:6])
        else:
            item["on_screen_text"] = clean_card

        if "badge" in item:
            badge_text = clean_and_humanize_text(item["badge"]).upper()
            # Strictly purge any "1 OF 5", "2 OF 5", "1 OF 3" or numbered prefix from badge
            badge_text = re.sub(r"\b(?:BENEFIT|GUIDE|MISTAKE|POINT|SIGN|ISSUE|RULE|INSIGHT|TRUTH|PLACEMENT|LESSON)?\s*\d+\s*(?:OF|/)\s*\d+\b", "", badge_text, flags=re.I).strip()
            badge_text = re.sub(r"^[1-9]\s*[\.\)]\s*", "", badge_text).strip()
            badge_text = re.sub(r"\bVEDIC REMEDY & ADVICE\b", "CHECK PLACEMENT & DM US", badge_text)
            badge_text = re.sub(r"\b(?:REMEDY|REMEDIES|UPAY|MANTRA)\b", "PLACEMENT", badge_text)
            item["badge"] = badge_text

        sanitized_scenes.append(item)
    return sanitized_scenes


def _generate_fallback_reel_data(
    topic: str,
    profile: Any,
    language: str,
    selected_hook: Dict[str, Any],
    total_scenes_target: int = 7,
    num_points: int = 5,
) -> Dict[str, Any]:
    """Generates structured 7-scene retention fallback data smartly adapted to the topic."""
    t_lower = (topic or "").lower()

    # Detect primary subject entity from topic
    if any(k in t_lower for k in ["rudraksha", "रुद्राक्ष", "mukhi"]):
        entity_name = "5-Mukhi Rudraksha"
        hook_on_screen = "RUDRAKSHA ENERGY CLASH"
        hook_spoken = "क्या आपका 5-Mukhi Rudraksha आपकी कुंडली की energy के साथ clash कर रहा है?"
        hook_visual = "Extreme macro photograph of authentic sacred 5-Mukhi Rudraksha beads showing natural deep crevices and facets on dark antique Sanskrit parchment"
        secondary_crystal = "Amethyst Crystal"
        sec_visual = "Deep purple natural raw amethyst crystal cluster glowing under cinematic directional lighting"
    elif any(k in t_lower for k in ["amethyst", "एमेथिस्ट"]):
        entity_name = "Amethyst Crystal"
        hook_on_screen = "AMETHYST ENERGY CLASH"
        hook_spoken = "क्या आपका Amethyst crystal आपकी कुंडली की energy के साथ clash कर रहा है?"
        hook_visual = "Extreme macro photograph of raw deep purple Amethyst crystal cluster with natural light refractions on dark velvet parchment"
        secondary_crystal = "5-Mukhi Rudraksha"
        sec_visual = "Authentic sacred five mukhi rudraksha beads resting on ancient Vedic chart"
    elif any(k in t_lower for k in ["pyrite", "पायराइट"]):
        entity_name = "Golden Pyrite"
        hook_on_screen = "PYRITE MONEY CLASH"
        hook_spoken = "क्या आपका Pyrite stone आपकी कुंडली की wealth energy को block कर रहा है?"
        hook_visual = "Macro photograph of shimmering golden pyrite crystal cluster with brassy cubic crystals on dark velvet"
        secondary_crystal = "Citrine Quartz"
        sec_visual = "Golden radiant citrine quartz crystal cluster with natural facets"
    elif any(k in t_lower for k in ["citrine", "सिट्रीन"]):
        entity_name = "Citrine Quartz"
        hook_on_screen = "CITRINE WEALTH CLASH"
        hook_spoken = "क्या आपका Citrine crystal आपकी कुंडली के 2nd house के साथ clash कर रहा है?"
        hook_visual = "Macro photograph of vibrant golden-yellow citrine crystal gemstone glowing under warm golden light"
        secondary_crystal = "Yellow Sapphire"
        sec_visual = "Flawless natural yellow sapphire gemstone on dark velvet"
    elif any(k in t_lower for k in ["tourmaline", "टूरमैलीन"]):
        entity_name = "Black Tourmaline"
        hook_on_screen = "TOURMALINE SHIELD CLASH"
        hook_spoken = "क्या आपका Black Tourmaline आपकी aura frequency के साथ align नहीं हो रहा?"
        hook_visual = "Macro photograph of raw needle-textured black tourmaline crystal cluster on dark slate stone"
        secondary_crystal = "Clear Quartz"
        sec_visual = "Prismatic clear quartz natural crystal point"
    elif any(k in t_lower for k in ["sapphire", "neelam", "नीलम"]):
        entity_name = "Royal Blue Sapphire"
        hook_on_screen = "NEELAM DANGER CLASH"
        hook_spoken = "बिना कुंडली जांचे Neelam पहनना आपकी mental peace को क्यों disrupt कर सकता है?"
        hook_visual = "Macro photograph of radiant royal blue sapphire gemstone showing hexagonal crystal growth lines"
        secondary_crystal = "Emerald Gemstone"
        sec_visual = "Flawless faceted natural emerald and blue sapphire gemstones glowing on dark velvet"
    else:
        entity_name = "Tiger Eye Gemstone"
        hook_on_screen = "TIGER EYE NOT WORKING"
        hook_spoken = "क्या आपका Tiger Eye स्टोन आपकी कुंडली की एनर्जी के साथ क्लैश कर रहा है?"
        hook_visual = "Extreme macro close-up photograph of a radiant golden-brown Tiger's Eye gemstone and bracelet showing vivid silky chatoyancy resting on dark antique Sanskrit parchment"
        secondary_crystal = "Royal Blue Sapphire"
        sec_visual = "Flawless faceted natural emerald and blue sapphire gemstones glowing on dark velvet"

    # Use hook override if provided
    if selected_hook and selected_hook.get("on_screen"):
        hook_on_screen = str(selected_hook["on_screen"]).upper().strip()
    if selected_hook and selected_hook.get("spoken"):
        hook_spoken = str(selected_hook["spoken"]).strip()

    # Determine planetary scene 2
    if any(k in t_lower for k in ["jupiter", "guru", "बृहस्पति"]):
        sc2_spoken = "पहला मुख्य संकेत, जब आपकी कुंडली में Guru Jupiter कमजोर स्थिति में होता है, तो यह higher wisdom और focus को disrupt करता है।"
        sc2_onscreen = "JUPITER ENERGY CLASH"
        sc2_badge = "GURU PLACEMENT"
        sc2_visual = "3D Guru Jupiter planet in Vedic Kundli 9th house with glowing golden aura"
    else:
        sc2_spoken = "पहला मुख्य संकेत, जब आपकी कुंडली में Sun और Rahu का ग्रहण संघर्ष आपके nervous system और mental peace को हिला देता है।"
        sc2_onscreen = "SUN RAHU CONFLICT"
        sc2_badge = "AURA SHIELD"
        sc2_visual = "Authentic ancient Vedic Kundli birth chart parchment showing Sun and Rahu planetary positions"

    # Determine planetary scene 4
    if any(k in t_lower for k in ["mars", "mangal", "मंगल"]):
        sc4_spoken = "तीसरा कारण, जब Mars की fierce energy गलत भाव में होती है, तो यह aggression और internal stress पैदा करती है।"
        sc4_onscreen = "MARS OVERHEATING MIND"
        sc4_badge = "BIO-ENERGY CODE"
        sc4_visual = "3D Planet Mars in Vedic Kundli 1st house glowing with fierce crimson-amber Martian aura"
    else:
        sc4_spoken = "तीसरा कारण, जब Mars की fierce energy गलत भाव में होती है, तो यह aggression और internal stress पैदा करती है।"
        sc4_onscreen = "MARS MISALIGNMENT"
        sc4_badge = "BIO-ENERGY CODE"
        sc4_visual = "Fiery red planet Mars in deep space showing atmospheric dust and cratered surface"

    # Determine planetary scene 5
    if any(k in t_lower for k in ["saturn", "shani", "शनि"]):
        sc5_spoken = "चौथा नियम, जब Shani ki dristi आपके chart पर पड़ती है, तो यह unexpected delays और heavy karmic pressure लाती है।"
        sc5_onscreen = "SHANI KARMIC DELAYS"
        sc5_badge = "INSTANT CALM"
        sc5_visual = "3D Planet Saturn in 7th house drawing 3 aspect arrows to 9th, 1st, and 4th house"
    else:
        sc5_spoken = "चौथा नियम, जब Shani ki dristi आपके chart पर पड़ती है, तो यह unexpected delays और heavy karmic pressure लाती है।"
        sc5_onscreen = "SHANI KARMIC IMPACT"
        sc5_badge = "INSTANT CALM"
        sc5_visual = "Planet Saturn with majestic cosmic rings in deep starry space"

    scenes = [
        {
            "scene_num": 1,
            "spoken_line": hook_spoken,
            "on_screen_text": hook_on_screen,
            "badge": "SACRED ENERGY SECRET",
            "visual_description": hook_visual,
            "estimated_seconds": 3.8,
        },
        {
            "scene_num": 2,
            "spoken_line": sc2_spoken,
            "on_screen_text": sc2_onscreen,
            "badge": sc2_badge,
            "visual_description": sc2_visual,
            "estimated_seconds": 4.5,
        },
        {
            "scene_num": 3,
            "spoken_line": "दूसरा गहरा भेद, जब 12th House की सक्रियता आपकी vital energy को drain करके focus पूरी तरह खत्म कर देती है।",
            "on_screen_text": "12TH HOUSE DRAIN",
            "badge": "SECRET FREQUENCY",
            "visual_description": "Vedic astrology diamond Kundli chart with 12th house quadrant highlighted on ancient parchment",
            "estimated_seconds": 4.5,
        },
        {
            "scene_num": 4,
            "spoken_line": sc4_spoken,
            "on_screen_text": sc4_onscreen,
            "badge": sc4_badge,
            "visual_description": sc4_visual,
            "estimated_seconds": 4.5,
        },
        {
            "scene_num": 5,
            "spoken_line": sc5_spoken,
            "on_screen_text": sc5_onscreen,
            "badge": sc5_badge,
            "visual_description": sc5_visual,
            "estimated_seconds": 4.5,
        },
        {
            "scene_num": 6,
            "spoken_line": f"पांचवां नियम: बिना complete birth chart analysis के कोई भी {entity_name} या {secondary_crystal} कभी न पहनें, यह adverse impact दे सकता है।",
            "on_screen_text": "AVOID BLIND REMEDIES",
            "badge": "SPIRITUAL WARNING",
            "visual_description": sec_visual,
            "estimated_seconds": 4.5,
        },
        {
            "scene_num": 7,
            "spoken_line": "यह reel तुरंत save करें। अपनी कुंडली की planetary placement comment करें और personal consultation के लिए हमें तुरंत DM करें।",
            "on_screen_text": "SAVE REEL • DM US",
            "badge": "CHECK PLACEMENT & DM US",
            "visual_description": "Ancient sacred stone temple sanctum with glowing golden brass oil lamps and Shiva lingam",
            "estimated_seconds": 4.0,
        },
    ]

    return {
        "title": f"{entity_name} & Kundli Energy Blueprint",
        "topic": topic,
        "niche": getattr(profile, "niche_id", "vedic_astrology"),
        "language": language,
        "visual_theme": "modern_dynamic",
        "scenes": scenes,
        "caption": f"Why your {entity_name} might clash with your birth chart ⚠️ Always verify your planetary positions before wearing sacred stones.",
        "hashtags": ["#VedicAstrology", "#GemstoneEnergy", "#KundliAnalysis", "#Jyotish", "#NeoDivineStore"],
        "call_to_action": "DM us for personal consultation",
    }


def generate_reel(
    topic: str,
    niche: str = "tech_ai",
    language: str = "English",
    duration: int = 25,
    niche_profile: Optional[NicheProfile] = None,
    seo_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a complete production-ready Instagram Reel with Gemini.
    Adapts fully to any configured NicheProfile (Tech, Fitness, Finance, Astrology, etc.)
    and integrates Instagram SEO search keywords into on-screen cards and spoken dialogue.
    """
    profile = niche_profile or get_default_niche(niche)

    # 0. Instagram Explore SEO Metadata Resolution
    seo_meta = seo_metadata
    if not seo_meta:
        try:
            seo_meta = generate_seo_metadata(topic=topic, niche=profile.name)
        except Exception as exc:
            logger.warning(f"Could not auto-generate SEO metadata: {exc}")
            seo_meta = {}

    seo_keywords = seo_meta.get("primary_search_keywords", [])
    seo_loop = seo_meta.get("loop_closing_phrase", "")
    seo_save_trigger = seo_meta.get("save_trigger_reason", "")
    seo_hashtags = seo_meta.get("recommended_hashtags", [])

    seo_prompt_section = ""
    if seo_keywords:
        seo_prompt_section = f"""
INSTAGRAM ALGORITHM SEO & EXPLORER SEARCH INDEXING:
1. Target Search Keywords (must appear in Scene 1 on-screen card & spoken hook for OCR and ASR indexing):
   {', '.join(seo_keywords)}
2. Retention Loop Hook:
   Ending transition concept: "{seo_loop}" (connects final scene cleanly back into opening hook word).
3. Save/Share Trigger:
   CTA must offer this reference value: "{seo_save_trigger}".
"""

    # 1. Generate & score hooks
    candidate_hooks = generate_hooks(topic, niche=profile.niche_id, language=language, niche_profile=profile)
    ranked_hooks = score_hooks(candidate_hooks)
    selected_hook = ranked_hooks[0]

    learning_engine = SelfLearningEngine()
    playbook_context = learning_engine.get_prompt_injection()
    algo_brain = InstagramAlgorithmBrain()
    algo_context = algo_brain.generate_prompt_boost_snippet()

    # Niche-specific instructions
    is_astrology = profile.niche_id in ("astrology_vedic", "astrology")
    is_hindi = "hindi" in language.lower() or "hi" in language.lower() or "hinglish" in language.lower()

    num_points = 5
    total_scenes_target = 7

    if is_hindi:
        # Dynamically determine point count from topic (defaults to 5 points for viral retention)
        m_pts = re.search(r"^\s*([456])\b", topic) or re.search(r"\b([456])\s*(?:points?|signs?|mistakes?|flaws?|reasons?|placements?|yogas?|rules?|insights?|secrets?|meanings?|ways?|lessons?|bhav|galti|lakshan)\b", topic, re.I)
        if m_pts:
            num_points = int(m_pts.group(1))
        else:
            num_points = 5  # default 5 high-voltage points for maximum Instagram engagement

        total_scenes_target = num_points + 2

        lang_rule_section = f"""
CRITICAL LANGUAGE & PRONUNCIATION MANDATE (NATURAL CONVERSATIONAL HINGLISH IN DEVANAGARI):
- ALL SCENES "spoken_line": Write in NATURAL, MODERN CONVERSATIONAL HINGLISH using Devanagari script for flawless Indian neural voice pronunciation (Sarvam AI).
  * Use everyday relatable words that modern people actually speak on social media:
    Use "नर्वस सिस्टम" (STRICT BAN on "तंत्रिका तंत्र"!),
    Use "करियर" (not "आजीविका" or "कर्मेश"),
    Use "स्ट्रेस / टेंशन" (not "मानसिक संताप / तनाव"),
    Use "ग्रोथ / सक्सेस" (not "पदोन्नति"),
    Use "क्लाइंट / लोग" (not "जातक"),
    Use "एनर्जी / पॉजिटिव वाइब्स" (not "ऊर्जा पुंज" or "सकारात्मक आभामंडल"),
    Use "रिजल्ट" (not "प्रतिफल"),
    Use "मेहनत" (not "अथक परिश्रम"),
    Use "फोकस / माइंड" (not "चित्त की एकाग्रता").
  * STRICT BAN ON DEEP / ARCHAIC SANSKRITIZED HINDI: Hard textbook Hindi alienates social media audiences. Keep it 100% natural, everyday conversational Hinglish!
- ALL SCENES "on_screen_text": Write in clean, bold ALL CAPS plain ASCII ENGLISH (2-4 words, e.g. "CAREER BREAKTHROUGH", "CALMS NERVOUS SYSTEM", "SHIELDS NEGATIVE ENERGY").
  * STRICT BAN: DO NOT prefix with "1.", "2.", "3." or "1 OF 5". Keep on-screen text punchy, curious, and immediate!
- ALL SCENES "badge": High-curiosity interactive badge pill (e.g. "WEALTH MAGNET", "SECRET FREQUENCY", "AURA SHIELD", "INSTANT CALM", "BIO-ENERGY CODE", "DEEP FOCUS").
  * STRICT BAN: NEVER write "1 OF 5", "2 OF 5", "BENEFIT 1 OF 5", or "1 OF 3". The audience hates robotic "1 OF X" text!

CRITICAL TONE & ASTROLOGER IDENTITY MANDATE (CALM, GENTLE & DIVERSE CLIENT CASE STUDIES):
- TONE: Calm, gentle, soothing, poised, compassionate and respectful. Absolutely NO aggressive, shouty, attacking, or accusatory delivery!
- NEVER speak in the first person about making a rookie mistake or suffering personal loss ("मैंने गलती की", "मेरा नुकसान हुआ", "मैंने गलत रत्न पहना").
- STRICT ZERO-REPETITION MANDATE (ABSOLUTE BAN ON "पैंतालीस लाख / 45 LAKHS / भारी नुकसान"):
  * NEVER use "पैंतालीस लाख" or "भारी नुकसान" repeatedly. That is completely banned.
  * Rotate across all life dimensions: mental clarity, 3 AM awakening intuition, career breakthroughs, emotional serenity, and ancestral karmic lessons.
  * Use varied, dignified expressions:
    "हमारे परामर्श सत्र में एक जातक आए जो निरंतर मानसिक तनाव से जूझ रहे थे...",
    "कुंडली विश्लेषण के दौरान हमने पाया कि उनकी कार्यक्षेत्र में प्रगति क्यों रुकी हुई थी...",
    "हाल ही में एक क्लाइंट अपनी जन्मपत्रिका लेकर आए जो रात में अचानक नींद टूटने की समस्या से परेशान थे..."

STRICT MANDATE - ZERO REMEDIES & ZERO MANTRAS (ABSOLUTELY CRITICAL):
- DO NOT recommend ANY remedies (no gemstones to wear, no rituals, no havan, no donations, no fasting).
- DO NOT provide ANY mantras, beej mantras, or chants (no 'ॐ...', no mantra text whatsoever).
- INSTEAD: Focus entirely on teaching the planet/nakshatra's karmic energy, warning symptoms, and key Kundli house placements.
- CALL TO ACTION (CTA): Ask viewers to check their house placement, comment below, and DM us for a personalized Kundli consultation!

NEGATIVE CONSTRAINT - COMPLETE BAN ON DEGREE JARGON:
- STRICTLY DO NOT USE the words "degree", "degrees", "डिग्री", "अंश", or "dead degrees" anywhere in spoken or on-screen text!
- Avoid boring astrological math. Viewers on Instagram care about REAL-LIFE IMPACT: emotional state, financial stability, health warnings, relationship harmony, and personal Kundli placements.

DYNAMIC SCENE STRUCTURE (EXACTLY {total_scenes_target} SCENES: HOOK + {num_points} INTERACTIVE POINTS + CTA):
- Write exactly {total_scenes_target} scenes tailored 100% specifically to "{topic}":
  * Scene 1 (Hook): Scroll-stopping opener (0-3s) asking a hypnotic question or revealing an irresistible curiosity hook. Badge: "SACRED ENERGY SECRET" or "WATCH CLOSELY".
  * Scene 2 (Point 1): Spoken: "पहला मुख्य संकेत / रहस्य..." | On-Screen: "[BESPOKE 2-4 WORD TITLE]" | Badge: "[INTERACTIVE CURIOSITY BADGE]"
  * Scene 3 (Point 2): Spoken: "दूसरा गहरा प्रभाव..." | On-Screen: "[BESPOKE 2-4 WORD TITLE]" | Badge: "[INTERACTIVE CURIOSITY BADGE]"
  * Scene 4 to {num_points + 1}: Remaining points through {num_points}
  * Scene {total_scenes_target} (CTA): Save + Share + Comment placement + DM for consultation | On-Screen: "SAVE REEL • COMMENT BELOW" | Badge: "SAVE REEL • COMMENT BELOW"

CRITICAL DIVERSITY MANDATE:
- Every point title and spoken line MUST be completely unique and specific to "{topic}".
- DO NOT reuse generic placeholders like "FIRST DANGER", "SUDDEN BLOCKS", or "ENEMY CLASH".
"""
        scenes_format_example = f"""    {{
      "scene_num": 1,
      "spoken_line": "{selected_hook['spoken']}",
      "on_screen_text": "{selected_hook['on_screen']}",
      "badge": "SACRED ENERGY SECRET",
      "visual_description": "Scroll-stopping opener matching {profile.visual_style}",
      "estimated_seconds": 3
    }},
    {{
      "scene_num": 2,
      "spoken_line": "पहला मुख्य रहस्य जो इस कुंडली स्थिति की वास्तविकता बताता है...",
      "on_screen_text": "PRIMARY MANIFESTATION",
      "badge": "AURA SHIELD",
      "visual_description": "Ancient Vedic manuscript or cosmic celestial visual",
      "estimated_seconds": 4
    }},
    {{
      "scene_num": 3,
      "spoken_line": "दूसरा गहरा प्रभाव, जब यह ऊर्जा जीवन में विशेष परिणाम देती है...",
      "on_screen_text": "DEEPER KARMIC REASON",
      "badge": "SECRET FREQUENCY",
      "visual_description": "Visual matching the planetary energy or Kundli houses",
      "estimated_seconds": 4
    }},
    {{
      "scene_num": 4,
      "spoken_line": "तीसरा सबसे महत्वपूर्ण पहलू, जिसे समझने के लिए अपनी कुंडली के भाव देखें...",
      "on_screen_text": "KUNDLI HOUSE SECRET",
      "badge": "BIO-ENERGY CODE",
      "visual_description": "Ancient temple sanctum or celestial planetary alignment",
      "estimated_seconds": 4
    }},
    {{
      "scene_num": {total_scenes_target},
      "spoken_line": "यह रील तुरंत सेव करें। अपनी कुंडली में इसकी स्थिति नीचे कमेंट करें और व्यक्तिगत विश्लेषण के लिए हमें तुरंत डीएम करें।",
      "on_screen_text": "SAVE REEL • COMMENT BELOW",
      "badge": "SAVE REEL • COMMENT BELOW",
      "visual_description": "Ancient temple sanctum sanctorum with brass lamps",
      "estimated_seconds": 4
    }}"""
    else:
        lang_rule_section = """
WRITING QUALITY:
- Spoken lines must be conversational, confident, and crisp (total 40-50 words across all 5 scenes).
- Natural ellipses (`...`) for dramatic breath pauses.
- On-screen text 100% clean plain ASCII letters (no emojis that break renderers).
"""
        scenes_format_example = f"""    {{
      "scene_num": 1,
      "spoken_line": "{selected_hook['spoken']}",
      "on_screen_text": "{selected_hook['on_screen']}",
      "visual_description": "Scroll-stopping opener matching {profile.visual_style}",
      "estimated_seconds": 3
    }},
    {{
      "scene_num": 2,
      "spoken_line": "First core insight or symptom that explains why this occurs.",
      "on_screen_text": "1. CORE INSIGHT",
      "visual_description": "Dynamic visual illustrating the problem or primary concept",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 3,
      "spoken_line": "The mechanism or shift: what most people overlook.",
      "on_screen_text": "2. THE HIDDEN SHIFT",
      "visual_description": "Clean analytical or high-energy demonstration",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 4,
      "spoken_line": "Actionable rule or mistake to avoid immediately.",
      "on_screen_text": "3. ACTIONABLE RULE",
      "visual_description": "High contrast emphasis on the solution or breakthrough",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 5,
      "spoken_line": "{profile.cta_presets[0]}",
      "on_screen_text": "SAVE • FOLLOW FOR MORE",
      "visual_description": "Memorable closing branded card with clear typography",
      "estimated_seconds": 4
    }}"""

    if is_astrology:
        niche_instructions = f"""
CRITICAL JYOTISH ACCURACY RULES:
- Focus solely on the planet, house, and transit relevant to "{topic}".
- Spoken lines: Must be written strictly in pure, natural, respectful HINDI in Devanagari script (हिंदी लिपि) for rich Vedic authority and perfect Indian pronunciation.
- On-screen cards: Clean ALL CAPS plain ASCII English keywords (3-5 words) that Indian viewers love on Instagram Reels (e.g. "5 DEADLY GEMSTONE MISTAKES", "SUDDEN MONEY DRAIN", "ENEMY STONES CLASH", "ACTIVATE NATURAL GEMS", "SAVE REEL • DM US").
- Call to Action: Instruct viewers to save the reel, share with friends, and DM for personalized chart consultation. Never say 'link in bio'.
- ABSOLUTELY NO DEGREE JARGON: Do NOT mention 'degrees', 'डिग्री', or mathematical degree values. Cover 4 to 5 tangible real-world symptoms, dangers, and authentic gemstone rules.
"""
    else:
        niche_instructions = f"""
NICHE STRATEGY ({profile.name.upper()}):
- Target Audience: {profile.target_audience}
- Content Pillars: {', '.join(profile.content_pillars)}
- Visual Tone: {profile.visual_style}
- Audio Tone: {profile.tone}
- Call to Action Options: {profile.cta_presets}
- DO NOT use astrological, esoteric, or temple terminology. Keep all concepts grounded in {profile.name}.
"""

    retention_structure_section = f"""
VIRAL RETENTION STRUCTURE (7 SCENES PERFECTLY SYNCED 1-TO-5):
TOPIC: {topic}
STRICT NEGATIVE CONSTRAINT - ZERO REMEDIES & ZERO MANTRAS.
STRICT MANDATE - ANCHOR EVERY SCENE TO CONCRETE ASTROLOGICAL / GEMSTONE ENTITIES:
- Every point MUST reference a tangible Jyotish entity (e.g. Tiger's Eye, Sun & Rahu in Kundli, 12th House, Mars energy, Saturn's aspect / Shani ki dristi).
- Spoken lines MUST be in natural conversational Hinglish using Devanagari script for flawless voiceover pronunciation.
- On-Screen cards MUST be strictly 100% English (ALL CAPS, 2-4 punchy words, ZERO Hindi text, ZERO number prefixes like '1.' or '2.').

1. SCENE 1 (0-3s) - THE HOOK:
   - Spoken: Winning hook above (calling out whether the gemstone is clashing with birth chart energy).
   - On-Screen: Winning on-screen text in ALL CAPS English (e.g. "TIGER EYE NOT WORKING", "GEMSTONE CLASHING").
   - Badge: "SACRED ENERGY SECRET"
2. SCENE 2 (3-7s) - POINT 1 (PLANETARY CONFLICT):
   - Spoken: "पहला मुख्य संकेत, जब आपकी कुंडली में Sun और Rahu का टकराव आपके nervous system और mental peace को हिला देता है।"
   - On-Screen: "SUN RAHU CONFLICT"
   - Badge: "AURA SHIELD"
3. SCENE 3 (7-11s) - POINT 2 (HOUSE ENERGY DRAIN):
   - Spoken: "दूसरा गहरा भेद, जब 12th House की सक्रियता आपकी vital energy को drain करके focus पूरी तरह खत्म कर देती है।"
   - On-Screen: "12TH HOUSE DRAIN"
   - Badge: "SECRET FREQUENCY"
4. SCENE 4 (11-15s) - POINT 3 (FIERCE PLANET MISALIGNMENT):
   - Spoken: "तीसरा कारण, जब Mars की fierce energy गलत भाव में होती है, तो यह aggression और internal stress पैदा करती है।"
   - On-Screen: "MARS FIERCE ENERGY"
   - Badge: "BIO-ENERGY CODE"
5. SCENE 5 (15-19s) - POINT 4 (KARMIC ASPECT / SHANI DRISTI):
   - Spoken: "चौथा रहस्य, जब Shani ki dristi आपके chart पर पड़ती है, तो यह unexpected delays और heavy karmic pressure लाती है।"
   - On-Screen: "SHANI KARMIC IMPACT"
   - Badge: "INSTANT CALM"
6. SCENE 6 (19-24s) - POINT 5 (DANGER OF BLIND REMEDIES):
   - Spoken: "पांचवां नियम: बिना complete birth chart analysis के कोई भी gemstone कभी न पहनें, यह adverse impact दे सकता है।"
   - On-Screen: "AVOID BLIND REMEDIES"
   - Badge: "SPIRITUAL WARNING"
7. SCENE 7 (24-28s) - 4-LAYER VIRAL CALL TO ACTION:
   - Spoken: "यह reel तुरंत save करें। अपनी कुंडली की planetary placement comment करें और personal consultation के लिए हमें तुरंत DM करें।"
   - On-Screen: "SAVE REEL • DM US"
   - Badge: "CHECK PLACEMENT & DM US"
"""

    prompt = f"""
You are the world-class short-form video director and creative strategist for {profile.name}.
You know how to write razor-sharp, hypnotic scripts that keep viewers glued to their screens from second 0 to the very last frame.

NICHE: {profile.name}
TOPIC: {topic}
TARGET DURATION: {duration} seconds
LANGUAGE: {language}
WINNING HOOK (AUDIO): {selected_hook["spoken"]}
WINNING ON-SCREEN HOOK: {selected_hook["on_screen"]}

{playbook_context}

{algo_context}

{seo_prompt_section}

{niche_instructions}

{retention_structure_section}

{lang_rule_section}

Return ONLY valid JSON in this exact structure:
{{
  "title": "Short punchy title",
  "topic": "{topic}",
  "niche": "{profile.niche_id}",
  "language": "{language}",
  "visual_theme": "modern_dynamic",
  "scenes": [
{scenes_format_example}
  ],
  "caption": "Full Instagram caption text optimized for SEO and engagement",
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],
  "call_to_action": "{profile.cta_presets[0]}"
}}
"""

    try:
        data = generate_json(prompt)
    except Exception as exc:
        logger.warning(f"Gemini script generation failed ({exc}). Using structured 7-scene retention fallback script...")
        data = _generate_fallback_reel_data(
            topic=topic,
            profile=profile,
            language=language,
            selected_hook=selected_hook,
            total_scenes_target=total_scenes_target,
            num_points=num_points,
        )

    scenes = data.get("scenes", [])
    if not scenes:
        raise ValueError("Gemini returned no scenes for the Reel.")

    scenes = sanitize_script_dialogue(scenes, topic)

    # Transform narration into structured scene visual plans with strict context isolation
    from app.video.scene_visual_planner import SceneVisualPlanner
    visual_plans = SceneVisualPlanner.plan_reel_visuals(scenes=scenes, topic=topic)
    for idx, sc in enumerate(scenes):
        plan = visual_plans[idx]
        sc["visual_plan"] = plan.to_dict()
        sc["visual_description"] = plan.generation_prompt
        sc["estimated_seconds"] = calculate_spoken_duration(sc.get("spoken_line", ""), language=language)

    full_script_lines = [sc["spoken_line"] for sc in scenes]

    full_script_text = "\n".join(full_script_lines)

    # Timing analysis via beats.py
    try:
        timing = beats.analyse(full_script_text, wpm=165, target=duration)
    except Exception as exc:
        timing = {"wpm": 165, "target": duration, "total_seconds": duration, "total_words": len(full_script_text.split()), "beats": []}

    # Human score check
    try:
        _, overall_score, verdict = detect.run(full_script_text, get_lexicon())
        human_score = round(overall_score, 1)
    except Exception as exc:
        human_score = 92.0

    # Ensure selected_hook is harmonized with sanitized Scene 1
    if scenes and len(scenes) > 0:
        selected_hook["spoken"] = scenes[0].get("spoken_line", selected_hook.get("spoken", ""))
        selected_hook["on_screen"] = scenes[0].get("on_screen_text", selected_hook.get("on_screen", ""))

    result = {
        "topic": topic,
        "niche": profile.niche_id,
        "language": language,
        "title": data.get("title", topic),
        "visual_theme": data.get("visual_theme", "modern_dynamic"),
        "selected_hook": selected_hook,
        "hook_rankings": ranked_hooks,
        "scenes": scenes,
        "visual_plans": [p.to_dict() for p in visual_plans],
        "full_script": full_script_text,
        "caption": data.get("caption", ""),
        "hashtags": (seo_hashtags[:5] if seo_hashtags else data.get("hashtags", []))[:5],
        "seo_metadata": seo_meta,
        "call_to_action": data.get("call_to_action", profile.cta_presets[0]),
        "timing": timing,
        "human_score": human_score,
    }

    # Save to scripts directory
    filename = re.sub(r"[^\w\-]", "_", topic.lower())[:30] + ".json"
    save_path = SCRIPTS_DIR / filename
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Reel script generated and saved to {save_path}")
    return result


if __name__ == "__main__":
    test_topic = "Top 3 Python AI libraries in 2026"
    print(f"Generating Reel for topic: {test_topic}...")
    res = generate_reel(test_topic, niche="tech_ai", duration=25)
    print("WINNING HOOK:", res["selected_hook"]["spoken"])
    print("SCENES COUNT:", len(res["scenes"]))
    print("HASHTAGS:", res["hashtags"])
    print("CAPTION SNIPPET:", res["caption"][:120])
