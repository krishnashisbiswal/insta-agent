"""
Niche Configuration and Profile Management.

Decouples all content generation, scripting, visual styling, and voice synthesis
from any single hardcoded domain. Supports arbitrary custom niches, preset libraries,
and dynamic AI-assisted niche detection.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NicheProfile:
    niche_id: str
    name: str
    sub_niches: List[str] = field(default_factory=list)
    target_audience: str = "Broad general audience interested in self-improvement and education."
    language: str = "English"
    tone: str = "Authoritative, insightful, engaging, and high-energy"
    content_pillars: List[str] = field(default_factory=list)
    visual_style: str = "Modern, clean, cinematic typography with rich contrast"
    audio_style: str = "Clear, articulate voiceover with ambient background audio"
    cta_presets: List[str] = field(
        default_factory=lambda: [
            "Save this reel for later reference.",
            "Share this with someone who needs to see it.",
            "Drop your thoughts in the comments below.",
            "Send us a DM to learn more.",
        ]
    )
    prohibited_terms: List[str] = field(default_factory=list)
    terminology_glossary: Dict[str, str] = field(default_factory=dict)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NicheProfile:
        return cls(**data)


# ---------------------------------------------------------------------------
# PRESET BUILT-IN NICHE PROFILES
# ---------------------------------------------------------------------------
BUILTIN_NICHES: Dict[str, NicheProfile] = {
    "tech_ai": NicheProfile(
        niche_id="tech_ai",
        name="Technology & Artificial Intelligence",
        sub_niches=["AI Tools", "Machine Learning", "Software Development", "Future Tech", "Tech Productivity"],
        target_audience="Developers, tech enthusiasts, creators, and professionals seeking workflow automation.",
        language="English",
        tone="Cutting-edge, insightful, concise, analytical, and forward-looking",
        content_pillars=["AI Workflow Hacks", "Breakthrough Model Releases", "Code in 60 Seconds", "Tech Industry Shifts"],
        visual_style="Dark cybernetic background, neon cyan and violet accents, crisp sans-serif monospace code styling",
        audio_style="Modern confident tech presenter, clear and fast-paced",
        cta_presets=[
            "Comment 'AI' to receive the full step-by-step workflow guide.",
            "Save this to implement into your stack this week.",
            "Follow for daily deep-dives into modern artificial intelligence.",
        ],
        terminology_glossary={
            "LLM": "large language model",
            "API": "A-P-I",
            "RAG": "retrieval augmented generation",
            "GPU": "G-P-U",
        },
    ),
    "fitness_wellness": NicheProfile(
        niche_id="fitness_wellness",
        name="Fitness, Gym & Nutrition",
        sub_niches=["Hypertrophy", "Fat Loss", "High-Protein Meals", "Mobility", "Discipline"],
        target_audience="Men and women aged 18-40 wanting strength, fat loss, energy, and optimal fitness habits.",
        language="English",
        tone="Energetic, motivating, science-grounded, tough-love, and practical",
        content_pillars=["Form Corrections", "Macro Hacks", "High-Protein Recipes", "Discipline Protocols"],
        visual_style="High-contrast athletic imagery, bold yellow and white impact typography, gym/nature aesthetic",
        audio_style="Deep energetic motivational tone with driving rhythm",
        cta_presets=[
            "Save this workout for your next gym session.",
            "Send this to your workout partner right now.",
            "Comment 'TRAIN' for the complete PDF workout split.",
        ],
    ),
    "personal_finance": NicheProfile(
        niche_id="personal_finance",
        name="Personal Finance & Investing",
        sub_niches=["Index Funds", "Budgeting", "Real Estate", "Tax Efficiency", "Side Hustles"],
        target_audience="Young professionals and investors building passive income and long-term financial freedom.",
        language="English",
        tone="Sober, strategic, empowering, data-driven, and trustworthy",
        content_pillars=["Compound Interest Visuals", "Mistakes That Keep People Poor", "Index Fund Investing", "Cash Flow Habits"],
        visual_style="Rich emerald green, gold, and dark navy palette with clean financial graphs and bold serif headers",
        audio_style="Composed, trustworthy financial advisor with measured cadence",
        cta_presets=[
            "Save this to review before your next paycheck.",
            "Share this with someone who needs to start investing.",
            "Comment 'WEALTH' for our beginner investing checklist.",
        ],
    ),
    "education_history": NicheProfile(
        niche_id="education_history",
        name="Science, History & Big Ideas",
        sub_niches=["Untold History", "Astrophysics", "Psychology Experiments", "Evolution", "Archaeology"],
        target_audience="Curious lifelong learners fascinated by world mysteries, scientific breakthroughs, and historical drama.",
        language="English",
        tone="Dramatic, storytelling, intellectually curious, and wonder-inducing",
        content_pillars=["Historical Turning Points", "Cosmic Wonders", "Psychological Paradoxes", "Forgotten Geniuses"],
        visual_style="Cinematic vintage documentary grading, warm amber and sepia, classic cinematic serif typography",
        audio_style="Dramatic narrative narrator, thoughtful with dramatic pauses",
        cta_presets=[
            "Follow for more forgotten history and universe deep dives.",
            "Did you know about this before? Tell us in the comments.",
            "Save this story to blow someone's mind later.",
        ],
    ),
    "astrology_vedic": NicheProfile(
        niche_id="astrology_vedic",
        name="Vedic Astrology & Planetary Karma",
        sub_niches=["Planetary Transits", "Kundli Placement", "Karmic Remedies", "Gemstone Science", "Zodiac Shifts"],
        target_audience="Spiritual seekers and people undergoing planetary dasha/transits seeking clarity and authentic guidance.",
        language="Hindi mixed with English",
        tone="Spiritual, reverent, mystical, grounded, and solution-focused",
        content_pillars=["Planetary Transit Warnings", "House Placement Truths", "Gemstone Compatibility", "Karmic Remedies"],
        visual_style="Deep space cosmic gradients, sacred sacred geometry, warm gold borders, luminous celestial spheres",
        audio_style="Respectful authoritative spiritual guide with precise Sanskrit pronunciation",
        cta_presets=[
            "Comment your planetary placement below for a personalized remedy.",
            "Book your 1-on-1 consultation through direct message (DM).",
            "Save this reel before your planetary transit begins.",
        ],
        terminology_glossary={
            "Shani": "Shuh-nee",
            "Ketu": "Kay-too",
            "Rahu": "Rah-hoo",
            "Kundli": "Koon-dlee",
        },
    ),
}


class NicheRegistry:
    """
    Registry for storing, loading, and querying niche profiles.
    """

    def __init__(self, custom_dir: Optional[Path] = None):
        self.profiles: Dict[str, NicheProfile] = dict(BUILTIN_NICHES)
        from config.settings import STORAGE_DIR
        self.custom_dir = custom_dir or (STORAGE_DIR / "niches")
        self.custom_dir.mkdir(parents=True, exist_ok=True)
        self._load_custom_profiles()

    def get(self, niche_id: str) -> NicheProfile:
        key = niche_id.strip().lower()
        if key in self.profiles:
            return self.profiles[key]
        # Return fallback generic profile
        return NicheProfile(
            niche_id=key,
            name=niche_id.replace("_", " ").title(),
            target_audience=f"Audience interested in {niche_id}",
        )

    def register(self, profile: NicheProfile, persist: bool = True) -> None:
        self.profiles[profile.niche_id] = profile
        if persist:
            filepath = self.custom_dir / f"{profile.niche_id}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=2)
            logger.info(f"Persisted custom niche profile {profile.niche_id} to {filepath}")

    def list_all(self) -> List[NicheProfile]:
        return list(self.profiles.values())

    def _load_custom_profiles(self) -> None:
        for p in self.custom_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                profile = NicheProfile.from_dict(data)
                self.profiles[profile.niche_id] = profile
            except Exception as exc:
                logger.warning(f"Could not load custom niche from {p}: {exc}")


_registry_instance: Optional[NicheRegistry] = None


def get_default_niche(niche_id: Optional[str] = None) -> NicheProfile:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = NicheRegistry()
    from config.settings import CONTENT_NICHE
    target = niche_id or CONTENT_NICHE or "tech_ai"
    # Map common aliases
    alias_map = {
        "tech": "tech_ai",
        "ai": "tech_ai",
        "fitness": "fitness_wellness",
        "gym": "fitness_wellness",
        "finance": "personal_finance",
        "money": "personal_finance",
        "history": "education_history",
        "history_education": "education_history",
        "science": "education_history",
        "astrology": "astrology_vedic",
        "vedic": "astrology_vedic",
    }
    normalized = alias_map.get(target.strip().lower(), target.strip().lower())
    return _registry_instance.get(normalized)


def detect_niche_from_prompt(prompt_text: str) -> NicheProfile:
    """
    Analyzes prompt text to identify or synthesize the appropriate NicheProfile.
    """
    text_lower = prompt_text.lower()

    # Fast heuristic matching
    if any(k in text_lower for k in ["workout", "muscle", "protein", "gym", "squat", "fat loss", "fitness"]):
        return get_default_niche("fitness_wellness")
    if any(k in text_lower for k in ["invest", "stock", "budget", "money", "index fund", "wealth", "crypto", "finance"]):
        return get_default_niche("personal_finance")
    if any(k in text_lower for k in ["coding", "ai", "software", "chatgpt", "gemini", "algorithm", "python", "developer"]):
        return get_default_niche("tech_ai")
    if any(k in text_lower for k in ["history", "ancient", "century", "war", "emperor", "empire", "roman", "universe", "planet earth"]):
        return get_default_niche("education_history")
    if any(k in text_lower for k in ["kundli", "shani", "ketu", "rahu", "astrology", "horoscope", "zodiac", "gemstone"]):
        return get_default_niche("astrology_vedic")

    # If Gemini API available, synthesize dynamic profile
    try:
        from app.agents.gemini_client import generate_json
        ai_resp = generate_json(
            f"Given the user topic '{prompt_text}', identify the niche and return a JSON object with keys: "
            f"'niche_id', 'name', 'target_audience', 'language', 'tone', 'content_pillars', 'visual_style', 'audio_style', 'cta_presets'. "
            f"All values must be realistic production specifications for Instagram content."
        )
        if isinstance(ai_resp, dict) and "name" in ai_resp:
            return NicheProfile(
                niche_id=ai_resp.get("niche_id", "custom_detected"),
                name=ai_resp.get("name", "Custom Niche"),
                target_audience=ai_resp.get("target_audience", "Instagram Audience"),
                language=ai_resp.get("language", "English"),
                tone=ai_resp.get("tone", "Engaging and authoritative"),
                content_pillars=ai_resp.get("content_pillars", ["Insights", "Tips", "Analysis"]),
                visual_style=ai_resp.get("visual_style", "Clean modern aesthetic with crisp typography"),
                audio_style=ai_resp.get("audio_style", "Engaging narrator"),
                cta_presets=ai_resp.get("cta_presets", ["Save this post for reference", "Comment below"]),
            )
    except Exception as exc:
        logger.warning(f"AI niche detection fallback to tech_ai: {exc}")

    return get_default_niche("tech_ai")
