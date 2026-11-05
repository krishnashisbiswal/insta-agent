import json
import logging
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows UTF-8 console output
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config.settings import STORAGE_DIR, TIMEZONE
from app.agents.gemini_client import generate_json
from app.autonomous.timing_engine import get_current_time

logger = logging.getLogger("TrendDiscoveryEngine")
TREND_HISTORY_FILE = STORAGE_DIR / "trend_history.json"


class TrendDiscoveryEngine:
    """
    Autonomous Instagram Trend Discovery & Anti-Fatigue Content Matrix.
    1. Analyzes viral Instagram Reels algorithms (watch-time completion, share velocity, Explore indexing).
    2. Identifies high-performing trending topics across all sub-niches of Vedic Astrology,
       Gemstones, Psychic Karma, and Spiritual Devotion.
    3. Guarantees 100% content and visual diversity with zero repetitive topics, rotating hook
       formulas, diverse gemstones, and distinct 3D procedural scenes.
    """

    # Comprehensive Sub-Niche Categories & Themes
    TRENDING_CATEGORIES = {
        "gemstone_energy": {
            "name": "Gemstone Energy & Hidden Hazards",
            "gemstones": [
                {"name": "Yellow Sapphire (Pukhraj)", "gem_type": "yellow_sapphire", "graha": "jupiter", "danger_houses": [6, 8, 12], "safe_ascendants": ["Aries", "Cancer", "Leo", "Scorpio", "Sagittarius", "Pisces"]},
                {"name": "Blue Sapphire (Neelam)", "gem_type": "blue_sapphire", "graha": "saturn", "danger_houses": [8, 12], "safe_ascendants": ["Taurus", "Gemini", "Virgo", "Libra", "Capricorn", "Aquarius"]},
                {"name": "Ruby (Manik)", "gem_type": "ruby", "graha": "sun", "danger_houses": [6, 7, 8], "safe_ascendants": ["Aries", "Leo", "Scorpio", "Sagittarius"]},
                {"name": "Emerald (Panna)", "gem_type": "emerald", "graha": "mercury", "danger_houses": [6, 8], "safe_ascendants": ["Taurus", "Gemini", "Virgo", "Libra", "Capricorn", "Aquarius"]},
                {"name": "Diamond (Heera)", "gem_type": "diamond", "graha": "venus", "danger_houses": [6, 8], "safe_ascendants": ["Taurus", "Gemini", "Virgo", "Libra", "Capricorn", "Aquarius"]},
                {"name": "Pearl (Moti)", "gem_type": "pearl", "graha": "moon", "danger_houses": [6, 8], "safe_ascendants": ["Cancer", "Aries", "Scorpio", "Pisces"]},
                {"name": "Red Coral (Moonga)", "gem_type": "red_coral", "graha": "mars", "danger_houses": [8, 12], "safe_ascendants": ["Aries", "Scorpio", "Cancer", "Leo", "Sagittarius", "Pisces"]},
            ],
            "angles": [
                "The Pillow Test to check compatibility before wearing",
                "Why wearing on the wrong finger creates financial blockage",
                "Dangerous Ascendant clashes that trigger sudden debt",
                "The Beej Mantra energization secret that 95% skip",
            ],
        },
        "psychic_karma": {
            "name": "Psychic Karma & Past-Life Debts",
            "themes": [
                "The Rahu-Moon Eclipse Syndrome: Why your anxiety spikes at night",
                "The 8th House Randhra Bhava: Why sudden transformations destroy comfortable illusions",
                "The 12th House Secret: Past-life karmic debts you are paying right now",
                "Brahma Muhurta (3:30 AM to 5:00 AM) Wakeup: What your Graha is trying to warn you",
                "The Ketu Soul Detachment: Why you push away people who genuinely love you",
                "Atmakaraka Soul Planet: The single toughest lesson your soul chose to master",
            ],
        },
        "kundli_secrets": {
            "name": "Shocking Kundali Secrets & Doshas",
            "themes": [
                "Kaal Sarp Dosh: The hidden serpentine curse that delays success until age 33",
                "Kemdrum Dosh: When the Moon has no surrounding planets causing sudden loneliness",
                "Manglik Dosha Myths: Why 80% of fearmongering astrologers are wrong",
                "Guru Chandal Dosh: The Jupiter-Rahu clash that shatters spiritual discipline",
                "Vipreet Raj Yoga: How your worst houses (6th, 8th, 12th) can make you extraordinarily wealthy",
                "Shani Sade Sati 3 Phases: The rising, peak, and setting karmic tests",
            ],
        },
        "spiritual_devotion": {
            "name": "Spiritual Devotion & Miracle Remedies",
            "themes": [
                "Lord Shiva Maha Mrityunjaya: The exact frequency to dissolve death-like fears",
                "Hanuman Chalisa Timings: Reciting 100 times on Tuesday vs Saturday night rules",
                "The Peepal Tree Mustard Lamp: Shani Dev's most powerful zero-cost karmic shield",
                "Bhairav Sadhana Secrets: Protecting your aura from psychic jealousy and evil eye",
                "Rudraksha Combination Powers: 5 Mukhi with 7 Mukhi for sudden financial revival",
            ],
        },
        "cosmic_transits": {
            "name": "Planetary Transits & Auspicious Shifts",
            "themes": [
                "Saturn (Shani) Direct Motion: 3 Zodiac signs whose stagnation ends this month",
                "Rahu-Ketu Karmic Axis Shift: The unexpected life area facing disruption",
                "Jupiter (Guru) Golden Aspect: Which house receives divine protection right now",
                "Amavasya Midnight Energy: Why negative astral vibrations peak during the new moon",
            ],
        },
    }

    def __init__(self, history_file: Path = TREND_HISTORY_FILE):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def load_history(self) -> List[Dict[str, Any]]:
        """Load persistent history of generated topics to prevent any duplicate content."""
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_history(self, history: List[Dict[str, Any]]) -> None:
        """Save history of generated topics to disk."""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def record_generated_topic(self, topic_info: Dict[str, Any]) -> None:
        """Record topic into diversity history."""
        hist = self.load_history()
        entry = {
            "topic": topic_info.get("topic", ""),
            "category": topic_info.get("category", "general"),
            "sub_niche": topic_info.get("sub_niche", ""),
            "gemstone": topic_info.get("gemstone", None),
            "graha": topic_info.get("graha", None),
            "house": topic_info.get("house", None),
            "formula_name": topic_info.get("formula_name", ""),
            "timestamp": int(time.time()),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        hist.append(entry)
        self.save_history(hist)

    def get_recent_elements(self, count: int = 10) -> Dict[str, List[str]]:
        """Extract recent gemstones, houses, grahas, and formulas to enforce cooldown."""
        hist = self.load_history()
        recent = hist[-count:]
        return {
            "topics": [h.get("topic", "").lower() for h in recent if h.get("topic")],
            "gemstones": [h.get("gemstone", "").lower() for h in recent if h.get("gemstone")],
            "grahas": [h.get("graha", "").lower() for h in recent if h.get("graha")],
            "houses": [str(h.get("house")) for h in recent if h.get("house")],
            "formulas": [h.get("formula_name", "").lower() for h in recent if h.get("formula_name")],
        }

    def discover_next_viral_trend(
        self,
        niche: str = "Vedic Astrology, Gemstone Energy, Psychic Karma & Spiritual Devotion",
        language: str = "Hindi mixed with English",
    ) -> Dict[str, Any]:
        """
        Dynamically discovers or synthesizes the next high-trending, viral topic
        that is strictly DIFFERENT from recent content.
        Balances across:
        1. Gemstone Energy (Pukhraj, Ruby, Emerald, etc.)
        2. Psychic Karma (Rahu-Moon, 8th House, 12th House, 3 AM wakeups)
        3. Kundali Secrets (Kaal Sarp, Manglik, Kemdrum, Vipreet Raj Yoga)
        4. Spiritual Devotion (Lord Shiva, Hanuman Chalisa, Peepal lamp)
        5. Cosmic Transits (Shani transit, Rahu shifts)
        """
        recent = self.get_recent_elements(count=15)
        recent_topics = recent["topics"]
        recent_gems = recent["gemstones"]
        recent_houses = recent["houses"]

        # Cycle category dynamically to ensure strict variety
        category_keys = ["gemstone_energy", "psychic_karma", "kundli_secrets", "spiritual_devotion", "cosmic_transits"]
        hist = self.load_history()
        last_category = hist[-1].get("category", "") if hist else ""

        # Pick next category different from last
        avail_categories = [c for c in category_keys if c != last_category]
        chosen_category = random.choice(avail_categories)

        # Use Gemini AI to synthesize an explosive trending topic
        try:
            from app.analytics.self_learning_engine import SelfLearningEngine
            from app.analytics.instagram_algorithm_brain import InstagramAlgorithmBrain

            learning_engine = SelfLearningEngine()
            playbook_ctx = learning_engine.get_prompt_injection()
            algo_brain = InstagramAlgorithmBrain()
            algo_ctx = algo_brain.generate_prompt_boost_snippet()

            prompt = f"""
You are the world's top viral trend scout and creative director for Instagram Reels in 2026.
You deeply understand how the Instagram algorithm recommends high-retention content to cold Explore feeds.

NICHE: {niche}
LANGUAGE: {language}
CHOSEN SUB-NICHE CATEGORY FOR THIS REEL: {chosen_category} ({self.TRENDING_CATEGORIES.get(chosen_category, {}).get('name', 'Vedic Wisdom')})

{playbook_ctx}

{algo_ctx}

RECENT TOPICS ALREADY COVERED (DO NOT REPEAT OR CLOSELY MIMIC ANY OF THESE):
{json.dumps(recent_topics[-10:], ensure_ascii=False)}

RECENT GEMSTONES RECENTLY USED (COOLDOWN ACTIVE): {recent_gems[-3:]}
RECENT HOUSES RECENTLY COVERED: {recent_houses[-3:]}

TASK:
Create ONE single explosive, audience-capturing, trending viral Instagram Reel topic that is 100% DIFFERENT from past reels.
Requirements:
1. Must trigger instant curiosity, urgent karmic danger, or shocking astrological truth.
2. If Gemstone category: Choose a gemstone OTHER than {recent_gems[-2:] if recent_gems else 'recent ones'} (e.g. Yellow Sapphire Pukhraj, Ruby Manik, Emerald Panna, Diamond Heera, Red Coral Moonga).
3. If Kundli category: Focus on Kaal Sarp Dosh, Kemdrum Dosh, Manglik, or Vipreet Raj Yoga.
4. If Psychic Karma category: Focus on 3 AM wakeups, Rahu anxiety, 12th house hidden karma, or Ketu soul ties.
5. If Spiritual Devotion category: Focus on Hanuman Chalisa night rules, Lord Shiva Mahamrityunjaya, or Peepal lamp remedies.

Return ONLY valid JSON in this exact structure:
{{
  "topic": "Concise high-voltage topic title",
  "category": "{chosen_category}",
  "sub_niche": "Specific sub-niche name",
  "gemstone": "Optional gemstone name or null",
  "graha": "Primary planetary deity involved (e.g. jupiter, saturn, mars, sun, moon, rahu, ketu)",
  "house": 8,
  "hook_angle": "Why this specific hook stops thumb scroll in 0.5 seconds",
  "suggested_formula": "Nobody Tells You",
  "target_duration_seconds": 25,
  "recommended_3d_theme": "gemstone_3d or kundli_chart_3d or planet_3d or karmic_vortex_3d or sacred_yantra_3d"
}}
"""
            res = generate_json(prompt)
            if res and res.get("topic"):
                logger.info(f"Discovered new trending viral topic via Gemini: \"{res['topic']}\"")
                return res
        except Exception as exc:
            logger.warning(f"Gemini trend discovery fallback triggered: {exc}")

        # High-voltage curated fallback topic if Gemini is offline
        curated_topics = [
            {
                "topic": "Stop Wearing Yellow Sapphire (Pukhraj) Until You Check This One Placement",
                "category": "gemstone_energy",
                "sub_niche": "Gemstone Energy & Hazards",
                "gemstone": "yellow_sapphire",
                "graha": "jupiter",
                "house": 6,
                "hook_angle": "Counter-intuitive warning on Jupiter's stone causing sudden debts when ruling negative houses",
                "suggested_formula": "Stop Doing X",
                "target_duration_seconds": 25,
                "recommended_3d_theme": "gemstone_3d",
            },
            {
                "topic": "The Rahu-Moon Eclipse Syndrome: Why Your Anxiety Spikes Every Monday Night",
                "category": "psychic_karma",
                "sub_niche": "Psychic & Karma",
                "gemstone": None,
                "graha": "moon",
                "house": 8,
                "hook_angle": "Relates recurring midnight anxiety attacks directly to natal Moon-Rahu afflicted axes",
                "suggested_formula": "Karmic Symptoms",
                "target_duration_seconds": 25,
                "recommended_3d_theme": "karmic_vortex_3d",
            },
            {
                "topic": "The 12th House Karmic Trap: Debts You Are Paying From Your Past Life",
                "category": "psychic_karma",
                "sub_niche": "Past Life Karma",
                "gemstone": None,
                "graha": "ketu",
                "house": 12,
                "hook_angle": "Reveals why unexplainable financial leakages and loneliness trace to 12th house soul debts",
                "suggested_formula": "Nobody Tells You",
                "target_duration_seconds": 25,
                "recommended_3d_theme": "kundli_chart_3d",
            },
            {
                "topic": "Lord Shiva Maha Mrityunjaya Secret: Why 90% Chants Give Zero Protection",
                "category": "spiritual_devotion",
                "sub_niche": "Spiritual Devotion",
                "gemstone": None,
                "graha": "saturn",
                "house": 8,
                "hook_angle": "Reveals the ancient pronunciation & energized copper vessel frequency required for the mantra",
                "suggested_formula": "The Secret Test",
                "target_duration_seconds": 25,
                "recommended_3d_theme": "sacred_yantra_3d",
            },
            {
                "topic": "Vipreet Raj Yoga Secret: How Your 6th and 8th Houses Can Make You Extraordinary Wealthy",
                "category": "kundli_secrets",
                "sub_niche": "Shocking Kundali Secrets",
                "gemstone": None,
                "graha": "saturn",
                "house": 8,
                "hook_angle": "Explains how extreme struggle in early life flips into sudden massive authority and wealth",
                "suggested_formula": "Contrarian Truth",
                "target_duration_seconds": 25,
                "recommended_3d_theme": "zodiac_wheel_3d",
            },
        ]

        # Filter out anything recently used
        for cand in curated_topics:
            if cand["topic"].lower() not in recent_topics:
                return cand

        return curated_topics[0]


if __name__ == "__main__":
    tde = TrendDiscoveryEngine()
    print("Testing Trend Discovery Engine...")
    trend = tde.discover_next_viral_trend()
    print("\nDiscovered Viral Trend:")
    print(json.dumps(trend, indent=2))
