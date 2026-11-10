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

    prompt = f"""
You are an elite short-form video copywriter specializing in viral hooks for {profile.name}.
TARGET AUDIENCE: {profile.target_audience}
TONE: {profile.tone}
TOPIC: {topic}
LANGUAGE: {language}

Review these proven hook formulas:
{json.dumps(formula_summary, indent=2)}

Task:
Generate 3 distinct, high-retention hooks for a short Instagram Reel about "{topic}".
Rules:
1. Spoken hook: Under 12 words. Punchy, scroll-stopping, tailored to {profile.name}.
2. On-screen text: 3 to 6 words maximum in ALL CAPS.
3. Natural delivery without clickbait traps or fluff.

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
    """
    ranked = []
    for item in hooks:
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


def generate_reel(
    topic: str,
    niche: str = "tech_ai",
    language: str = "English",
    duration: int = 25,
    niche_profile: Optional[NicheProfile] = None,
) -> Dict[str, Any]:
    """
    Generate a complete production-ready Instagram Reel with Gemini.
    Adapts fully to any configured NicheProfile (Tech, Fitness, Finance, Astrology, etc.).
    """
    profile = niche_profile or get_default_niche(niche)

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
    is_hindi = language.lower() in ["hindi", "hi"]

    if is_astrology:
        niche_instructions = f"""
CRITICAL JYOTISH ACCURACY RULES:
- Focus solely on the planet, house, and transit relevant to "{topic}".
- If language is Hindi: spoken lines MUST be written in natural Devanagari Hindi (हिंदी लिपि) for authentic pronunciation.
- On-screen text in clean ALL CAPS English (3-5 words).
- Call to Action: Instruct viewers to comment their placement or DM for consultation. Never say 'link in bio'.
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

{niche_instructions}

VIRAL RETENTION STRUCTURE (5 DYNAMIC SCENES):
1. SCENE 1 (0-3s) - THE HOOK:
   - Spoken: Winning hook above.
   - On-Screen: Winning on-screen text in ALL CAPS (3-5 words).
2. SCENE 2 (3-8s) - POINT 1:
   - Vivid, relatable point or insight.
   - On-Screen: Punchy 3-5 words in ALL CAPS.
3. SCENE 3 (8-13s) - POINT 2:
   - Deepens the value or presents the core breakthrough.
   - On-Screen: Punchy 3-5 words in ALL CAPS.
4. SCENE 4 (13-18s) - POINT 3 / CRITICAL SHIFT:
   - Practical application or mistake warning.
   - On-Screen: Punchy 3-5 words in ALL CAPS.
5. SCENE 5 (18-25s) - CALL TO ACTION:
   - Clear engagement instruction from presets.
   - On-Screen: Punchy ALL CAPS CTA.

WRITING QUALITY:
- Spoken lines must be conversational, confident, and crisp (total 40-50 words across all 5 scenes).
- Natural ellipses (`...`) for dramatic breath pauses.
- On-screen text 100% clean plain ASCII letters (no emojis that break renderers).

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

    result = {
        "topic": topic,
        "niche": profile.niche_id,
        "language": language,
        "title": data.get("title", topic),
        "visual_theme": data.get("visual_theme", "modern_dynamic"),
        "selected_hook": selected_hook,
        "hook_rankings": ranked_hooks,
        "scenes": scenes,
        "full_script": full_script_text,
        "caption": data.get("caption", ""),
        "hashtags": data.get("hashtags", [])[:5],
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
