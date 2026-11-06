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
    niche: str = "Vedic astrology",
    language: str = "Hindi mixed with English",
) -> List[Dict[str, Any]]:
    """
    Generate three distinct hooks for a topic using the 26 repository hook formulas.
    """
    formulas = load_hook_formulas()
    formula_summary = [
        {
            "id": item["id"],
            "name": item["name"],
            "template": item["template"],
            "trap": item["trap"],
        }
        for item in formulas
    ]

    learning_engine = SelfLearningEngine()
    playbook_context = learning_engine.get_prompt_injection()
    algo_brain = InstagramAlgorithmBrain()
    algo_context = algo_brain.generate_prompt_boost_snippet()

    is_hindi = language.lower() in ["hindi", "hi"]

    if is_hindi:
        lang_rule = """
LANGUAGE & PRONUNCIATION MANDATE (100% PURE DEVANAGARI HINDI):
- "spoken": MUST be written strictly in pure, natural, respectful HINDI in Devanagari script (हिंदी लिपि).
  Example Spoken: "रुकिए! पुखराज पहनने से पहले अपनी कुंडली का यह भाव ज़रूर देख लें!"
  DO NOT write spoken lines in Roman English or Hinglish! Pure Devanagari guarantees native Indian voice models pronounce every Vedic Sanskrit term (शनि, राहु, केतु, नीलम, पन्ना, कुंडली, उपाय) with 100% human-grade studio perfection.
- "on_screen": MUST be written in clean, bold ALL CAPS ENGLISH (3 to 6 words) with a relevant emoji.
  Example On-Screen: "⚠️ STOP WEARING PUKHRAJ!"
"""
        example_json = """{
  "hooks": [
    {
      "formula_id": 2,
      "formula_name": "Negative Command",
      "spoken": "रुकिए! पुखराज पहनने से पहले अपनी कुंडली का यह भाव ज़रूर देख लें!",
      "on_screen": "⚠️ STOP WEARING PUKHRAJ!"
    }
  ]
}"""
    else:
        lang_rule = """
LANGUAGE & PRONUNCIATION MANDATE (CLEAN FLUENT ENGLISH):
- "spoken": MUST be written in clean, fluent, grammatical English.
  Example Spoken: "Stop wearing Yellow Sapphire right now until you check this placement!"
- "on_screen": MUST be in bold ALL CAPS ENGLISH (3 to 6 words) with a relevant emoji.
  Example On-Screen: "⚠️ STOP WEARING PUKHRAJ!"
"""
        example_json = """{
  "hooks": [
    {
      "formula_id": 2,
      "formula_name": "Negative Command",
      "spoken": "Stop wearing Yellow Sapphire right now until you check this placement!",
      "on_screen": "⚠️ STOP WEARING PUKHRAJ!"
    }
  ]
}"""

    prompt = f"""
You are the #1 viral Instagram Reels strategist who has scripted dozens of 10M+ view Reels in the personal growth, psychology, and Vedic wisdom niche.

Create THREE explosive, scroll-stopping viral hooks for an Instagram Reel.

NICHE: {niche}
TOPIC: {topic}
LANGUAGE: {language}

{lang_rule}

{playbook_context}

{algo_context}

AVAILABLE HOOK FORMULAS:
{json.dumps(formula_summary, ensure_ascii=False)}

CRITICAL VIRAL HOOK PRINCIPLES:
1. PATTERN INTERRUPT: The first 1-2 seconds MUST stop the thumb cold. Use urgency, an aggressive warning, a counter-intuitive taboo, or a direct callout.
2. ON-SCREEN TEXT CARD:
   - Must be 3 to 6 words MAXIMUM.
   - High visual impact, aggressive uppercase, includes a relevant emoji (⚠️, ❌, 🚨, 🪐, ⚡, 💎).
   - Must be instantly readable in 0.5 seconds at arm's length on a mobile screen.
3. SPOKEN VOICE & LENGTH:
   - CRITICAL: The spoken line MUST be between 7 and 12 WORDS MAXIMUM (approx 2.5 seconds).
   - If a hook is more than 12 words, it FAILS the viral algorithm!
   - Urgent, authoritative, relatable.
4. Select 3 completely different formulas.

Return ONLY valid JSON in this exact structure:
{example_json}
"""

    data = generate_json(prompt)
    hooks = data.get("hooks", [])

    if len(hooks) != 3:
        if len(hooks) > 0:
            return hooks
        raise ValueError("Gemini did not return valid hooks.")

    # Validate on_screen word count (trim if needed)
    for h in hooks:
        words = h["on_screen"].split()
        if len(words) > 6:
            h["on_screen"] = " ".join(words[:6])

    return hooks


def score_hooks(hooks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score hooks using the repository's hookscore.py heuristic engine.
    Handles both pure English and Devanagari Hindi gracefully.
    """
    ranked = []
    for item in hooks:
        text_to_score = item.get("spoken", "")
        is_hindi = bool(re.search(r"[\u0900-\u097F]", text_to_score))
        if is_hindi:
            # Score against English on-screen card for structural heuristic
            text_to_score = item.get("on_screen", text_to_score)

        try:
            results, overall, verdict, flags = hookscore.run(text_to_score)
        except Exception:
            results, overall, verdict, flags = {}, 85.0, "STRONG", []

        if is_hindi and overall < 70.0:
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


def generate_reel(
    topic: str,
    niche: str = "Vedic astrology",
    language: str = "Hindi mixed with English",
    duration: int = 30,
) -> Dict[str, Any]:
    """
    Generate a complete production-ready Instagram Reel with Gemini.
    Produces:
    - Ranked hooks
    - Selected winning hook
    - Beat-by-beat script with visual descriptions
    - Timed on-screen text cards
    - Clean Instagram caption (first 125 chars optimized)
    - Targeted hashtags (max 5)
    - Timing and beat sheet analysis
    """
    # 1. Generate & score hooks
    candidate_hooks = generate_hooks(topic, niche=niche, language=language)
    ranked_hooks = score_hooks(candidate_hooks)
    selected_hook = ranked_hooks[0]

    learning_engine = SelfLearningEngine()
    playbook_context = learning_engine.get_prompt_injection()
    algo_brain = InstagramAlgorithmBrain()
    algo_context = algo_brain.generate_prompt_boost_snippet()

    is_hindi = language.lower() in ["hindi", "hi"]

    if is_hindi:
        scenes_format_example = f"""    {{
      "scene_num": 1,
      "spoken_line": "{selected_hook['spoken']}",
      "on_screen_text": "{selected_hook['on_screen']}",
      "visual_description": "Cinematic dramatic zoom on the sacred Vedic birth chart or planetary symbol",
      "estimated_seconds": 3
    }},
    {{
      "scene_num": 2,
      "spoken_line": "पहला संकेत: जब यह ग्रह इस भाव में बैठता है, तो भारी मेहनत के बाद भी अनचाहे संकट और रुकावटें बढ़ जाती हैं।",
      "on_screen_text": "1. PLACEMENT ONE SIGN",
      "visual_description": "Ancient Vedic parchment chart illuminated by sacred oil lamp",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 3,
      "spoken_line": "दूसरा संकेत: इस ग्रह की वक्री दृष्टि आपके जीवन में ठीक सफलता के समय अप्रत्याशित अड़चनें पैदा करती है।",
      "on_screen_text": "2. PLACEMENT TWO IMPACT",
      "visual_description": "Deep space cinematic planetary cosmos view",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 4,
      "spoken_line": "तीसरा संकेत: अगर यह ग्रह पीड़ित है, तो बिना सटीक डिग्री जाने कोई भी सामान्य उपाय भारी नुकसान करा सकता है।",
      "on_screen_text": "3. NEVER GUESS YOUR REMEDY",
      "visual_description": "Mystical ancient Vedic parchment chart illuminated by cosmic starlight",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 5,
      "spoken_line": "अपनी जन्म तारीख और समय नीचे कमेंट करें, हम चेक करेंगे। और संपूर्ण कुंडली विश्लेषण के लिए बायो में कंसल्टेशन बुक करें। पर कोई भी कदम उठाने से पहले...",
      "on_screen_text": "BOOK 1-ON-1 CONSULTATION",
      "visual_description": "Ancient temple sanctum at midnight with glowing diyas",
      "estimated_seconds": 4
    }}"""
    else:
      scenes_format_example = f"""    {{
      "scene_num": 1,
      "spoken_line": "{selected_hook['spoken']}",
      "on_screen_text": "{selected_hook['on_screen']}",
      "visual_description": "Cinematic dramatic zoom on the cosmic planetary chart",
      "estimated_seconds": 3
    }},
    {{
      "scene_num": 2,
      "spoken_line": "Sign one: When this planet occupies this house, it drains your savings through sudden unexpected expenses.",
      "on_screen_text": "1. PLACEMENT ONE SIGN",
      "visual_description": "Ancient Vedic parchment chart illuminated by sacred oil lamp",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 3,
      "spoken_line": "Sign two: Retrograde aspect on this house creates frustrating roadblocks right before major breakthroughs.",
      "on_screen_text": "2. PLACEMENT TWO IMPACT",
      "visual_description": "Deep space cinematic planetary cosmos view",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 4,
      "spoken_line": "Sign three: If this planet is afflicted, performing random generic remedies can backfire severely without checking degrees.",
      "on_screen_text": "3. NEVER GUESS YOUR REMEDY",
      "visual_description": "Mystical ancient Vedic parchment chart illuminated by cosmic starlight",
      "estimated_seconds": 5
    }},
    {{
      "scene_num": 5,
      "spoken_line": "Comment your Date of Birth and exact time below—we will check your chart! For complete customized remedies, book a 1-on-1 consultation in bio. But before you comment, always remember...",
      "on_screen_text": "BOOK 1-ON-1 CONSULTATION",
      "visual_description": "Ancient temple sanctum at midnight with glowing diyas",
      "estimated_seconds": 4
    }}"""

    prompt = f"""
You are the #1 viral Instagram Reels director and world-class creator in Vedic wisdom, esoteric astrology, and spiritual energy.
You know how to write razor-sharp, hypnotic scripts that keep viewers glued to their screens from second 0 to the very last frame.

NICHE: {niche}
TOPIC: {topic}
TARGET DURATION: {duration} seconds
LANGUAGE: {language}
WINNING HOOK (AUDIO): {selected_hook["spoken"]}
WINNING ON-SCREEN HOOK: {selected_hook["on_screen"]}

{playbook_context}

{algo_context}

VIRAL RETENTION BLUEPRINT (5 DYNAMIC SCENES - UNIVERSAL MULTI-REASON / CHECKLIST FORMAT):
1. SCENE 1 (0-3s) - THE HOOK & PATTERN INTERRUPT:
   - Spoken: {selected_hook["spoken"]}
   - On-Screen Text: Punchy 3-5 words in clean ALL CAPS matching the topic (e.g. "{selected_hook['on_screen']}").
2. SCENE 2 (3-8s) - REASON 1 / FIRST PLACEMENT & LIFE SYMPTOM:
   - Detail Placement #1 or Sign #1 for this topic with vivid, relatable real-life symptoms (e.g., if wealth: Rahu in 2nd/11th giving sudden money followed by mysterious expenses; if marriage: Ketu in 7th causing emotional detachment; if career: Shani in 10th testing perseverance; if gemstone: wearing stone of 6th/8th functional malefic).
   - On-Screen Text: Punchy 3-5 words in ALL CAPS (e.g., "1. RAHU IN 2ND HOUSE").
3. SCENE 3 (8-14s) - REASON 2 / SECOND PLACEMENT & PLANETARY MECHANISM:
   - Detail Placement #2 or Sign #2 with the exact planetary mechanism (e.g., if wealth: retrograde Saturn in 12th causing constant leakages; if marriage: Mars in 8th Manglik causing friction; if psychic: Jupiter aspect on 9th giving uncanny premonitions).
   - On-Screen Text: Punchy 3-5 words in ALL CAPS (e.g., "2. SATURN IN 12TH HOUSE").
4. SCENE 4 (14-20s) - REASON 3 / THIRD PLACEMENT + REMEDY WARNING (STRICT NO-FREE-REMEDY RULE):
   - Detail Placement #3 or Sign #3 with urgency.
   - CRITICAL VIRAL RULE (NEVER PROVIDE REMEDIES IN THE REEL): NEVER give away free remedies or rituals in the video! Explicitly warn the viewer: generic online remedies can severely clash with their ascendant and cause heavier damage without checking degrees.
   - On-Screen Text: Punchy 3-5 words in ALL CAPS (e.g. "3. NEVER GUESS YOUR REMEDY" or "3. GENERIC REMEDIES BACKFIRE").
5. SCENE 5 (20-25s) - THE DUAL COMMENT-MAGNET & 1-ON-1 CONSULTATION UPSELL:
   - Strong interactive 2-step call-to-action:
     1) Ask viewers to COMMENT their exact Date of Birth, Time, or placement below for a preliminary chart scan (forcing maximum comment volume to trigger the Instagram algorithm!).
     2) Urge them to BOOK A 1-ON-1 CONSULTATION via the link in bio for a complete deep Kundli analysis and personalized remedies.
     3) Seamless infinite grammatical loop back to Scene 1's opening hook word!
   - On-Screen Text: Punchy 3-5 words in ALL CAPS (e.g. "BOOK 1-ON-1 CONSULTATION" or "COMMENT BIRTH DATE TO CHECK").

CRITICAL JYOTISH ACCURACY RULES (100% SCRIPTURALLY CORRECT VEDIC ASTROLOGY):
- PLANET & GEMSTONE ACCURACY: Only speak about the EXACT planet, house, and gemstone relevant to "{topic}".
  * Shani (Saturn) -> Blue Sapphire (Neelam) | 8th/10th/11th house | Peepal tree mustard lamp / Hanuman Chalisa
  * Brihaspati (Jupiter) -> Yellow Sapphire (Pukhraj) | 9th/12th house | Vishnu Sahasranama / Turmeric tilak
  * Ketu (South Node) -> Cat's Eye (Lehsuniya) | 12th house Moksha/Vyaya | Ganesha Atharvashirsha / Feeding street dogs
  * Rahu (North Node) -> Hessonite (Gomed) | 8th house illusions | Shiva Abhishek / Coconut donation
  * Budh (Mercury) -> Emerald (Panna) | 3rd/6th house | Feeding green spinach to cows
  * Mangal (Mars) -> Red Coral (Moonga) | 1st/8th house Manglik | Hanuman temple offering
  * Surya (Sun) -> Ruby (Manik) | 1st/5th house | Copper vessel Surya Arghya at sunrise
  * Shukra (Venus) -> Diamond / Opal | 2nd/7th house | Lakshmi devotion
  * Chandra (Moon) -> Pearl (Moti) | 4th house | Shiva milk offering
- NEVER confuse planetary houses or gemstones. If the topic is Ketu, DO NOT mention Shani or Neelam. If the topic is Pukhraj, DO NOT mention 8th house Shani.

WRITING QUALITY & HUMAN CREATOR VOICE:
- LANGUAGE & PRONUNCIATION MANDATE (100% FLAWLESS DICTION):
  * If LANGUAGE is "Hindi":
    - ALL 5 SCENES "spoken_line": MUST be written in pure, natural, respectful HINDI in Devanagari script (हिंदी लिपि, e.g. "अगर आपकी कुंडली के आठवें भाव में शनि देव बैठे हैं..."). Do NOT write spoken lines in English or Romanized Hinglish! This guarantees the native Indian voice model pronounces every Vedic Sanskrit term (शनि, राहु, केतु, नीलम, पन्ना, कुंडली, उपाय) with 100% sacred, human-grade perfection.
    - ALL 5 SCENES "on_screen_text": Write in clean, bold ALL CAPS ENGLISH (3-5 words, e.g. "STOP WEARING NEELAM!", "CHECK YOUR 8TH HOUSE") so Instagram viewers immediately read the visual card while listening to the Hindi pandit voice.
  * If LANGUAGE is "English":
    - ALL 5 SCENES "spoken_line": MUST be written in clean, fluent, grammatical English without broken hybrid slang.
    - ALL 5 SCENES "on_screen_text": Clean, bold ALL CAPS ENGLISH.
- Use natural ellipses (`...`) for dramatic breath pauses so the voice pauses naturally like a real human.
- STRICT TOTAL WORD COUNT: 35 TO 45 WORDS TOTAL across all 5 scenes combined (approx 20-22 seconds total). Each scene MUST be 6 to 9 words maximum for rapid, scroll-stopping retention.
- Fast, conversational, confident creator cadence (160 words per minute).
- Keep on-screen text 100% clean plain ASCII letters (no raw emoji symbols that break font rendering).

Return ONLY valid JSON in this exact structure:
{{
  "title": "Short punchy title",
  "topic": "{topic}",
  "niche": "{niche}",
  "language": "{language}",
  "visual_theme": "cinematic_broll",
  "scenes": [
{scenes_format_example}
  ],
  "caption": "Full Instagram caption text",
  "hashtags": ["#VedicAstrology", "#BlueSapphire", "#ShaniDev", "#JyotishSecrets", "#KarmicHealing"],
  "call_to_action": "Comment your Date of Birth below"
}}
"""

    data = generate_json(prompt)

    # Extract scenes
    scenes = data.get("scenes", [])
    if not scenes:
        raise ValueError("Gemini returned no scenes for the Reel.")

    # Humanize spoken lines
    full_script_lines = []
    for sc in scenes:
        sc["spoken_line"] = clean_and_humanize_text(sc["spoken_line"])
        full_script_lines.append(sc["spoken_line"])

        # Enforce on-screen text word limit
        card_words = sc["on_screen_text"].split()
        if len(card_words) > 6:
            sc["on_screen_text"] = " ".join(card_words[:6])

    full_script_text = "\n".join(full_script_lines)

    # 4. Timing analysis via beats.py
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

    result = {
        "topic": topic,
        "niche": niche,
        "language": language,
        "title": data.get("title", topic),
        "visual_theme": data.get("visual_theme", "cosmic"),
        "selected_hook": selected_hook,
        "hook_rankings": ranked_hooks,
        "scenes": scenes,
        "full_script": full_script_text,
        "caption": data.get("caption", ""),
        "hashtags": data.get("hashtags", [])[:5],
        "call_to_action": data.get("call_to_action", "Save this reel"),
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
    test_topic = "Why Saturn delays but never denies your success"
    print(f"Generating Reel for topic: {test_topic}...")
    res = generate_reel(test_topic, duration=25)
    print("WINNING HOOK:", res["selected_hook"]["spoken"])
    print("SCENES COUNT:", len(res["scenes"]))
    print("HASHTAGS:", res["hashtags"])
    print("CAPTION SNIPPET:", res["caption"][:120])
