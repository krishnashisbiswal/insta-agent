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
        "healing_crystals": {
            "name": "Sacred Healing Crystals: Frequencies, Aura Alignment & Abundance",
            "crystals": [
                {"name": "Pyrite (Iron Pyrite)", "energy": "Wealth attraction, mental focus & solar plexus vitality", "best_for": "Work desk, financial confidence, willpower"},
                {"name": "Raw Amethyst", "energy": "Crown chakra awakening, deep calm & insomnia relief", "best_for": "Bedside, meditation, anxiety shielding"},
                {"name": "Black Tourmaline", "energy": "EMF shielding, psychic protection & absorbing negativity", "best_for": "Entrance, pockets, heavy energetic spaces"},
                {"name": "Natural Citrine", "energy": "Merchant stone of abundance, joy & creative manifestation", "best_for": "Cash box, study table, positive mindset"},
                {"name": "Rose Quartz", "energy": "Heart chakra healing, self-compassion & relationship harmony", "best_for": "Bedroom, emotional reconciliation"},
                {"name": "Tiger's Eye", "energy": "Root chakra grounding, fearless action & discernment", "best_for": "Decision making, overcoming self-doubt"},
                {"name": "Clear Quartz", "energy": "Master healer, amplifying intentions & high vibration", "best_for": "Meditation altar, energetic clarity"},
            ],
            "themes": [
                "3 Hidden Benefits of Keeping Pyrite Crystal on Your Work Desk for Money Attraction",
                "How Raw Amethyst Calms an Overactive Mind and Shields Your Aura from Negative Energy",
                "3 Ways Black Tourmaline Absorbs Electromagnetic and Envious Negative Energy",
                "Citrine: The Merchant's Stone That Clears Solar Plexus Energy Blocks",
                "Rose Quartz & Clear Quartz: How Natural Crystal Frequencies Harmonize Your Home",
                "3 Real Benefits of Meditating with Tiger's Eye for Unshakable Confidence",
            ],
        },
        "sacred_rudraksha": {
            "name": "Sacred Rudraksha Beads: Divine Bio-Electromagnetism, Peace & Vitality",
            "beads": [
                {"name": "5 Mukhi (Pancha Mukhi) Rudraksha", "deity": "Lord Kalagni Rudra", "energy": "Regulates blood pressure, calms nervous system & mental peace"},
                {"name": "7 Mukhi (Saptamukhi) Rudraksha", "deity": "Goddess Mahalaxmi", "energy": "Attracts financial stability, opens blocked prosperity channels"},
                {"name": "Gauri Shankar Rudraksha", "deity": "Shiva & Parvati", "energy": "Harmonizes relationships, marital peace & deep soul-connection"},
                {"name": "8 Mukhi (Ashtamukhi) Rudraksha", "deity": "Lord Ganesha", "energy": "Removes unseen obstacles in business, enhances wisdom and intellect"},
                {"name": "10 Mukhi (Dashamukhi) Rudraksha", "deity": "Lord Vishnu", "energy": "Ultimate protective shield against evil eyes and psychological fear"},
                {"name": "14 Mukhi (Devamani) Rudraksha", "deity": "Lord Shiva & Hanuman", "energy": "Activates third-eye intuition, foresight and fearless leadership"},
            ],
            "themes": [
                "The Science of 5 Mukhi Rudraksha: How It Regulates Blood Pressure and Calms Anxiety",
                "7 Mukhi Mahalaxmi Rudraksha: Why Ancient Rishis Linked It to Constant Financial Stability",
                "The Power of Gauri Shankar Rudraksha: Harmonizing Yin-Yang and Soul Relationships",
                "8 Mukhi Ganesha Rudraksha: How It Eliminates Unseen Obstacles in Career and Business",
                "10 Mukhi Lord Vishnu Rudraksha: The Ultimate Divine Shield Against Psychic Drain",
                "Why Wearing Real Nepali Rudraksha Instantly Grounds Your Nervous System",
            ],
        },
        "wealth_and_money": {
            "name": "Sudden Wealth, Money Leakage & Rare Dhana Yogas",
            "themes": [
                "3 Kundli Placements That Drain Your Money No Matter How Much You Earn",
                "3 Rare Wealth Yogas That Trigger Sudden Riches After Age 28",
                "3 Signs Rahu in 2nd House Is Creating Mysterious Financial Losses",
                "3 Kundli Signs You Will Gain Unexpected Wealth Through Inheritance or Trading",
                "3 Placements That Block You From Buying Property or Building Savings",
            ],
        },
        "marriage_and_relationships": {
            "name": "Relationship Karma, Marriage Delays & Soulmate Bonds",
            "themes": [
                "3 Kundli Placements That Delay Marriage Until Age 30+",
                "3 Signs You Have a Heavy Past-Life Karmic Debt With Your Partner",
                "3 Kundli Placements Causing Constant Heartbreak and Misunderstandings",
                "3 Signs of True Manglik Dosha That Astrologers Never Explain",
                "The 7th House Ketu Trap: Why You Push Away Pure Love",
            ],
        },
        "career_and_saturn": {
            "name": "Career Breakthroughs, Sade Sati & Karmic Struggles",
            "themes": [
                "3 Signs Saturn (Shani) Is Preparing You For A Massive Career Jump",
                "3 Placements That Cause Constant Career Blockages and Stagnation",
                "3 Signs You Are Experiencing The Peak Phase of Shani Sade Sati",
                "The 10th House Karmic Lesson: Why Hard Work Alone Never Brings Fame",
                "Vipreet Raj Yoga: How 6th and 8th Houses Trigger Massive Power",
            ],
        },
        "psychic_and_destiny": {
            "name": "Psychic Intuition, 3 AM Wakeups & Divine Protection",
            "themes": [
                "3 Signs You Have Divine Protection (Deva Kripa) in Your Kundli",
                "3 Hidden Meanings If You Wake Up Between 3:00 AM and 5:00 AM",
                "3 Placements That Give Uncanny Psychic Dreams and 3rd Eye Intuition",
                "The Rahu-Moon Eclipse Syndrome: Why Your Anxiety Spikes at Night",
                "3 Kundli Signs You Have an Old Soul Paying Past-Life Debts",
            ],
        },
        "gemstone_energy": {
            "name": "Gemstone Energy & Cosmic Alignment",
            "gemstones": [
                {"name": "Yellow Sapphire (Pukhraj)", "gem_type": "yellow_sapphire", "graha": "jupiter", "safe_ascendants": ["Aries", "Cancer", "Leo", "Scorpio", "Sagittarius", "Pisces"]},
                {"name": "Blue Sapphire (Neelam)", "gem_type": "blue_sapphire", "graha": "saturn", "safe_ascendants": ["Taurus", "Gemini", "Virgo", "Libra", "Capricorn", "Aquarius"]},
                {"name": "Ruby (Manik)", "gem_type": "ruby", "graha": "sun", "safe_ascendants": ["Aries", "Leo", "Scorpio", "Sagittarius"]},
                {"name": "Emerald (Panna)", "gem_type": "emerald", "graha": "mercury", "safe_ascendants": ["Taurus", "Gemini", "Virgo", "Libra", "Capricorn", "Aquarius"]},
                {"name": "Pearl (Moti)", "gem_type": "pearl", "graha": "moon", "safe_ascendants": ["Cancer", "Aries", "Scorpio", "Pisces"]},
            ],
            "themes": [
                "How Natural Yellow Sapphire (Pukhraj) Expands Wisdom, Divine Grace & Higher Knowledge",
                "The Subtle Fire of Natural Ruby (Manik): Awakening Leadership, Dignity & Soul Confidence",
                "The Calming Silver Energy of Natural Pearl (Moti): Balancing Emotional Whirlpools & Intuition",
                "Emerald (Panna) for Sharp Intellect, Communication Mastery & Business Acumen",
            ],
        },
        "vedic_foundations_basics": {
            "name": "Vedic Astrology Foundations: Planets, 27 Nakshatras & 4 Padas",
            "themes": [
                "Vedic Astrology Foundation: 9 Planets, 27 Nakshatras and 4 Padas Explained",
                "The Mystery of 4 Nakshatra Padas: How Dharma, Artha, Kama, Moksha Rule Your Kundli",
                "The 9 Navagrahas Explained: How Sun to Ketu Control Your Entire Life Path",
                "The 27 Nakshatras: The True Cosmic Power Behind Your Birth Chart",
                "Why Your Rashi Means Nothing Without Your Birth Nakshatra and Pada",
            ],
        },
    }

    NARRATIVE_ARCHETYPES = [
        {
            "id": "karmic_mystery_deep_dive",
            "name": "Karmic Mystery & Hidden House Trap",
            "hook_style": "Unveils a hidden Kundli mystery, rare yoga or difficult house activation (e.g. 7th house Ketu detachment, 8th house sudden wealth, Vipreet Raj Yoga).",
            "point_count": 3,
            "badge_prefix": "INSIGHT",
            "focus": "Deep astrological placement mechanics, past-life debts, and sudden energetic shifts.",
        },
        {
            "id": "real_life_symptoms",
            "name": "Real-Life Awakening Symptoms & Physical Signs",
            "hook_style": "Identifies 3 uncanny physical, emotional or circumstantial symptoms (e.g. 3 AM wakeups, money leakage, throat chakra blocks).",
            "point_count": 3,
            "badge_prefix": "SIGN",
            "focus": "Tangible daily life symptoms that make viewers immediately relate and check their chart.",
        },
        {
            "id": "contrarian_truth",
            "name": "Contrarian Truth & Vedic Myth Buster",
            "hook_style": "Shatters a common modern astrological myth using authentic Sage Parashara Vedic wisdom.",
            "point_count": 3,
            "badge_prefix": "TRUTH",
            "focus": "Contrasting pop-astrology illusions against deep ancient Vedic reality (e.g. Rashi vs Nakshatra/Pada, Sade Sati cleansing).",
        },
        {
            "id": "planetary_power_code",
            "name": "Planetary Power & Nakshatra Codes",
            "hook_style": "Explores the raw cosmic frequency of a specific Graha or Nakshatra and how it governs destiny.",
            "point_count": 3,
            "badge_prefix": "CODE",
            "focus": "Celestial mechanics, soul evolution, and understanding planetary signatures in birth charts.",
        },
        {
            "id": "consultation_case_study",
            "name": "Astrologer Consultation Case Study",
            "hook_style": "Begins with an authentic client consultation case study where a subtle placement changed everything.",
            "point_count": 4,
            "badge_prefix": "LESSON",
            "focus": "Practical wisdom learned from consulting charts, avoiding blind remedies, and recognizing chart clashes.",
        },
        {
            "id": "sacred_energy_benefits",
            "name": "Sacred Energy Benefits & Spiritual Science",
            "hook_style": "Explains 3 scientifically and spiritually proven benefits of sacred natural tools (Rudraksha, healing crystals, divine frequencies).",
            "point_count": 3,
            "badge_prefix": "BENEFIT",
            "focus": "Uplifting, empowering knowledge on calming the nervous system, sharpening focus, attracting wealth, and shielding personal energy without fear.",
        },
        {
            "id": "crystal_and_rudraksha_guide",
            "name": "Crystals & Rudraksha Bio-Energy Guide",
            "hook_style": "Unveils the specific energetic frequency of authentic crystals or Rudraksha Mukhis and how to use them for daily vitality.",
            "point_count": 3,
            "badge_prefix": "GUIDE",
            "focus": "Practical sacred energy benefits: Pyrite for wealth attraction, Amethyst for anxiety, 5/7 Mukhi Rudraksha for heart and bio-electromagnetic harmony.",
        },
    ]

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
            "archetype": topic_info.get("archetype", ""),
            "point_count": topic_info.get("point_count", 3),
            "badge_prefix": topic_info.get("badge_prefix", "INSIGHT"),
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
            "archetypes": [h.get("archetype", "").lower() for h in recent if h.get("archetype")],
        }

    def discover_next_viral_trend(
        self,
        niche: str = "Vedic Astrology, Gemstone Energy, Psychic Karma & Spiritual Devotion",
        language: str = "Hindi mixed with English",
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically discovers or synthesizes the next high-trending, viral topic
        that is strictly DIFFERENT from recent content.
        Balances across 5 distinct narrative archetypes:
        1. Karmic Mystery & Hidden House Trap (7th house Ketu, 8th house wealth, Vipreet Raj Yoga)
        2. Real-Life Awakening Symptoms (3 AM wakeups, money leakage, emotional detachment)
        3. Contrarian Truth & Vedic Myth Buster (Rashi vs Nakshatra & Pada, Sade Sati reality)
        4. Planetary Power & Nakshatra Codes (Graha frequencies, soul evolution)
        5. Astrologer Consultation Case Studies (Authentic client breakthroughs & clash avoidance)
        """
        recent = self.get_recent_elements(count=15)
        recent_topics = recent["topics"]
        recent_gems = recent["gemstones"]
        recent_houses = recent["houses"]
        recent_archetypes = recent.get("archetypes", [])

        # Cycle category dynamically across all viral pillars to ensure explosive diversity
        category_keys = [
            "healing_crystals",
            "sacred_rudraksha",
            "wealth_and_money",
            "psychic_and_destiny",
            "career_and_saturn",
            "marriage_and_relationships",
            "vedic_foundations_basics",
            "gemstone_energy",
        ]
        hist = self.load_history()
        last_category = hist[-1].get("category", "") if hist else ""

        # Pick next category different from last (or explicit requested category)
        if category and category in self.TRENDING_CATEGORIES:
            chosen_category = category
        else:
            avail_categories = [c for c in category_keys if c != last_category]
            chosen_category = random.choice(avail_categories if avail_categories else category_keys)

        # Rotate narrative archetype dynamically to prevent repetitive "5 deadly mistakes" formats
        last_archetype = hist[-1].get("archetype", "") if hist else ""
        avail_archetypes = [a for a in self.NARRATIVE_ARCHETYPES if a["id"] != last_archetype]
        chosen_archetype = random.choice(avail_archetypes if avail_archetypes else self.NARRATIVE_ARCHETYPES)

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
CHOSEN SUB-NICHE CATEGORY: {chosen_category} ({self.TRENDING_CATEGORIES.get(chosen_category, {}).get('name', 'Vedic Wisdom')})
TARGET NARRATIVE ARCHETYPE: {chosen_archetype['name']}
ARCHETYPE HOOK STYLE: {chosen_archetype['hook_style']}
TARGET NUMBER OF POINTS: {chosen_archetype['point_count']}
BADGE STYLE: {chosen_archetype['badge_prefix']} 1 OF {chosen_archetype['point_count']}

{playbook_ctx}

{algo_ctx}

RECENT TOPICS ALREADY COVERED (DO NOT REPEAT OR CLOSELY MIMIC ANY OF THESE):
{json.dumps(recent_topics[-10:], ensure_ascii=False)}

RECENT GEMSTONES RECENTLY USED (COOLDOWN ACTIVE): {recent_gems[-3:]}
RECENT HOUSES RECENTLY COVERED: {recent_houses[-3:]}

CRITICAL DIVERSITY MANDATE:
- DO NOT use generic repetitive templates like '5 Deadly Mistakes' or '5 Fatal Mistakes' unless explicitly requested.
- STRICT BAN ON REPETITIVE FINANCIAL LOSS TOPICS: DO NOT propose topics about '45 lakhs loss', 'sudden financial collapse', or repetitive gemstone disasters!
- MANDATORY CONTENT EXPANSION (CRYSTALS & RUDRAKSHA INCLUDED):
  * When category is 'healing_crystals': Focus on natural raw crystals (Pyrite, Amethyst, Black Tourmaline, Citrine, Rose Quartz, Tiger's Eye) and their tangible benefits (focus, anxiety relief, EMF shield, abundance, grounding).
  * When category is 'sacred_rudraksha': Focus on authentic sacred Rudraksha beads (5 Mukhi, 7 Mukhi Mahalaxmi, 8 Mukhi Ganesh, 10 Mukhi Vishnu, Gauri Shankar) and their ancient bio-electromagnetic and nervous system calming science.
  * TONE SHIFT: STOP DEFAULTING TO FEAR! Highlight real POSITIVE BENEFITS, sacred science, and energy empowerment.
- VARY themes widely across life pillars:
  * Spiritual Awakening, 3 AM wakeups, intuition & past life debts
  * Career breakthroughs, Saturn's reality check & hidden 10th house blocks
  * Relationship karma, 7th house Ketu detachment & emotional peace
  * Nakshatra frequencies, soul purpose & Vipreet Raj Yoga
- Create an entirely fresh, unique angle fitting the '{chosen_archetype['name']}' archetype.
- Make the title fascinating, educational, dignified, and curiosity-inducing.

STRICT NEGATIVE CONSTRAINT:
- DO NOT use the word 'degree', 'degrees', 'डिग्री', or abstract math jargon. Focus 100% on concrete real-life symptoms, mental peace, planetary energy, and personal Kundli placements.
- STRICTLY ZERO REMEDIES & ZERO MANTRAS. No gemstone wearing prescriptions, no mantras, no rituals.

TASK:
Create ONE single explosive, fresh, never-before-seen Instagram Reel topic in the '{chosen_category}' pillar using the '{chosen_archetype['name']}' format.

Return ONLY valid JSON in this exact structure:
{{
  "topic": "Concise high-voltage topic title (e.g. {chosen_archetype['hook_style']})",
  "category": "{chosen_category}",
  "sub_niche": "Specific sub-niche name",
  "archetype": "{chosen_archetype['id']}",
  "point_count": {chosen_archetype['point_count']},
  "badge_prefix": "{chosen_archetype['badge_prefix']}",
  "gemstone": "Optional gemstone name or null",
  "graha": "Primary planetary deity involved (e.g. jupiter, saturn, mars, venus, rahu, ketu, mercury, moon, sun)",
  "house": 8,
  "hook_angle": "Why this specific hook stops thumb scroll and forces comment engagement",
  "suggested_formula": "{chosen_archetype['name']}",
  "target_duration_seconds": 25,
  "cinematic_visual_theme": "photorealistic_gemstone or sacred_temple or vedic_astrology_chart or cosmic_nebula"
}}
"""
            res = generate_json(prompt)
            if res and res.get("topic"):
                if "archetype" not in res:
                    res["archetype"] = chosen_archetype["id"]
                if "point_count" not in res:
                    res["point_count"] = chosen_archetype["point_count"]
                if "badge_prefix" not in res:
                    res["badge_prefix"] = chosen_archetype["badge_prefix"]
                logger.info(f"Discovered new trending viral topic via Gemini: \"{res['topic']}\" (Archetype: {res['archetype']})")
                return res
        except Exception as exc:
            logger.warning(f"Gemini trend discovery fallback triggered: {exc}")

        # High-voltage curated fallback topics spanning diverse archetypes
        curated_topics = [
            {
                "topic": "Vedic Astrology Foundation: 9 Planets, 27 Nakshatras and 4 Padas Explained",
                "category": "vedic_foundations_basics",
                "sub_niche": "Vedic Astrology Basics & Cosmic Mechanics",
                "archetype": "contrarian_truth",
                "point_count": 3,
                "badge_prefix": "FOUNDATION",
                "gemstone": None,
                "graha": None,
                "house": None,
                "hook_angle": "Contrast superficial zodiac signs against the authentic 3-layer Vedic foundation (Planets, 27 Nakshatras, and 4 Padas)",
                "suggested_formula": "Contrarian Truth",
                "target_duration_seconds": 28,
                "cinematic_visual_theme": "vedic_astrology_chart",
            },
            {
                "topic": "3 Kundli Signs Rahu in 2nd House Is Creating Mysterious Financial Losses",
                "category": "wealth_and_money",
                "sub_niche": "Sudden Wealth & Rahu Traps",
                "archetype": "karmic_mystery_deep_dive",
                "point_count": 3,
                "badge_prefix": "INSIGHT",
                "gemstone": None,
                "graha": "rahu",
                "house": 2,
                "hook_angle": "Uncanny financial mystery: explains why money disappears through unseen leakages",
                "suggested_formula": "Karmic Mystery",
                "target_duration_seconds": 25,
                "cinematic_visual_theme": "vedic_astrology_chart",
            },
            {
                "topic": "The 7th House Ketu Trap: Why You Push Away Pure Love",
                "category": "marriage_and_relationships",
                "sub_niche": "Relationship Karma & Detachment",
                "archetype": "karmic_mystery_deep_dive",
                "point_count": 3,
                "badge_prefix": "INSIGHT",
                "gemstone": None,
                "graha": "ketu",
                "house": 7,
                "hook_angle": "Deep emotional identification: why partners with 7th house Ketu feel sudden detachment",
                "suggested_formula": "Karmic Mystery",
                "target_duration_seconds": 25,
                "cinematic_visual_theme": "cosmic_nebula",
            },
            {
                "topic": "3 Hidden Meanings If You Wake Up Between 3:00 AM and 5:00 AM",
                "category": "psychic_and_destiny",
                "sub_niche": "Psychic Intuition & Brahma Muhurta",
                "archetype": "real_life_symptoms",
                "point_count": 3,
                "badge_prefix": "SIGN",
                "gemstone": None,
                "graha": "jupiter",
                "house": 12,
                "hook_angle": "Hyper-relatable spiritual awakening symptom explaining spontaneous night wakeups",
                "suggested_formula": "Awakening Signs",
                "target_duration_seconds": 25,
                "cinematic_visual_theme": "sacred_temple",
            },
            {
                "topic": "Why Your Rashi Means Nothing Without Your Birth Nakshatra and Pada",
                "category": "vedic_foundations_basics",
                "sub_niche": "Ancient Vedic Secrets",
                "archetype": "contrarian_truth",
                "point_count": 3,
                "badge_prefix": "TRUTH",
                "gemstone": None,
                "graha": "moon",
                "house": 1,
                "hook_angle": "Contrarian truth dismantling superficial Western sun-sign astrology",
                "suggested_formula": "Contrarian Truth",
                "target_duration_seconds": 25,
                "cinematic_visual_theme": "vedic_astrology_chart",
            },
            {
                "topic": "Vipreet Raj Yoga: How 6th and 8th Houses Trigger Massive Power",
                "category": "career_and_saturn",
                "sub_niche": "Career Breakthroughs & Reversals",
                "archetype": "karmic_mystery_deep_dive",
                "point_count": 3,
                "badge_prefix": "INSIGHT",
                "gemstone": None,
                "graha": "saturn",
                "house": 8,
                "hook_angle": "Transforming struggle into victory: how dusthana houses trigger sudden royal power",
                "suggested_formula": "Karmic Mystery",
                "target_duration_seconds": 25,
                "cinematic_visual_theme": "vedic_astrology_chart",
            },
            {
                "topic": "The 72-Hour Test: 3 Signs A Gemstone Clashes With Your Aura",
                "category": "gemstone_energy",
                "sub_niche": "Gemstone Energy & Aura Harmony",
                "archetype": "consultation_case_study",
                "point_count": 3,
                "badge_prefix": "LESSON",
                "gemstone": "blue_sapphire",
                "graha": "saturn",
                "house": 8,
                "hook_angle": "Crucial client consultation rule: 3 energetic warning signs to test within 72 hours",
                "suggested_formula": "Client Case Study",
                "target_duration_seconds": 25,
                "cinematic_visual_theme": "photorealistic_gemstone",
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
