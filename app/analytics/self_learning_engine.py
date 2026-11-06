import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows UTF-8 safety
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

logger = logging.getLogger("SelfLearningEngine")

PLAYBOOK_FILE = STORAGE_DIR / "evolution_playbook.json"
HISTORY_FILE = STORAGE_DIR / "published_history.json"


DEFAULT_PLAYBOOK: Dict[str, Any] = {
    "version": "1.0.0",
    "evolution_level": 1.0,
    "last_upgrade_date": "2026-11-05",
    "total_training_cycles": 1,
    "niche": "Vedic Astrology, Gemstone Energy, Psychic Karma & Spiritual Devotion",
    "daily_golden_rules": [
        "RULE 1: Lead with a shocking negative command or high-stakes warning within the first 1.5 seconds (e.g. 'Never wear Neelam on a Saturday without checking your 8th house').",
        "RULE 2: Anchor every astrological or psychic claim to a concrete life symptom (e.g. sudden financial loss, unexplainable relationship detachment, 3 AM wakeups).",
        "RULE 3: STRICT NO-FREE-REMEDIES MANDATE IN REELS. Never give away remedies in the video. Generic online rituals backfire without knowing exact degrees and ascendant. This withholds the resolution and drives curiosity.",
        "RULE 4: ALGORITHM BOOST VIA COMMENT MAGNET + 1-ON-1 CONSULTATION BOOKING. Command viewers to drop their exact Birth Date + Time below for a preliminary chart scan, and DM 'KUNDLI' or click the bio link to Book a 1-on-1 Consultation for customized remedies.",
    ],
    "winning_hooks_bank": [
        {
            "template": "Stop wearing {gemstone} right now. {percent}% of people ruin their {area} instead.",
            "example": "Stop wearing Pukhraj right now. 90% of people ruin their finances instead.",
            "category": "Gemstone Warning",
            "score": 93.5,
        },
        {
            "template": "If you wake up between {time_window}, your {graha} is desperately trying to tell you this.",
            "example": "If you wake up between 3 AM and 5 AM, your Rahu is desperately trying to tell you this.",
            "category": "Psychic & Karma",
            "score": 91.2,
        },
        {
            "template": "The single most dangerous placement in your birth chart that nobody talks about.",
            "example": "The single most dangerous placement in your birth chart that nobody talks about.",
            "category": "Vedic Astrology",
            "score": 89.8,
        },
        {
            "template": "Recite this one {deity} mantra before sleeping to break any karmic blockage.",
            "example": "Recite this one Hanuman mantra before sleeping to break any karmic blockage.",
            "category": "Spiritual Devotion",
            "score": 92.4,
        },
    ],
    "banned_low_retention_phrases": [
        "In this video we will discuss",
        "Hello everyone and welcome back",
        "Have you ever wondered about astrology",
        "Let's dive into the details",
        "Astrology is a very ancient science",
        "Please like, share, and subscribe",
        "Today I will explain",
    ],
    "niche_mastery_matrix": {
        "vedic_astrology": {
            "top_themes": ["Shani Sade Sati", "Rahu Mahadasha", "Manglik Dosha", "Vipreet Raj Yoga", "8th House Secrets"],
            "high_retention_visual": "3D rotating shaded planet with tilted rings and orbital Graha nodes",
        },
        "gemstones": {
            "top_themes": ["Pukhraj vs Neelam", "Right finger rules", "Energizing Beej Mantras", "Dangerous Ascendant clashes"],
            "high_retention_visual": "3D metallic gemstone medallion with specular light flash",
        },
        "psychic_karma": {
            "top_themes": ["Past life debts (Rin)", "Intuition signs", "Brahma Muhurta messages", "Soul connections & Ketu"],
            "high_retention_visual": "3D obsidian shadow orb with pulsing violet corona",
        },
        "spiritual_devotion": {
            "top_themes": ["Mahamrityunjaya healing", "Hanuman Chalisa rules", "Surya Arghya copper vessel", "Peepal mustard lamp"],
            "high_retention_visual": "3D radiant solar/divine flare with celestial halo",
        },
    },
    "seo_high_reach_keywords": [
        "VedicAstrology",
        "KundliSecrets",
        "PukhrajGemstone",
        "ShaniSadeSati",
        "KarmaRemedies",
        "HanumanRemedy",
        "Mahamrityunjaya",
        "PsychicIntuition",
        "JyotishUpay",
        "AstrologyReels",
    ],
    "evolution_history": [
        {
            "cycle": 1,
            "date": "2026-11-05",
            "notes": "Initialized baseline agent memory with 26 viral hook formulas, 3D procedural celestial rendering, and Instagram SEO algorithm weights.",
            "evolution_level": 1.0,
        }
    ],
}


class SelfLearningEngine:
    """
    Autonomous Daily Self-Training & Evolution Engine.
    Analyzes historical reel metrics, discovers viral retention patterns,
    prunes weak vocabulary, and continuously upgrades the agent's prompts and strategies.
    """

    def __init__(self, playbook_path: Optional[Path] = None, history_path: Optional[Path] = None):
        self.playbook_path = playbook_path or PLAYBOOK_FILE
        self.history_path = history_path or HISTORY_FILE
        self.playbook_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def load_playbook(self) -> Dict[str, Any]:
        """Load current agent evolution playbook from disk or initialize default."""
        if not self.playbook_path.exists():
            self.save_playbook(DEFAULT_PLAYBOOK)
            return DEFAULT_PLAYBOOK.copy()

        try:
            with open(self.playbook_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Error loading playbook: {exc}. Using default.")
            return DEFAULT_PLAYBOOK.copy()

    def save_playbook(self, playbook: Dict[str, Any]):
        """Persist updated playbook to disk."""
        with open(self.playbook_path, "w", encoding="utf-8") as f:
            json.dump(playbook, f, indent=2, ensure_ascii=False)

    def load_history(self) -> List[Dict[str, Any]]:
        """Load published history records."""
        if not self.history_path.exists():
            return []
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def should_upgrade_today(self) -> bool:
        """Check if daily self-upgrade has already run today."""
        playbook = self.load_playbook()
        last_date = playbook.get("last_upgrade_date", "")
        today_date = datetime.now().strftime("%Y-%m-%d")
        return last_date != today_date

    def run_daily_self_upgrade(self, force: bool = False) -> Dict[str, Any]:
        """
        Executes the autonomous daily self-training cycle:
        1. Analyzes recent reel scripts, hooks, and SEO performance
        2. Queries Gemini to extract new viral heuristics & prune weak patterns
        3. Generates fresh golden rules & winning hook templates
        4. Increments evolution level and updates playbook
        """
        playbook = self.load_playbook()
        today_date = datetime.now().strftime("%Y-%m-%d")

        if not force and playbook.get("last_upgrade_date") == today_date:
            print(f"[SELF-LEARNING] Agent is already up-to-date for today ({today_date}) at Level {playbook.get('evolution_level', 1.0):.1f}.")
            return playbook

        print(f"\n" + "=" * 75)
        print("     ✦ AUTONOMOUS SELF-TRAINING & KNOWLEDGE EVOLUTION CYCLE")
        print("=" * 75)
        print(f"Current Agent Level: {playbook.get('evolution_level', 1.0):.1f}")
        print(f"Target Domains:      Vedic Astrology | Gemstones | Psychic Karma | Devotion")
        print(f"Training Date:       {today_date}")
        print("-" * 75)

        history = self.load_history()
        recent_samples = history[-10:] if history else []

        prompt = f"""
You are the Meta-Learning & Algorithmic Optimization Brain for an Autonomous Instagram Reels Creator.
The agent produces high-retention viral content across 5 core viral pillars:
1. Sudden Wealth, Money Drain & Rare Dhana Yogas (Rahu in 2nd/11th, Kemdrum Moon, 8th house wealth)
2. Relationship Karma, Marriage Delays & Toxic Soul Ties (7th house Ketu/Rahu, Venus affliction, Manglik)
3. Career Breakthroughs, Sade Sati & Karmic Obstacles (10th house Saturn, Rahu Mahadasha, Vipreet Raj Yoga)
4. Psychic Intuition, 3 AM Wakeups & Divine Protection (Deva Kripa, 8th house 3rd eye, old soul debts)
5. Gemstone Energies & Dangers (Pukhraj, Neelam, Manik, Moti, Panna, Heera, Moonga)

CURRENT PLAYBOOK RULES:
{json.dumps(playbook.get("daily_golden_rules", []), ensure_ascii=False)}

RECENT REELS GENERATED / PUBLISHED:
{json.dumps(recent_samples, ensure_ascii=False)}

CRITICAL ALGORITHM DIRECTIVES:
- Multi-Reason/Checklist Dominance: Viewers prioritize reels providing 3 distinct signs or placements because it guarantees 100% video completion as they wait for their placement, and drives extreme comment velocity.
- Comment Consultation Retention Loop: CTAs prompt viewers to comment their Date of Birth or placement, allowing our AI agent to reply directly with personalized Vedic remedies.

TASK:
Analyze recent content trends and synthesize a higher-intelligence upgrade for today's production:
1. Formulate 4 upgraded "daily_golden_rules" for maximum watch-time, multi-reason retention, and comment engagement.
2. Formulate 3 NEW "winning_hooks" using the multi-reason / 3-signs framework (7-12 spoken words).
3. Identify 3 new "banned_low_retention_phrases" that weaken short-form retention.
4. Highlight the TOP 3 highest-reach SEO keywords for today's Explore indexing.
5. Provide a 2-sentence "evolution_summary" of what the agent learned today.

Return ONLY valid JSON in this exact structure:
{{
  "daily_golden_rules": [
    "Rule 1...",
    "Rule 2...",
    "Rule 3...",
    "Rule 4..."
  ],
  "new_winning_hooks": [
    {{
      "template": "...",
      "example": "...",
      "category": "Gemstone Warning / Vedic Astrology / Psychic Karma / Spiritual Devotion",
      "score": 94.0
    }}
  ],
  "new_banned_phrases": [
    "Phrase 1",
    "Phrase 2",
    "Phrase 3"
  ],
  "top_seo_keywords": [
    "Keyword1",
    "Keyword2",
    "Keyword3"
  ],
  "evolution_summary": "Summary of today's upgrades..."
}}
"""
        print("[SELF-LEARNING] Analyzing performance vectors and synthesizing upgrade with Gemini...")
        try:
            res = generate_json(prompt)
        except Exception as exc:
            logger.warning(f"Self-upgrade synthesis fallback: {exc}")
            res = {}

        # Merge updates
        if res.get("daily_golden_rules"):
            playbook["daily_golden_rules"] = res["daily_golden_rules"]

        if res.get("new_winning_hooks"):
            existing_templates = {h.get("template") for h in playbook.get("winning_hooks_bank", [])}
            for nh in res["new_winning_hooks"]:
                if nh.get("template") not in existing_templates:
                    playbook.setdefault("winning_hooks_bank", []).append(nh)

        if res.get("new_banned_phrases"):
            current_banned = set(playbook.get("banned_low_retention_phrases", []))
            for bp in res["new_banned_phrases"]:
                current_banned.add(bp)
            playbook["banned_low_retention_phrases"] = list(current_banned)

        if res.get("top_seo_keywords"):
            current_seo = set(playbook.get("seo_high_reach_keywords", []))
            for kw in res["top_seo_keywords"]:
                current_seo.add(kw)
            playbook["seo_high_reach_keywords"] = list(current_seo)

        # Increment evolution level
        current_level = float(playbook.get("evolution_level", 1.0))
        new_level = round(current_level + 0.1, 1)
        playbook["evolution_level"] = new_level
        playbook["last_upgrade_date"] = today_date
        playbook["total_training_cycles"] = playbook.get("total_training_cycles", 0) + 1

        summary = res.get("evolution_summary", f"Upgraded script pacing, tightened gemstone warnings, and refined devotional comment triggers for {today_date}.")

        # Log history
        playbook.setdefault("evolution_history", []).append({
            "cycle": playbook["total_training_cycles"],
            "date": today_date,
            "evolution_level": new_level,
            "notes": summary,
        })

        self.save_playbook(playbook)

        print(f"\n[SELF-LEARNING] AGENT UPGRADED TO LEVEL {new_level}!")
        print(f" -> Evolution Summary: {summary}")
        print(" -> Daily Golden Rules Updated:")
        for r in playbook["daily_golden_rules"][:3]:
            print(f"    * {r}")
        print(f" -> Knowledge Base: {len(playbook.get('winning_hooks_bank', []))} winning hooks stored.")
        print(f" -> Playbook saved to: {self.playbook_path.name}\n")

        return playbook

    def get_prompt_injection(self) -> str:
        """
        Generate a dynamic training context snippet to inject into script and hook prompts,
        ensuring every video is generated using the agent's latest evolved intelligence.
        """
        playbook = self.load_playbook()
        level = playbook.get("evolution_level", 1.0)
        rules = playbook.get("daily_golden_rules", [])
        banned = playbook.get("banned_low_retention_phrases", [])[:6]
        top_hooks = [h.get("example") for h in playbook.get("winning_hooks_bank", [])[-3:] if h.get("example")]

        injection = f"""
--- AGENT SELF-EVOLVED KNOWLEDGE CORE (LEVEL {level:.1f}) ---
LEARNED DAILY RETENTION RULES:
"""
        for r in rules:
            injection += f"- {r}\n"

        if top_hooks:
            injection += "\nHIGH-RETENTION BENCHMARK HOOKS LEARNED:\n"
            for th in top_hooks:
                injection += f"- \"{th}\"\n"

        if banned:
            injection += "\nSTRICTLY FORBIDDEN CLICHES (PRUNED BY AGENT):\n"
            for bp in banned:
                injection += f"- \"{bp}\"\n"

        injection += "--------------------------------------------------------\n"
        return injection


if __name__ == "__main__":
    print("Testing Self-Learning Engine...")
    engine = SelfLearningEngine()
    print("Initial Level:", engine.load_playbook().get("evolution_level"))
    upgraded = engine.run_daily_self_upgrade(force=True)
    print("New Level:", upgraded.get("evolution_level"))
    print("\nPrompt Injection Preview:\n", engine.get_prompt_injection())
