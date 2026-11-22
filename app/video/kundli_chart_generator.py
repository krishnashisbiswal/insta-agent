"""
Dynamic Vedic Kundli Chart Visual Generator.
Generates authentic, high-resolution 1080x1920 (9:16 vertical) North Indian
astrological Kundli birth charts with dynamic house highlighting and planet markers:

1. Dynamic House Highlighting: Illuminates any specified house (1 to 12) with
   radiant golden/amber light, Devanagari Sanskrit numerals, and signification banners.
2. Natural Language Script Extraction: Extracts house numbers and planetary placements
   from Hindi, English, and Hinglish narrations (including oblique cases like 'दूसरे', 'आठवें').
3. Script-Driven Visual Intelligence: Understands actual astrological intent without random inference:
   - Mode A (HOUSE_ONLY): Highlighting, illumination, light shafts; NO random planet inserted.
   - Mode B (PLANET_ONLY): Cinematic 3D celestial planet in cosmic space; NO invented house.
   - Mode C (PLANET_IN_HOUSE): Planet positioned inside house; house highlighted; floor contact shadow.
   - Mode D (CONJUNCTION): Multiple planets together in the target house; dual aura; NO extra planets.
   - Mode E (ASPECT / DRISHTI): Aspecting planet in source house; target house highlighted;
     controlled parabolic ray with directional arrowhead; non-mirrored typography.
4. Photorealistic 3D Celestial Spheres: Accurate spherical projection, realistic Lambertian
   terminator, ambient fill, specular highlight, and atmospheric Fresnel limb glow.
"""

from __future__ import annotations

import dataclasses
import hashlib
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

logger = logging.getLogger("KundliChartGenerator")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED_BROLL_DIR = PROJECT_ROOT / "assets" / "generated_broll"
GENERATED_BROLL_DIR.mkdir(parents=True, exist_ok=True)

# Complete 12-House Astrological Metadata
HOUSE_METADATA: Dict[int, Dict[str, str]] = {
    1: {
        "name_hi": "प्रथम भाव (लग्न)",
        "name_en": "1st House (Ascendant)",
        "sanskrit": "तनु भाव",
        "sanskrit_translit": "TANU BHAVA",
        "significance": "Self, Physical Body, Vitality & Life Direction",
        "type": "Kendra & Trikona (Most Auspicious)",
    },
    2: {
        "name_hi": "द्वितीय भाव (धन)",
        "name_en": "2nd House (Dhana)",
        "sanskrit": "धन भाव",
        "sanskrit_translit": "DHANA BHAVA",
        "significance": "Accumulated Wealth, Speech, Assets & Family Lineage",
        "type": "Maraka & Panapara",
    },
    3: {
        "name_hi": "तृतीय भाव (सहज)",
        "name_en": "3rd House (Sahaja)",
        "sanskrit": "पराक्रम भाव",
        "sanskrit_translit": "SAHAJA BHAVA",
        "significance": "Courage, Willpower, Self-Effort & Communication",
        "type": "Upachaya",
    },
    4: {
        "name_hi": "चतुर्थ भाव (सुख)",
        "name_en": "4th House (Sukha)",
        "sanskrit": "मातृ भाव",
        "sanskrit_translit": "SUKHA BHAVA",
        "significance": "Inner Peace, Mother, Real Estate, Vehicles & Mind",
        "type": "Kendra",
    },
    5: {
        "name_hi": "पंचम भाव (पुत्र)",
        "name_en": "5th House (Putra)",
        "sanskrit": "बुद्धि भाव",
        "sanskrit_translit": "PUTRA BHAVA",
        "significance": "Intellect, Past-Life Karma (Purva Punya), Speculation",
        "type": "Trikona (Auspicious Dharma)",
    },
    6: {
        "name_hi": "षष्ठ भाव (रिपु)",
        "name_en": "6th House (Ripu)",
        "sanskrit": "शत्रु/ऋण भाव",
        "sanskrit_translit": "RIPU BHAVA",
        "significance": "Debts, Enemies, Daily Struggles, Disease & Overcoming",
        "type": "Dusthana & Upachaya",
    },
    7: {
        "name_hi": "सप्तम भाव (जाया)",
        "name_en": "7th House (Kalatra)",
        "sanskrit": "कलत्र भाव",
        "sanskrit_translit": "KALATRA BHAVA",
        "significance": "Marriage, Long-Term Partnerships & Public Relations",
        "type": "Kendra & Maraka",
    },
    8: {
        "name_hi": "अष्टम भाव (आयु)",
        "name_en": "8th House (Ayu/Randhra)",
        "sanskrit": "रंध्र भाव",
        "sanskrit_translit": "RANDHRA BHAVA",
        "significance": "Sudden Shifts, Occult, Longevity, Hidden Wealth & Transformation",
        "type": "Major Dusthana (Transformation)",
    },
    9: {
        "name_hi": "नवम भाव (धर्म)",
        "name_en": "9th House (Bhagya)",
        "sanskrit": "भाग्य भाव",
        "sanskrit_translit": "BHAGYA BHAVA",
        "significance": "Higher Fortune, Dharma, Guru's Grace & Pilgrimage",
        "type": "Supreme Trikona (Luck)",
    },
    10: {
        "name_hi": "दशम भाव (कर्म)",
        "name_en": "10th House (Karma)",
        "sanskrit": "राज्य भाव",
        "sanskrit_translit": "KARMA BHAVA",
        "significance": "Career, Power, Authority, Public Status & Leadership",
        "type": "Supreme Kendra",
    },
    11: {
        "name_hi": "एकादश भाव (लाभ)",
        "name_en": "11th House (Labha)",
        "sanskrit": "आय भाव",
        "sanskrit_translit": "LABHA BHAVA",
        "significance": "Massive Gains, Network Circles & Fulfillment of Desires",
        "type": "Upachaya (Growth)",
    },
    12: {
        "name_hi": "द्वादश भाव (व्यय)",
        "name_en": "12th House (Vyaya)",
        "sanskrit": "मोक्ष भाव",
        "sanskrit_translit": "VYAYA BHAVA",
        "significance": "Subconscious Mind, Foreign Travel, Isolation & Spiritual Liberation",
        "type": "Dusthana & Moksha",
    },
}

DEVANAGARI_NUMERALS: Dict[int, str] = {
    1: "१", 2: "२", 3: "३", 4: "४", 5: "५", 6: "६",
    7: "७", 8: "८", 9: "९", 10: "१०", 11: "११", 12: "१२"
}

ROMAN_NUMS: Dict[int, str] = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI",
    7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"
}

PLANET_PATTERNS: Dict[str, Tuple[str, str]] = {
    "sun": ("सूर्य", "SUN"),
    "surya": ("सूर्य", "SUN"),
    "moon": ("चंद्र", "MOON"),
    "chandra": ("चंद्र", "MOON"),
    "mars": ("मंगल", "MARS"),
    "mangal": ("मंगल", "MARS"),
    "mercury": ("बुध", "MERCURY"),
    "budh": ("बुध", "MERCURY"),
    "budha": ("बुध", "MERCURY"),
    "jupiter": ("गुरु", "JUPITER"),
    "guru": ("गुरु", "JUPITER"),
    "brihaspati": ("बृहस्पति", "JUPITER"),
    "venus": ("शुक्र", "VENUS"),
    "shukra": ("शुक्र", "VENUS"),
    "saturn": ("शनि", "SATURN"),
    "shani": ("शनि", "SATURN"),
    "rahu": ("राहु", "RAHU"),
    "ketu": ("केतु", "KETU"),
}

PLANET_CANONICAL_MAP: Dict[str, str] = {
    "sun": "sun", "surya": "sun", "रवि": "sun", "ravi": "sun", "solar": "sun", "आदित्य": "sun", "aditya": "sun", "सूर्य": "sun",
    "moon": "moon", "chandra": "moon", "चंद्र": "moon", "चन्द्र": "moon", "सोम": "moon", "som": "moon",
    "mars": "mars", "mangal": "mars", "मंगल": "mars", "कुज": "mars", "kuja": "mars", "भौम": "mars", "bhauma": "mars", "angarak": "mars",
    "mercury": "mercury", "budh": "mercury", "budha": "mercury", "बुध": "mercury", "सौम्य": "mercury",
    "jupiter": "jupiter", "guru": "jupiter", "गुरु": "jupiter", "बृहस्पति": "jupiter", "brihaspati": "jupiter", "देवगुरु": "jupiter",
    "venus": "venus", "shukra": "venus", "शुक्र": "venus", "दैत्यगुरु": "venus", "भार्गव": "venus",
    "saturn": "saturn", "shani": "saturn", "शनि": "saturn", "शनिश्चर": "saturn", "manda": "saturn",
    "rahu": "rahu", "राहु": "rahu", "छाया ग्रह": "rahu", "north node": "rahu", "dragon head": "rahu",
    "ketu": "ketu", "केतु": "ketu", "south node": "ketu", "dragon tail": "ketu",
}

PLANET_DISPLAY_NAMES: Dict[str, Tuple[str, str]] = {
    "sun": ("SURYA", "SUN"),
    "moon": ("CHANDRA", "MOON"),
    "mars": ("MANGAL", "MARS"),
    "mercury": ("BUDHA", "MERCURY"),
    "jupiter": ("GURU", "JUPITER"),
    "venus": ("SHUKRA", "VENUS"),
    "saturn": ("SHANI", "SATURN"),
    "rahu": ("RAHU", "NORTH NODE"),
    "ketu": ("KETU", "SOUTH NODE"),
}

# Special Vedic Drishti (Aspects) by planet
VEDIC_ASPECTS: Dict[str, List[int]] = {
    "saturn": [3, 7, 10],
    "mars": [4, 7, 8],
    "jupiter": [5, 7, 9],
    "rahu": [5, 7, 9],
    "ketu": [5, 7, 9],
    "sun": [7],
    "moon": [7],
    "mercury": [7],
    "venus": [7],
}
VEDIC_SPECIAL_ASPECTS = VEDIC_ASPECTS

HOUSE_ALIASES: Dict[int, List[str]] = {
    1: ["1st", "first", "प्रथम", "पहला", "पहले", "लग्न", "तनु"],
    2: ["2nd", "second", "द्वितीय", "दूसरा", "दूसरे", "धन"],
    3: ["3rd", "third", "तृतीय", "तीसरा", "तीसरे", "सहज", "पराक्रम"],
    4: ["4th", "fourth", "चतुर्थ", "चौथा", "चौथे", "सुख", "मातृ"],
    5: ["5th", "fifth", "पंचम", "पांचवा", "पांचवे", "पांचवें", "पुत्र", "बुद्धि"],
    6: ["6th", "sixth", "षष्ठ", "छठा", "छठे", "शत्रु", "ऋण", "रोग"],
    7: ["7th", "seventh", "सप्तम", "सातवां", "सातवा", "सातवे", "सातवें", "कलत्र", "जाया"],
    8: ["8th", "eighth", "अष्टम", "आठवां", "आठवा", "आठवे", "आठवें", "रंध्र", "आयु"],
    9: ["9th", "ninth", "नवम", "नौवां", "नौवा", "नौवे", "नौवें", "भाग्य", "धर्म"],
    10: ["10th", "tenth", "दशम", "दसवां", "दसवा", "दसवे", "दसवें", "कर्म", "राज्य"],
    11: ["11th", "eleventh", "एकादश", "ग्यारहवां", "ग्यारहवा", "ग्यारहवे", "ग्यारहवें", "लाभ", "आय"],
    12: ["12th", "twelfth", "द्वादश", "बारहवां", "बारहवा", "बारहवे", "बारहवें", "व्यय", "मोक्ष"],
}


@dataclasses.dataclass
class AstrologyScenePlan:
    intent: str  # HOUSE_ONLY, PLANET_ONLY, PLANET_IN_HOUSE, CONJUNCTION, ASPECT, MULTI_PLANET, GENERAL
    primary_house: Optional[int] = None
    target_house: Optional[int] = None
    planets: List[str] = dataclasses.field(default_factory=list)
    aspect_type: Optional[str] = None
    aspect_count: Optional[int] = None
    badge_title: str = ""
    subtitle: str = ""
    source_explicit: bool = False
    target_explicit: bool = False
    aspect_verified: bool = False
    relationship: str = "none"  # "conjunction", "aspect", "placement", "contrast", "separate", "none"


class KundliChartGenerator:
    """
    Renders 1080x1920 dynamic Vedic astrology charts and 3D scenes tailored to script context.
    """

    @staticmethod
    def _get_ordinal(n: int) -> str:
        if 11 <= (n % 100) <= 13:
            return f"{n}TH"
        suffixes = {1: f"{n}ST", 2: f"{n}ND", 3: f"{n}RD"}
        return suffixes.get(n % 10, f"{n}TH")

    @classmethod
    def extract_house_and_planet(cls, text: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Backwards-compatible extraction of house number (1-12) and planetary entity string.
        """
        plan = cls.parse_astrology_scene(text)
        detected_house = plan.primary_house or plan.target_house
        detected_planet = None
        if plan.planets:
            p_key = plan.planets[0]
            for pk, (p_hi, p_en) in PLANET_PATTERNS.items():
                if pk == p_key:
                    detected_planet = f"{p_hi} ({p_en})"
                    break
            if not detected_planet:
                hi_name, en_name = PLANET_DISPLAY_NAMES.get(p_key, (p_key.upper(), p_key.upper()))
                detected_planet = f"{hi_name} ({en_name})"
        return detected_house, detected_planet

    @classmethod
    def parse_astrology_scene(
        cls,
        text: str,
        fallback_topic: str = "",
        chart_data: Optional[Dict[str, Any]] = None,
    ) -> AstrologyScenePlan:
        """
        Intelligently parses script narration to extract exact astrological entities without random inference.
        Differentiates between:
        - Mode A: HOUSE_ONLY
        - Mode B: PLANET_ONLY
        - Mode C: PLANET_IN_HOUSE
        - Mode D: CONJUNCTION
        - Mode E: ASPECT (DRISHTI)
        - Mode F: GENERAL
        - Mode MULTI_PLANET: Non-conjunction multiple planet comparison
        """
        if not text:
            text = fallback_topic or ""
        t = text.lower()

        # Normalize chart_data verified placements if provided
        placements: Dict[str, int] = {}
        if chart_data:
            if "placements" in chart_data and isinstance(chart_data["placements"], dict):
                placements = {str(k).lower(): int(v) for k, v in chart_data["placements"].items()}
            elif "houses" in chart_data and isinstance(chart_data["houses"], dict):
                for h_num, plist in chart_data["houses"].items():
                    for p in plist:
                        placements[str(p).lower()] = int(h_num)
            else:
                for k, v in chart_data.items():
                    if isinstance(k, str) and isinstance(v, (int, str)) and str(v).isdigit():
                        placements[k.lower()] = int(v)

        # 1. Detect all planets mentioned
        found_planets: List[str] = []
        for p_word, canonical in PLANET_CANONICAL_MAP.items():
            has_unicode = any(ord(c) > 127 for c in p_word)
            if (has_unicode and p_word in t) or re.search(r"\b" + re.escape(p_word) + r"\b", t):
                if canonical not in found_planets:
                    found_planets.append(canonical)

        # 2. Extract syntactic roles for houses (Target vs Source vs General)
        tgt_h: Optional[int] = None
        target_explicit = False
        target_patterns = [
            r"(?:aspects|casts aspect onto|casts its \w+ aspect onto|drishti on|पर दृष्टि|को देखता)\s+(?:the\s+)?([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\b",
            r"\b([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\s*(?:receives an aspect|receives drishti|पर दृष्टि|को देखता)\b",
            r"(?:onto|into|to)\s+(?:the\s+)?([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\b",
        ]
        for pat in target_patterns:
            m_tgt = re.search(pat, t)
            if m_tgt:
                tgt_h = int(m_tgt.group(1))
                target_explicit = True
                break

        src_h: Optional[int] = None
        source_explicit = False
        source_patterns = [
            r"\b(?:from)\b\s+(?:the\s+)?([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\b",
            r"(?:in|occupying|sitting in|में)\s+(?:the\s+)?([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\s*(?:casts|aspects|drishti)\b",
            r"\b([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\s*(?:se|से)\s*(?:aspect|drishti|दृष्टि)\b",
        ]
        for pat in source_patterns:
            m_src = re.search(pat, t)
            if m_src:
                src_h = int(m_src.group(1))
                source_explicit = True
                break

        # Detect all house numbers mentioned in text
        found_houses: List[int] = []
        for m in re.finditer(r"\b([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\b", t):
            start, end = max(0, m.start() - 10), min(len(t), m.end() + 10)
            sub = t[start:end]
            if any(k in sub for k in ["house", "bhav", "bhava", "ghar", "भाव", "घर", "drishti", "दृष्टि", "aspect", "st", "nd", "rd", "th", "वें", "वां", "वीं"]):
                post = t[m.end():m.end() + 15]
                # If followed immediately by aspect/drishti count (e.g. 7th aspect, 3rd drishti), skip
                if any(k in post for k in ["aspect", "drishti", "दृष्टि"]):
                    continue
                h_val = int(m.group(1))
                if h_val not in found_houses:
                    found_houses.append(h_val)

        for h_num, aliases in HOUSE_ALIASES.items():
            if h_num not in found_houses:
                for alias in aliases:
                    has_unicode = any(ord(c) > 127 for c in alias)
                    if (has_unicode and alias in t) or re.search(r"\b" + re.escape(alias) + r"\s*(?:house|bhav|bhava|ghar|भाव|घर)?\b", t):
                        found_houses.append(h_num)
                        break
                    elif alias in ["लग्न", "तनु भाव", "रंध्र भाव", "व्यय भाव", "मोक्ष भाव", "भाग्य भाव", "कर्म भाव", "सुख भाव", "मातृ भाव", "धन भाव", "सहज भाव", "पुत्र भाव", "बुद्धि भाव", "शत्रु भाव", "ऋण भाव", "कलत्र भाव", "जाया भाव", "आयु भाव", "लाभ भाव", "आय भाव"] and alias in t:
                        found_houses.append(h_num)
                        break

        # 3. Detect Aspect / Drishti
        aspect_match = re.search(r"\b(3rd|4th|5th|7th|8th|9th|10th|तीसरी|चौथी|पाँचवीं|पांचवीं|सातवीं|आठवीं|नौवीं|दसवीं)\s*(?:aspect|drishti|दृष्टि)\b", t)
        aspect_count: Optional[int] = None
        if aspect_match:
            asp_str = aspect_match.group(1)
            asp_map = {
                "3rd": 3, "तीसरी": 3,
                "4th": 4, "चौथी": 4,
                "5th": 5, "पाँचवीं": 5, "पांचवीं": 5,
                "7th": 7, "सातवीं": 7,
                "8th": 8, "आठवीं": 8,
                "9th": 9, "नौवीं": 9,
                "10th": 10, "दसवीं": 10,
            }
            aspect_count = asp_map.get(asp_str)

        has_aspect_negation = any(re.search(p, t) for p in [
            r"(?:\b(?:no|not|without|lacks|nahi|nahin|nhi)\b|नहीं|ना|बिना).*?(?:\b(?:aspect|aspects|drishti)\b|दृष्टि)",
            r"(?:\b(?:aspect|aspects|drishti)\b|दृष्टि).*?(?:\b(?:not|nahi|nahin|nhi)\b|नहीं|ना)",
            r"\b(?:no aspect|not aspect)\b|दृष्टि\s*नहीं|दृष्टि\s*का\s*अभाव",
        ])

        is_aspect = (
            not has_aspect_negation
            and (
                bool(aspect_count)
                or bool(re.search(r"\b(?:aspects|casts aspect onto|casts its \w+ aspect onto|drishti on|पर दृष्टि|को देखता|receives an aspect|receives drishti)\b", t))
                or (any(k in t for k in ["drishti", "दृष्टि"]) and (found_houses or found_planets))
            )
        )

        # 4. Resolve exact relationship
        if is_aspect and (found_planets or found_houses or tgt_h is not None):
            # Aspecting planet - NEVER INVENT SATURN OR ANY DEFAULT PLANET!
            aspecting_planet: Optional[str] = found_planets[0] if found_planets else None
            aspect_verified = False

            # If target house not explicitly caught yet, check if a single house was found in target context
            if tgt_h is None:
                if any(k in t for k in ["aspects the", "aspects house", "casts aspect onto", "पर दृष्टि", "को देखता", "falls on", "falling on"]):
                    if found_houses:
                        tgt_h = found_houses[-1]
                        target_explicit = True
                elif len(found_houses) == 1:
                    # Single house mentioned in aspect scene without source indicators is the target
                    if not any(k in t for k in ["from the", "sitting in", "occupying", "से दृष्टि", "se drishti"]):
                        tgt_h = found_houses[0]
                        target_explicit = True

            # If source house is unknown from text, check verified chart_data!
            if src_h is None and aspecting_planet and aspecting_planet in placements:
                src_h = placements[aspecting_planet]
                aspect_verified = True

            # Aspect count: ONLY use if explicitly narrated or mathematically verified from chart data
            asp_num = aspect_count
            if asp_num is None and src_h is not None and tgt_h is not None and aspect_verified:
                calc_count = ((tgt_h - src_h) % 12) + 1
                valid_counts = VEDIC_SPECIAL_ASPECTS.get(aspecting_planet, [7])
                if calc_count in valid_counts:
                    asp_num = calc_count

            planets_list = [aspecting_planet] if aspecting_planet else []
            p_disp = PLANET_DISPLAY_NAMES.get(aspecting_planet, (aspecting_planet.upper(), aspecting_planet.upper()))[0] if aspecting_planet else None

            if src_h is not None and tgt_h is not None:
                src_ord = cls._get_ordinal(src_h)
                tgt_ord = cls._get_ordinal(tgt_h)
                asp_ord = f"{cls._get_ordinal(asp_num)} " if asp_num else ""
                p_label = f"{p_disp} " if p_disp else ""
                badge = f"{src_ord} TO {tgt_ord} HOUSE • {p_label}{asp_ord}DRISHTI"
                sub = f"Planetary Rays from Bhava {src_h} illuminating Bhava {tgt_h}"
                asp_type = f"{asp_ord}DRISHTI".strip()
            elif tgt_h is not None:
                tgt_ord = cls._get_ordinal(tgt_h)
                if p_disp:
                    badge = f"{tgt_ord} HOUSE • {p_disp} DRISHTI"
                    sub = f"{p_disp} casting celestial rays onto Bhava {tgt_h}"
                    asp_type = f"{p_disp} DRISHTI"
                else:
                    badge = f"{tgt_ord} HOUSE • ASPECT RECEIVED"
                    sub = f"Divine celestial rays illuminating Bhava {tgt_h}"
                    asp_type = "ASPECT RECEIVED"
            elif src_h is not None and p_disp:
                src_ord = cls._get_ordinal(src_h)
                badge = f"{src_ord} HOUSE • {p_disp} ASPECTING"
                sub = f"{p_disp} activating rays from Bhava {src_h}"
                asp_type = f"{p_disp} ASPECT"
            else:
                p_label = f"{p_disp} " if p_disp else "VEDIC "
                badge = f"{p_label}PLANETARY ASPECT • COSMIC DRISHTI"
                sub = "Celestial influence across the cosmos"
                asp_type = f"{p_label}ASPECT".strip()

            return AstrologyScenePlan(
                intent="ASPECT",
                primary_house=src_h,
                target_house=tgt_h,
                planets=planets_list,
                aspect_type=asp_type,
                aspect_count=asp_num,
                badge_title=badge,
                subtitle=sub,
                source_explicit=source_explicit,
                target_explicit=target_explicit,
                aspect_verified=aspect_verified,
                relationship="aspect",
            )

        # -------------------------------------------------------------
        # Conjunction vs Contrast / Separate / Negation
        # -------------------------------------------------------------
        has_conj_negation = any(re.search(p, t) for p in [
            r"(?:\b(?:no|not|neither|nor|never|without|lacks|nahi|nahin|nhi)\b|नहीं|ना|बिना|बगैर).*?(?:\b(?:conjunction|conjunct|conjoined)\b|युति)",
            r"(?:\b(?:conjunction|conjunct|conjoined)\b|युति).*?(?:\b(?:is not|are not|does not|do not|never|absent|denied|nahi|nahin|nhi)\b|नहीं|ना)",
            r"(?:\b(?:there is no|no such)\s+conjunction|कोई\s*(?:भी\s*)?युति\s*नहीं)",
            r"\b(?:no conjunction|not conjunct)\b|युति\s*नहीं|युति\s*का\s*अभाव",
        ])

        conj_keywords = [
            "conjunct", "conjoined", "conjunction", "in conjunction", "conjuncts",
            "युति", "युत", "बुधादित्य", "budhaditya"
        ]
        has_conj_kw = any(k in t for k in conj_keywords)
        has_together_placement = bool(re.search(
            r"\b(?:sitting together|placed together|positioned together|located together|एक साथ स्थित|एक साथ बैठे)\b", t
        ))

        contrast_keywords = [
            "while", "whereas", "different", "अलग", "जबकि",
            "on the other hand", "represents disruption while", "disruption",
            "clashes with", "clash", "vs", "versus", "contrast"
        ]
        has_contrast_kw = any(k in t for k in contrast_keywords)

        # Check if text mentions distinct houses for different planets e.g. "Sun in 8th house and Rahu in 12th house"
        has_separate_houses = False
        if len(found_houses) >= 2 and len(found_planets) >= 2:
            # Check if each planet has its own house pattern
            distinct_placements = 0
            for p_cand in found_planets:
                for h_cand in found_houses:
                    if re.search(rf"\b{re.escape(p_cand)}\b.*?\b{h_cand}(?:st|nd|rd|th|वें|वां|वीं)?\b|\b{h_cand}(?:st|nd|rd|th|वें|वां|वीं)?\b.*?\b{re.escape(p_cand)}\b", t):
                        distinct_placements += 1
                        break
            if distinct_placements >= 2:
                has_separate_houses = True

        # Shared house check e.g. "Sun and Rahu in the 8th house"
        shared_house_match = re.search(
            r"\b(?:and|aur|तथा|,)\b.*?\b(?:in|occupying|sitting in|में)\s+(?:the\s+)?([1-9]|1[0-2])(?:st|nd|rd|th|वें|वां|वीं)?\s*(?:house|bhav|bhava|ghar|भाव|घर)?\b", t
        )
        is_shared_house_conjunction = (
            bool(shared_house_match)
            and len(found_planets) >= 2
            and len(found_houses) == 1
            and not has_contrast_kw
            and not has_separate_houses
            and not has_conj_negation
        )

        is_explicit_conjunction = (
            not has_conj_negation
            and not has_contrast_kw
            and not has_separate_houses
            and ((has_conj_kw and len(found_planets) >= 1) or has_together_placement or is_shared_house_conjunction)
        )

        if is_explicit_conjunction:
            intent = "CONJUNCTION"
            h = found_houses[0] if (found_houses and not has_separate_houses) else None
            # Check verified placements if house not in text
            if h is None and chart_data:
                for p in found_planets:
                    if p in placements:
                        h = placements[p]
                        break

            names = [PLANET_DISPLAY_NAMES.get(p, (p.upper(), p.upper()))[0] for p in found_planets]
            p_str = " & ".join(names) if names else "GRAHA YUTI"
            if h is not None:
                h_ord = cls._get_ordinal(h)
                badge = f"{h_ord} HOUSE • {p_str} CONJUNCTION"
                sub = f"Conjoined celestial energy activating Bhava {h}"
            else:
                badge = f"{p_str} • CELESTIAL CONJUNCTION"
                sub = "Powerful conjoined planetary alignment in cosmic space"

            return AstrologyScenePlan(
                intent=intent,
                primary_house=h,
                planets=found_planets,
                badge_title=badge,
                subtitle=sub,
                relationship="conjunction",
            )

        elif len(found_planets) >= 2:
            intent = "MULTI_PLANET"
            names = [PLANET_DISPLAY_NAMES.get(p, (p.upper(), p.upper()))[0] for p in found_planets]
            p_str = " & ".join(names)
            h = found_houses[0] if (found_houses and not has_separate_houses and not has_contrast_kw) else None
            rel = "no_conjunction" if has_conj_negation else ("contrast" if has_contrast_kw else "separate")
            badge = f"{p_str} • DUAL CELESTIAL ENERGIES" if len(names) == 2 else f"{p_str} • MULTI-PLANETARY ENERGIES"
            sub = "Distinct astrological archetypes and cosmic influences"
            return AstrologyScenePlan(
                intent=intent,
                primary_house=h,
                planets=found_planets,
                badge_title=badge,
                subtitle=sub,
                relationship=rel,
            )

        elif len(found_planets) == 1 and found_houses:
            h = found_houses[0]
            p = found_planets[0]

            # Verify explicit placement grammar or chart data
            is_placed = False
            if chart_data and placements.get(p) == h:
                is_placed = True
            else:
                h_terms = [rf"\b{h}(?:st|nd|rd|th|वें|वां|वीं)?\b"] + [re.escape(a) for a in HOUSE_ALIASES.get(h, [])]
                h_pat = "(?:" + "|".join(h_terms) + ")"

                all_p_names = [p] + [k for k, v in PLANET_CANONICAL_MAP.items() if v == p]
                placement_patterns = []
                for p_name in all_p_names:
                    p_esc = re.escape(p_name)
                    placement_patterns.extend([
                        rf"(?:\b{p_esc}\b|{p_esc}).*?(?:\b(?:is\s+)?(?:in|inside|occupying|occupies|sitting in|sits in|positioned in|placed in|located in|residing in|transits|transiting|transit in|transit into|enters|moving into|moves into)\b|में|mein|me)\s+(?:the\s+|your\s+|its\s+)?{h_pat}",
                        rf"{h_pat}\s*(?:house|bhav|bhava|ghar|भाव|घर)?\s*(?:का|ke|ki|के|की|में|me|mein)\s*.*?(?:\b{p_esc}\b|{p_esc})",
                        rf"(?:\b{p_esc}\b|{p_esc}).*?{h_pat}\s*(?:house|bhav|bhava|ghar|भाव|घर)?\s*(?:में|me|mein)",
                        rf"{h_pat}\s*(?:house|bhav|bhava|ghar|भाव|घर)?\s+(?:\b{p_esc}\b|{p_esc})",
                    ])
                if any(re.search(pat, t) for pat in placement_patterns):
                    is_placed = True

            p_hi, p_en = PLANET_DISPLAY_NAMES.get(p, (p.upper(), p.upper()))
            if is_placed:
                intent = "PLANET_IN_HOUSE"
                meta = HOUSE_METADATA.get(h, {})
                sanskrit_name = meta.get("sanskrit_translit", f"BHAVA {h}")
                h_ord = cls._get_ordinal(h)
                badge = f"{h_ord} HOUSE • {p_hi} ({p_en}) IN {sanskrit_name.upper()}"
                return AstrologyScenePlan(
                    intent=intent,
                    primary_house=h,
                    planets=[p],
                    badge_title=badge,
                    subtitle=meta.get("significance", ""),
                    relationship="placement",
                )
            else:
                # Planet and house mentioned separately without established placement -> do NOT invent placement!
                badge = f"{p_hi} ({p_en}) • CELESTIAL ARCHETYPE"
                return AstrologyScenePlan(
                    intent="PLANET_ONLY",
                    primary_house=None,
                    planets=[p],
                    badge_title=badge,
                    subtitle=f"Cosmological force of {p_en} in celestial space",
                    relationship="separate",
                )
            h = found_houses[0]
            p = found_planets[0]
            p_hi, p_en = PLANET_DISPLAY_NAMES.get(p, (p.upper(), p.upper()))
            meta = HOUSE_METADATA.get(h, {})
            sanskrit_name = meta.get("sanskrit_translit", f"BHAVA {h}")
            h_ord = cls._get_ordinal(h)
            badge = f"{h_ord} HOUSE • {p_hi} ({p_en}) IN {sanskrit_name.upper()}"
            return AstrologyScenePlan(
                intent=intent,
                primary_house=h,
                planets=[p],
                badge_title=badge,
                subtitle=meta.get("significance", ""),
                relationship="placement",
            )

        elif len(found_planets) == 1 and not found_houses:
            intent = "PLANET_ONLY"
            p = found_planets[0]
            p_hi, p_en = PLANET_DISPLAY_NAMES.get(p, (p.upper(), p.upper()))
            badge = f"{p_hi} ({p_en}) • CELESTIAL ARCHETYPE"
            return AstrologyScenePlan(
                intent=intent,
                primary_house=None,
                planets=[p],
                badge_title=badge,
                subtitle=f"Divine cosmological force & energetic significance of {p_en}",
                relationship="archetype",
            )

        elif found_houses and not found_planets:
            intent = "HOUSE_ONLY"
            h = found_houses[0]
            meta = HOUSE_METADATA.get(h, {})
            sanskrit_name = meta.get("sanskrit_translit", f"BHAVA {h}")
            h_ord = cls._get_ordinal(h)
            badge = f"{h_ord} HOUSE • {sanskrit_name.upper()} ACTIVATION"
            return AstrologyScenePlan(
                intent=intent,
                primary_house=h,
                planets=[],
                badge_title=badge,
                subtitle=meta.get("significance", ""),
                relationship="house_activation",
            )

        else:
            intent = "GENERAL"
            return AstrologyScenePlan(
                intent=intent,
                primary_house=None,
                planets=[],
                badge_title="VEDIC KUNDLI BIRTH CHART • SACRED GEOMETRY",
                subtitle="North Indian Diamond Cosmic Alignment",
                relationship="none",
            )

    @classmethod
    def get_house_polygons(cls, x0: float, y0: float, x1: float, y1: float) -> Dict[int, List[Tuple[float, float]]]:
        """Calculates exact polygon coordinates for the 12 houses of a North Indian Kundli."""
        x_mid = (x0 + x1) / 2.0
        y_mid = (y0 + y1) / 2.0

        p_tl = ((x0 + x_mid) / 2.0, (y0 + y_mid) / 2.0)
        p_tr = ((x1 + x_mid) / 2.0, (y0 + y_mid) / 2.0)
        p_bl = ((x0 + x_mid) / 2.0, (y1 + y_mid) / 2.0)
        p_br = ((x1 + x_mid) / 2.0, (y1 + y_mid) / 2.0)

        return {
            1: [(x_mid, y0), p_tr, (x_mid, y_mid), p_tl],
            2: [(x0, y0), (x_mid, y0), p_tl],
            3: [(x0, y0), (x0, y_mid), p_tl],
            4: [p_tl, (x0, y_mid), p_bl, (x_mid, y_mid)],
            5: [(x0, y_mid), (x0, y1), p_bl],
            6: [(x0, y1), (x_mid, y1), p_bl],
            7: [(x_mid, y_mid), p_bl, (x_mid, y1), p_br],
            8: [(x_mid, y1), (x1, y1), p_br],
            9: [(x1, y1), (x1, y_mid), p_br],
            10: [(x_mid, y_mid), p_br, (x1, y_mid), p_tr],
            11: [(x1, y_mid), (x1, y0), p_tr],
            12: [(x_mid, y0), (x1, y0), p_tr],
        }

    @classmethod
    def get_centroid(cls, poly: List[Tuple[float, float]]) -> Tuple[float, float]:
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        return (cx, cy)

    @classmethod
    def generate_dynamic_chart(
        cls,
        highlight_house: Optional[int] = None,
        planet_name: Optional[str] = None,
        title: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Renders an authentic, 1080x1920 vertical cinematic chart with the target house highlighted.
        """
        width, height = 1080, 1920

        # Load system fonts
        from config.settings import DEFAULT_FONT_PATH, FALLBACK_FONT_PATH
        try:
            font_large = ImageFont.truetype(DEFAULT_FONT_PATH, 44)
            font_small = ImageFont.truetype(FALLBACK_FONT_PATH, 24)
            font_title = ImageFont.truetype(DEFAULT_FONT_PATH, 46)
            font_badge = ImageFont.truetype(DEFAULT_FONT_PATH, 30)
            font_sub = ImageFont.truetype(FALLBACK_FONT_PATH, 22)
        except Exception:
            try:
                font_large = ImageFont.truetype("arial.ttf", 44)
                font_small = ImageFont.truetype("arial.ttf", 24)
                font_title = ImageFont.truetype("arial.ttf", 46)
                font_badge = ImageFont.truetype("arial.ttf", 30)
                font_sub = ImageFont.truetype("arial.ttf", 22)
            except Exception:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_title = ImageFont.load_default()
                font_badge = ImageFont.load_default()
                font_sub = ImageFont.load_default()

        # 1. Base dark cosmic canvas
        canvas = Image.new("RGBA", (width, height), (8, 6, 16, 255))

        center_y = int(height * 0.48)

        # 2. Cosmic Ambient Light & Aura
        ambient_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ambient_draw = ImageDraw.Draw(ambient_layer)
        ambient_draw.ellipse(
            [width // 2 - 450, center_y - 450, width // 2 + 450, center_y + 450],
            fill=(28, 16, 44, 200)
        )
        if highlight_house:
            ambient_draw.ellipse(
                [width // 2 - 280, center_y - 280, width // 2 + 280, center_y + 280],
                fill=(190, 120, 10, 70)
            )
        ambient_layer = ambient_layer.filter(ImageFilter.GaussianBlur(80))
        canvas = Image.alpha_composite(canvas, ambient_layer)
        draw = ImageDraw.Draw(canvas)

        # 3. Geometry Setup
        box_size = 900
        x0 = (width - box_size) // 2
        x1 = x0 + box_size
        y0 = center_y - (box_size // 2)
        y1 = y0 + box_size
        x_mid = (x0 + x1) // 2
        y_mid = (y0 + y1) // 2

        polygons = cls.get_house_polygons(x0, y0, x1, y1)

        # 4. Highlight Selected House Polygon
        if highlight_house and highlight_house in polygons:
            poly = polygons[highlight_house]
            hl_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            hl_draw = ImageDraw.Draw(hl_layer)

            # Radiant Amber / Sacred Gold Fill
            hl_draw.polygon(poly, fill=(255, 175, 10, 115))
            hl_draw.line(poly + [poly[0]], fill=(255, 235, 110, 255), width=8)

            # Glowing Aura
            aura = hl_layer.filter(ImageFilter.GaussianBlur(24))
            canvas = Image.alpha_composite(canvas, aura)
            canvas = Image.alpha_composite(canvas, hl_layer)
            draw = ImageDraw.Draw(canvas)

        # 5. Golden Kundli Framework Lines
        gold_border = (212, 175, 55, 235)
        grid_gold = (185, 145, 45, 200)

        # Outer double frame
        draw.rectangle([x0, y0, x1, y1], outline=gold_border, width=5)
        draw.rectangle([x0 - 8, y0 - 8, x1 + 8, y1 + 8], outline=(150, 115, 35, 110), width=2)

        # Diagonals
        draw.line([(x0, y0), (x1, y1)], fill=grid_gold, width=3)
        draw.line([(x1, y0), (x0, y1)], fill=grid_gold, width=3)

        # Inner Diamond
        draw.line([(x_mid, y0), (x1, y_mid)], fill=grid_gold, width=3)
        draw.line([(x1, y_mid), (x_mid, y1)], fill=grid_gold, width=3)
        draw.line([(x_mid, y1), (x0, y_mid)], fill=grid_gold, width=3)
        draw.line([(x0, y_mid), (x_mid, y0)], fill=grid_gold, width=3)

        # 6. House Numbers and Callouts
        for h_num, poly in polygons.items():
            cx, cy = cls.get_centroid(poly)
            is_hl = (h_num == highlight_house)

            num_str = DEVANAGARI_NUMERALS.get(h_num, str(h_num))
            num_color = (255, 245, 180, 255) if is_hl else (175, 155, 125, 150)

            draw.text((cx - 12, cy - 20), num_str, fill=num_color, font=font_large)

            if is_hl:
                draw.ellipse([cx - 42, cy - 42, cx + 42, cy + 42], outline=(255, 235, 120, 240), width=3)
                meta = HOUSE_METADATA.get(h_num, {})
                tag_name = meta.get("sanskrit") or f"HOUSE {h_num}"
                draw.text((cx - 40, cy + 30), tag_name, fill=(255, 255, 200, 240), font=font_small)

                if planet_name:
                    draw.text((cx - 30, cy - 56), f"[{planet_name}]", fill=(255, 220, 0, 255), font=font_badge)

        # 7. Top Header
        top_y = y0 - 150
        header_text = title or (
            f"KUNDLI: {HOUSE_METADATA[highlight_house]['name_en'].upper()}"
            if highlight_house and highlight_house in HOUSE_METADATA
            else "VEDIC KUNDLI BIRTH CHART"
        )
        draw.rounded_rectangle(
            [x0 + 40, top_y, x1 - 40, top_y + 100],
            radius=18,
            fill=(14, 10, 24, 230),
            outline=(212, 175, 55, 210),
            width=2,
        )
        bbox = draw.textbbox((0, 0), header_text, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text((x0 + 40 + ((x1 - x0 - 80 - tw) // 2), top_y + 24), header_text, fill=(255, 235, 150, 255), font=font_title)

        # 8. Bottom Information Card
        if highlight_house and highlight_house in HOUSE_METADATA:
            meta = HOUSE_METADATA[highlight_house]
            bot_y = y1 + 45
            draw.rounded_rectangle(
                [x0 + 30, bot_y, x1 - 30, bot_y + 145],
                radius=20,
                fill=(24, 15, 6, 240),
                outline=(255, 185, 30, 240),
                width=3,
            )
            card_title = f"{meta['name_hi']} • {meta['name_en']}".upper()
            sig_text = f"Signification: {meta['significance']}"
            type_text = f"Classification: {meta['type']}"

            draw.text((x0 + 60, bot_y + 18), card_title, fill=(255, 225, 60, 255), font=font_badge)
            draw.text((x0 + 60, bot_y + 65), sig_text, fill=(235, 225, 210, 240), font=font_sub)
            draw.text((x0 + 60, bot_y + 100), type_text, fill=(200, 190, 175, 210), font=font_sub)

        # 9. Save and commit
        if output_path is None:
            house_tag = f"h{highlight_house}" if highlight_house else "full"
            seed_hash = hashlib.md5(f"kundli_{house_tag}_{time.time_ns()}".encode()).hexdigest()[:8]
            output_path = GENERATED_BROLL_DIR / f"dynamic_kundli_{house_tag}_{seed_hash}.jpg"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(str(output_path), "JPEG", quality=95)
        logger.info(f"[KundliChartGenerator] Generated dynamic chart for house {highlight_house}: {output_path.name}")
        return output_path

    @staticmethod
    def _make_3d_sphere(img: Image.Image, sz: int, light_dir: Tuple[float, float, float] = (-0.45, -0.45, 0.77)) -> Image.Image:
        """
        Transforms any planar circular or rectangular planet texture into a photorealistic 3D celestial sphere
        with spherical surface projection, diffuse Lambertian terminator, specular highlight, and atmospheric Fresnel limb haze.
        """
        w_in, h_in = img.size
        tex_arr = np.array(img.convert("RGB")).astype(np.float32)

        # True 2D coordinate meshgrid (sz, sz)
        y, x = np.mgrid[:sz, :sz]
        cx = cy = sz / 2.0
        r = sz / 2.0
        nx = (x - cx) / r
        ny = (y - cy) / r
        r2 = nx * nx + ny * ny
        mask = r2 <= 1.0

        nz = np.zeros((sz, sz), dtype=np.float32)
        nz[mask] = np.sqrt(np.maximum(0.0, 1.0 - r2[mask]))

        # Spherical mapping: latitude theta, longitude phi
        theta = np.arcsin(np.clip(ny, -1.0, 1.0))
        cos_theta = np.maximum(np.cos(theta), 1e-4)
        sin_phi = np.clip(nx / cos_theta, -1.0, 1.0)
        phi = np.arcsin(sin_phi)

        map_x = np.clip(((phi / np.pi + 0.5) * (w_in - 1)), 0, w_in - 1).astype(np.float32)
        map_y = np.clip(((theta / np.pi + 0.5) * (h_in - 1)), 0, h_in - 1).astype(np.float32)

        if HAS_CV2 and cv2 is not None:
            sphere_tex = cv2.remap(tex_arr, map_x, map_y, cv2.INTER_LINEAR)
        else:
            ix = np.clip(np.floor(map_x).astype(int), 0, w_in - 1)
            iy = np.clip(np.floor(map_y).astype(int), 0, h_in - 1)
            sphere_tex = tex_arr[iy, ix]

        lx, ly, lz = light_dir
        l_mag = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / l_mag, ly / l_mag, lz / l_mag

        diff = np.maximum(0.0, nx * lx + ny * ly + nz * lz)
        light = 0.30 + 0.70 * diff

        vx, vy, vz = 0.0, 0.0, 1.0
        hx = lx + vx
        hy = ly + vy
        hz = lz + vz
        h_mag = np.sqrt(hx * hx + hy * hy + hz * hz)
        spec = np.maximum(0.0, (nx * hx + ny * hy + nz * hz) / np.maximum(1e-4, h_mag)) ** 20
        fresnel = (1.0 - nz) ** 2.5

        out = np.zeros((sz, sz, 4), dtype=np.uint8)
        for c in range(3):
            ch = sphere_tex[:, :, c] * light + 255.0 * spec * 0.28 + 240.0 * fresnel * 0.32
            out[:, :, c] = np.clip(ch, 0, 255).astype(np.uint8)

        edge = np.clip((1.0 - np.sqrt(r2)) * sz * 0.85, 0.0, 1.0)
        out[:, :, 3] = (edge * 255).astype(np.uint8)

        return Image.fromarray(out, "RGBA")

    @classmethod
    def render_celestial_sphere(cls, planet_key: str, sz: int = 320) -> Image.Image:
        """
        Renders a photorealistic, physically plausible 3D celestial sphere for any of the 9 Vedic planets.
        Uses procedural atmospheric banding, lunar craters, iron-oxide terrain, or solar plasma.
        """
        from config.settings import BASE_DIR
        broll_dir = BASE_DIR / "assets" / "cinematic_broll"

        # Special case: Saturn with 3D rings
        if planet_key == "saturn":
            sat_cutout = Path("output/saturn_3d_feathered.png")
            if not sat_cutout.exists():
                sat_cutout = Path("output/saturn_seamless.png")
            if sat_cutout.exists():
                try:
                    s_img = Image.open(sat_cutout).convert("RGBA")
                    sw = sz
                    sh = int(sw * s_img.height / s_img.width)
                    return s_img.resize((sw, sh), Image.Resampling.LANCZOS)
                except Exception:
                    pass

        # Dedicated high-fidelity procedural generation with spherical projection
        y, x = np.mgrid[:sz, :sz]
        cx = cy = sz / 2.0
        r = sz / 2.0
        nx = (x - cx) / r
        ny = (y - cy) / r
        r2 = nx ** 2 + ny ** 2
        mask = r2 <= 1.0

        nz = np.zeros((sz, sz), dtype=np.float32)
        nz[mask] = np.sqrt(np.maximum(0.0, 1.0 - r2[mask]))

        theta = np.arcsin(np.clip(ny, -1.0, 1.0))
        cos_theta = np.maximum(np.cos(theta), 1e-4)
        phi = np.arcsin(np.clip(nx / cos_theta, -1.0, 1.0))

        u = phi / np.pi + 0.5
        v = theta / np.pi + 0.5

        # Key light from top-left
        lx, ly, lz = -0.45, -0.45, 0.77
        l_mag = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / l_mag, ly / l_mag, lz / l_mag

        diff = np.maximum(0.0, nx * lx + ny * ly + nz * lz)
        vx, vy, vz = 0.0, 0.0, 1.0
        hx, hy, hz = lx + vx, ly + vy, lz + vz
        h_mag = np.sqrt(hx * hx + hy * hy + hz * hz)
        spec = np.maximum(0.0, (nx * hx + ny * hy + nz * hz) / np.maximum(1e-4, h_mag)) ** 22
        fresnel = (1.0 - nz) ** 2.4

        out = np.zeros((sz, sz, 4), dtype=np.float32)

        if planet_key == "sun":
            # Self-luminous solar star: granulation + blazing limb
            gran = np.sin(phi * 24.0) * np.cos(theta * 24.0) * 0.15 + np.sin(phi * 48.0 + theta * 36.0) * 0.10
            limb = 0.65 + 0.35 * nz
            c_core = np.array([255.0, 240.0, 150.0])
            c_mid = np.array([255.0, 180.0, 25.0])
            c_edge = np.array([230.0, 95.0, 10.0])
            t_val = np.clip(nz + gran, 0.0, 1.0)
            col = (1.0 - t_val)[..., None] * c_edge + t_val[..., None] * (0.45 * c_mid + 0.55 * c_core)
            col = col * limb[..., None] * 1.25
            out[:, :, :3] = col

        elif planet_key == "jupiter":
            # Jovian gas bands + Great Red Spot
            bands = np.sin(v * 28.0) * 0.45 + np.sin(v * 56.0 + np.sin(u * 12.0) * 1.5) * 0.25 + np.sin(u * 8.0) * 0.10
            spot_dist = np.sqrt(((u - 0.45) * 2.5) ** 2 + ((v - 0.62) * 5.0) ** 2)
            spot = np.clip(1.0 - spot_dist, 0.0, 1.0) ** 2
            c_cream = np.array([238.0, 222.0, 192.0])
            c_terra = np.array([168.0, 92.0, 55.0])
            c_amber = np.array([205.0, 145.0, 88.0])
            c_redspot = np.array([180.0, 50.0, 30.0])
            b_val = np.clip((bands + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - b_val)[..., None] * c_terra + b_val[..., None] * (0.6 * c_amber + 0.4 * c_cream)
            base = (1.0 - spot)[..., None] * base + spot[..., None] * c_redspot
            light = 0.32 + 0.68 * diff
            out[:, :, :3] = base * light[..., None] + 255.0 * spec[..., None] * 0.22 + np.array([245.0, 185.0, 85.0]) * fresnel[..., None] * 0.38

        elif planet_key == "mars":
            # Rust terrain + darker volcanic features + polar ice cap
            terrain = np.sin(u * 14.0) * np.cos(v * 10.0) * 0.3 + np.sin(u * 28.0 + v * 20.0) * 0.2
            polar = np.clip((v - 0.88) * 8.0, 0.0, 1.0)
            c_rust = np.array([215.0, 85.0, 35.0])
            c_dark = np.array([125.0, 45.0, 20.0])
            c_ice = np.array([245.0, 240.0, 240.0])
            val = np.clip((terrain + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - val)[..., None] * c_dark + val[..., None] * c_rust
            base = (1.0 - polar)[..., None] * base + polar[..., None] * c_ice
            light = 0.28 + 0.72 * diff
            out[:, :, :3] = base * light[..., None] + 255.0 * spec[..., None] * 0.16 + np.array([255.0, 110.0, 50.0]) * fresnel[..., None] * 0.32

        elif planet_key == "mercury":
            # Gray cratered rocky world
            craters = np.sin(u * 32.0) * np.sin(v * 32.0) * 0.25 + np.sin(u * 64.0 + v * 48.0) * 0.15
            c_rock = np.array([165.0, 160.0, 155.0])
            c_shadow = np.array([78.0, 75.0, 72.0])
            val = np.clip((craters + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - val)[..., None] * c_shadow + val[..., None] * c_rock
            light = 0.22 + 0.78 * diff
            out[:, :, :3] = base * light[..., None] + 255.0 * spec[..., None] * 0.35 + np.array([205.0, 215.0, 225.0]) * fresnel[..., None] * 0.22

        elif planet_key == "venus":
            # Sulfuric acid pearlescent cloud deck
            clouds = np.sin(v * 18.0 + np.sin(u * 6.0) * 2.0) * 0.25 + np.cos(u * 12.0) * 0.15
            c_gold = np.array([245.0, 228.0, 180.0])
            c_cream = np.array([255.0, 245.0, 215.0])
            val = np.clip((clouds + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - val)[..., None] * c_gold + val[..., None] * c_cream
            light = 0.35 + 0.65 * diff
            out[:, :, :3] = base * light[..., None] + 255.0 * spec[..., None] * 0.26 + np.array([255.0, 235.0, 175.0]) * fresnel[..., None] * 0.42

        elif planet_key == "moon":
            # Lunar maria (dark basalt) and bright highlands
            maria = np.sin(u * 12.0) * np.sin(v * 8.0) * 0.4 + np.sin(u * 24.0 + v * 16.0) * 0.2
            c_maria = np.array([92.0, 98.0, 108.0])
            c_highland = np.array([215.0, 220.0, 230.0])
            val = np.clip((maria + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - val)[..., None] * c_maria + val[..., None] * c_highland
            light = 0.25 + 0.75 * diff
            out[:, :, :3] = base * light[..., None] + 255.0 * spec[..., None] * 0.22 + np.array([195.0, 220.0, 255.0]) * fresnel[..., None] * 0.35

        elif planet_key == "saturn":
            # Saturn body banded atmosphere
            bands = np.sin(v * 36.0) * 0.35 + np.sin(v * 18.0) * 0.20
            c_amber = np.array([215.0, 180.0, 120.0])
            c_gold = np.array([238.0, 210.0, 150.0])
            val = np.clip((bands + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - val)[..., None] * c_amber + val[..., None] * c_gold
            light = 0.30 + 0.70 * diff
            out[:, :, :3] = base * light[..., None] + 255.0 * spec[..., None] * 0.25 + np.array([255.0, 225.0, 150.0]) * fresnel[..., None] * 0.35

        elif planet_key == "rahu":
            # Obsidian shadow plasma sphere
            plasma = np.sin(u * 16.0 + v * 16.0) * 0.3 + np.sin(u * 32.0) * 0.2
            c_obsidian = np.array([26.0, 16.0, 40.0])
            c_violet = np.array([98.0, 48.0, 145.0])
            val = np.clip((plasma + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - val)[..., None] * c_obsidian + val[..., None] * c_violet
            light = 0.40 + 0.60 * diff
            out[:, :, :3] = base * light[..., None] + np.array([165.0, 95.0, 245.0]) * fresnel[..., None] * 0.70

        elif planet_key == "ketu":
            # Smoky bronze mystic sphere
            smoke = np.sin(u * 14.0 - v * 14.0) * 0.3 + np.cos(v * 24.0) * 0.2
            c_dark = np.array([42.0, 24.0, 16.0])
            c_bronze = np.array([145.0, 78.0, 42.0])
            val = np.clip((smoke + 1.0) * 0.5, 0.0, 1.0)
            base = (1.0 - val)[..., None] * c_dark + val[..., None] * c_bronze
            light = 0.35 + 0.65 * diff
            out[:, :, :3] = base * light[..., None] + np.array([225.0, 135.0, 65.0]) * fresnel[..., None] * 0.58

        else:
            light = 0.30 + 0.70 * diff
            out[:, :, :3] = np.array([205.0, 185.0, 145.0]) * light[..., None]

        edge = np.clip((1.0 - np.sqrt(r2)) * sz * 0.90, 0.0, 1.0)
        out[:, :, 3] = edge * 255.0

        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")

        # If Saturn procedural: render 3D rings around it
        if planet_key == "saturn":
            rw = int(sz * 1.95)
            rh = int(sz * 0.65)
            ring_canvas = Image.new("RGBA", (rw, sz + rh // 2), (0, 0, 0, 0))
            rcx, rcy = rw // 2, (sz + rh // 2) // 2

            # Back half of rings
            back_rings = Image.new("RGBA", (rw, sz + rh // 2), (0, 0, 0, 0))
            br_draw = ImageDraw.Draw(back_rings)
            for r_out, r_in, col in [(rw // 2, int(rw * 0.36), (220, 185, 115, 180)), (int(rw * 0.44), int(rw * 0.38), (180, 145, 85, 140))]:
                br_draw.ellipse([rcx - r_out, rcy - int(r_out * 0.28), rcx + r_out, rcy + int(r_out * 0.28)], fill=col)
                br_draw.ellipse([rcx - r_in, rcy - int(r_in * 0.28), rcx + r_in, rcy + int(r_in * 0.28)], fill=(0, 0, 0, 0))

            # Mask back rings behind planet top
            ring_canvas = Image.alpha_composite(ring_canvas, back_rings)
            # Paste planet
            px0 = rcx - sz // 2
            py0 = rcy - sz // 2
            ring_canvas.paste(res, (px0, py0), res)

            # Front half of rings
            front_rings = Image.new("RGBA", (rw, sz + rh // 2), (0, 0, 0, 0))
            fr_draw = ImageDraw.Draw(front_rings)
            for r_out, r_in, col in [(rw // 2, int(rw * 0.36), (235, 195, 125, 210)), (int(rw * 0.44), int(rw * 0.38), (190, 155, 95, 160))]:
                fr_draw.ellipse([rcx - r_out, rcy - int(r_out * 0.28), rcx + r_out, rcy + int(r_out * 0.28)], fill=col)
                fr_draw.ellipse([rcx - r_in, rcy - int(r_in * 0.28), rcx + r_in, rcy + int(r_in * 0.28)], fill=(0, 0, 0, 0))

            # Crop only lower half of front rings
            mask_front = Image.new("L", (rw, sz + rh // 2), 0)
            mdraw = ImageDraw.Draw(mask_front)
            mdraw.rectangle([0, rcy, rw, sz + rh // 2], fill=255)
            front_rings.putalpha(ImageChops.multiply(front_rings.split()[3], mask_front))
            ring_canvas = Image.alpha_composite(ring_canvas, front_rings)
            return ring_canvas

        return res

    @classmethod
    def generate_3d_kundli_planet_scene(
        cls,
        scene_dict: Dict[str, Any],
        topic: str = "",
        scene_idx: int = 0,
        output_path: Optional[Path] = None,
        chart_data: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Renders a script-driven, authentic 1080x1920 3D Vedic visual without random inference.
        Differentiates between:
        - Mode A: HOUSE_ONLY
        - Mode B: PLANET_ONLY
        - Mode C: PLANET_IN_HOUSE
        - Mode D: CONJUNCTION
        - Mode E: ASPECT (DRISHTI)
        - Mode F: GENERAL
        - Mode MULTI_PLANET: Distinct non-conjoined planetary energies
        """
        from config.settings import BASE_DIR, DEFAULT_FONT_PATH, FALLBACK_FONT_PATH
        broll_dir = BASE_DIR / "assets" / "cinematic_broll"

        spoken = str(scene_dict.get("spoken_line", "")).strip()
        on_screen = str(scene_dict.get("on_screen_text", "")).strip()
        vis_desc = str(scene_dict.get("visual_description", "")).strip()
        # Spoken narration is the ground truth. Use on_screen / vis_desc only as fallback.
        scene_narration = spoken or on_screen or vis_desc
        passed_chart_data = chart_data or scene_dict.get("chart_data")
        plan = cls.parse_astrology_scene(scene_narration, fallback_topic=topic, chart_data=passed_chart_data)

        logger.info(
            f"[KundliChartGenerator] Scene {scene_idx + 1} Plan: intent={plan.intent}, "
            f"primary_house={plan.primary_house}, target_house={plan.target_house}, "
            f"planets={plan.planets}, badge='{plan.badge_title}'"
        )

        width, height = 1080, 1920

        # Load fonts
        try:
            font_title = ImageFont.truetype(DEFAULT_FONT_PATH, 34)
            font_badge = ImageFont.truetype(DEFAULT_FONT_PATH, 24)
            font_num = ImageFont.truetype(DEFAULT_FONT_PATH, 26)
            font_header = ImageFont.truetype(DEFAULT_FONT_PATH, 28)
            font_sub = ImageFont.truetype(FALLBACK_FONT_PATH, 20)
        except Exception:
            try:
                font_title = ImageFont.truetype("arial.ttf", 34)
                font_badge = ImageFont.truetype("arial.ttf", 24)
                font_num = ImageFont.truetype("arial.ttf", 26)
                font_header = ImageFont.truetype("arial.ttf", 28)
                font_sub = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                font_title = ImageFont.load_default()
                font_badge = ImageFont.load_default()
                font_num = ImageFont.load_default()
                font_header = ImageFont.load_default()
                font_sub = ImageFont.load_default()

        # -------------------------------------------------------------
        # MODE B: PLANET_ONLY (Deep Space Celestial Realm, NO Chart Floor!)
        # -------------------------------------------------------------
        if plan.intent == "PLANET_ONLY" and plan.planets:
            planet_key = plan.planets[0]
            p_hi, p_en = PLANET_DISPLAY_NAMES.get(planet_key, (planet_key.upper(), planet_key.upper()))

            # Deep cosmic starfield canvas
            canvas = Image.new("RGBA", (width, height), (6, 4, 14, 255))
            c_draw = ImageDraw.Draw(canvas)

            # Cosmic Nebula Glow
            nebula = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ndraw = ImageDraw.Draw(nebula)
            glow_col = (255, 175, 45, 110) if planet_key in ["sun", "jupiter"] else (
                (255, 60, 25, 90) if planet_key == "mars" else (
                    (140, 75, 230, 95) if planet_key in ["rahu", "ketu"] else (210, 225, 255, 90)
                )
            )
            ndraw.ellipse([width // 2 - 420, 850 - 420, width // 2 + 420, 850 + 420], fill=glow_col)
            nebula = nebula.filter(ImageFilter.GaussianBlur(110))
            canvas = Image.alpha_composite(canvas, nebula)

            # Sacred Geometrical Mandalas in background
            yantra_path = broll_dir / "sacred_geometric_yantra.jpg"
            if yantra_path.exists():
                try:
                    y_img = Image.open(yantra_path).convert("RGBA")
                    y_res = ImageOps.fit(y_img, (760, 760), Image.Resampling.LANCZOS)
                    rad_mask = Image.new("L", (760, 760), 0)
                    rmdraw = ImageDraw.Draw(rad_mask)
                    rmdraw.ellipse([40, 40, 720, 720], fill=255)
                    rad_mask = rad_mask.filter(ImageFilter.GaussianBlur(60))
                    y_mask = ImageChops.multiply(y_res.convert("L").filter(ImageFilter.GaussianBlur(3)), rad_mask)
                    y_fade = ImageEnhance.Brightness(y_res).enhance(0.18)
                    y_fade.putalpha(y_mask)
                    canvas.paste(y_fade, (width // 2 - 380, 850 - 380), y_fade)
                except Exception:
                    pass

            # Render Large Celestial Sphere
            sphere_sz = 520
            p_sphere = cls.render_celestial_sphere(planet_key, sphere_sz)

            # Planet Aura
            p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            p_adraw = ImageDraw.Draw(p_aura)
            p_adraw.ellipse([width // 2 - 320, 850 - 320, width // 2 + 320, 850 + 320], fill=glow_col)
            if planet_key == "sun":
                # Sun Coronal Flares
                for ang in range(0, 360, 8):
                    rad = math.radians(ang)
                    fl_len = 310 + (ang % 24) * 5
                    p_adraw.line(
                        [(width // 2, 850), (width // 2 + math.cos(rad) * fl_len, 850 + math.sin(rad) * fl_len)],
                        fill=(255, 225, 90, 180),
                        width=4,
                    )
            p_aura = p_aura.filter(ImageFilter.GaussianBlur(34))
            canvas = Image.alpha_composite(canvas, p_aura)

            # Paste planet sphere
            px0 = width // 2 - p_sphere.width // 2
            py0 = 850 - p_sphere.height // 2
            canvas.paste(p_sphere, (px0, py0), p_sphere)

            # Top Floating Badge Pill
            cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)

            # Bottom Celestial Card
            cls._draw_bottom_celestial_card(
                canvas,
                title=f"{p_hi} ({p_en}) • COSMIC RULERSHIP",
                subtitle=plan.subtitle,
                width=width,
                bottom_y=1420,
                font_title=font_title,
                font_sub=font_sub,
            )

            # Save and return
            return cls._save_scene_output(canvas, topic, scene_idx, "planet_only", output_path)

        # -------------------------------------------------------------
        # MODE MULTI_PLANET (Distinct Non-Conjoined Planet Archetypes)
        # -------------------------------------------------------------
        elif plan.intent == "MULTI_PLANET" and plan.planets:
            canvas = Image.new("RGBA", (width, height), (6, 4, 14, 255))
            nebula = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ndraw = ImageDraw.Draw(nebula)
            ndraw.ellipse([width // 2 - 450, 850 - 450, width // 2 + 450, 850 + 450], fill=(210, 160, 45, 80))
            nebula = nebula.filter(ImageFilter.GaussianBlur(120))
            canvas = Image.alpha_composite(canvas, nebula)

            planets = plan.planets
            n_p = len(planets)
            if n_p == 2:
                centers = [(width // 2 - 240, 840), (width // 2 + 240, 840)]
                p_sz = 300
            elif n_p == 3:
                centers = [(width // 2 - 300, 840), (width // 2, 840), (width // 2 + 300, 840)]
                p_sz = 260
            elif n_p == 4:
                centers = [
                    (width // 2 - 330, 840),
                    (width // 2 - 110, 840),
                    (width // 2 + 110, 840),
                    (width // 2 + 330, 840),
                ]
                p_sz = 205
            else:
                centers = []
                spacing = min(220, (width - 160) // n_p)
                start_x = width // 2 - (n_p - 1) * spacing // 2
                for i in range(n_p):
                    centers.append((start_x + i * spacing, 840))
                p_sz = max(130, spacing - 25)

            for idx, p_key in enumerate(planets):
                cx, cy = centers[idx]
                p_sphere = cls.render_celestial_sphere(p_key, p_sz)
                p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                p_adraw = ImageDraw.Draw(p_aura)
                g_col = cls._get_planet_glow(p_key)
                p_adraw.ellipse([cx - p_sz // 2 - 25, cy - p_sz // 2 - 25, cx + p_sz // 2 + 25, cy + p_sz // 2 + 25], fill=g_col)
                p_aura = p_aura.filter(ImageFilter.GaussianBlur(24))
                canvas = Image.alpha_composite(canvas, p_aura)
                canvas.paste(p_sphere, (cx - p_sz // 2, cy - p_sz // 2), p_sphere)

            cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
            card_title = "CONTRASTING PLANETARY FORCES" if plan.relationship == "contrast" else (
                "NO CONJUNCTION • INDEPENDENT FORCES" if plan.relationship == "no_conjunction" else "DISTINCT PLANETARY FORCES"
            )
            cls._draw_bottom_celestial_card(
                canvas,
                title=card_title,
                subtitle=plan.subtitle,
                width=width,
                bottom_y=1420,
                font_title=font_title,
                font_sub=font_sub,
            )
            return cls._save_scene_output(canvas, topic, scene_idx, "multi_planet", output_path)
            cls._draw_bottom_celestial_card(
                canvas,
                title="DISTINCT PLANETARY FORCES",
                subtitle=plan.subtitle,
                width=width,
                bottom_y=1420,
                font_title=font_title,
                font_sub=font_sub,
            )
            return cls._save_scene_output(canvas, topic, scene_idx, "multi_planet_contrast", output_path)

        # -------------------------------------------------------------
        # 3D PERSPECTIVE KUNDLI CANVAS SETUP (Modes A, C, D, E, F)
        # -------------------------------------------------------------
        src_quad = np.float32([[0, 0], [1000, 0], [1000, 1000], [0, 1000]])
        dst_quad = np.float32([[210, 560], [870, 560], [970, 1260], [110, 1260]])

        if HAS_CV2 and cv2 is not None:
            M = cv2.getPerspectiveTransform(src_quad, dst_quad)
        else:
            A, B = [], []
            for i in range(4):
                x_val, y_val = src_quad[i][0], src_quad[i][1]
                u_val, v_val = dst_quad[i][0], dst_quad[i][1]
                A.append([x_val, y_val, 1, 0, 0, 0, -u_val * x_val, -u_val * y_val])
                A.append([0, 0, 0, x_val, y_val, 1, -v_val * x_val, -v_val * y_val])
                B.append(u_val)
                B.append(v_val)
            h_vec = np.linalg.solve(np.array(A, dtype=np.float64), np.array(B, dtype=np.float64))
            M = np.array([
                [h_vec[0], h_vec[1], h_vec[2]],
                [h_vec[3], h_vec[4], h_vec[5]],
                [h_vec[6], h_vec[7], 1.0]
            ], dtype=np.float32)

        def project_pt(u: float, v: float, h: float = 0.0) -> Tuple[float, float, float]:
            if HAS_CV2 and cv2 is not None:
                pt = np.array([[[u, v]]], dtype=np.float32)
                proj = cv2.perspectiveTransform(pt, M)[0][0]
                sx, sy = float(proj[0]), float(proj[1])
            else:
                res = M @ np.array([u, v, 1.0], dtype=np.float64)
                w_val = res[2] if abs(res[2]) > 1e-8 else 1e-8
                sx, sy = float(res[0] / w_val), float(res[1] / w_val)
            depth_scale = 0.74 + (v / 1000.0) * 0.36
            sy = sy - (h * depth_scale)
            return sx, sy, float(depth_scale)

        def project_poly(pts_uv: List[Tuple[float, float]], h: float = 0.0) -> List[Tuple[float, float]]:
            return [project_pt(u_pt, v_pt, h)[:2] for u_pt, v_pt in pts_uv]

        u_mid, v_mid = 500.0, 500.0
        p_tl = (250.0, 250.0)
        p_tr = (750.0, 250.0)
        p_bl = (250.0, 750.0)
        p_br = (750.0, 750.0)

        uv_polygons: Dict[int, List[Tuple[float, float]]] = {
            1: [(u_mid, 0.0), p_tr, (u_mid, v_mid), p_tl],
            2: [(0.0, 0.0), (u_mid, 0.0), p_tl],
            3: [(0.0, 0.0), (0.0, v_mid), p_tl],
            4: [p_tl, (0.0, v_mid), p_bl, (u_mid, v_mid)],
            5: [(0.0, v_mid), (0.0, 1000.0), p_bl],
            6: [(0.0, 1000.0), (u_mid, 1000.0), p_bl],
            7: [(u_mid, v_mid), p_bl, (u_mid, 1000.0), p_br],
            8: [(u_mid, 1000.0), (1000.0, 1000.0), p_br],
            9: [(1000.0, 1000.0), (1000.0, v_mid), p_br],
            10: [(u_mid, v_mid), p_br, (1000.0, v_mid), p_tr],
            11: [(1000.0, v_mid), (1000.0, 0.0), p_tr],
            12: [(u_mid, 0.0), (1000.0, 0.0), p_tr],
        }

        def get_uv_centroid(poly: List[Tuple[float, float]]) -> Tuple[float, float]:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            return sum(xs) / len(xs), sum(ys) / len(ys)

        # Base backdrop: authentic ancient parchment with vignette
        parchment_path = broll_dir / "authentic_vedic_kundli_parchment.jpg"
        if parchment_path.exists():
            base_raw = Image.open(parchment_path).convert("RGB")
            base_raw = ImageOps.fit(base_raw, (width, height), Image.Resampling.LANCZOS)
            base_blur = base_raw.filter(ImageFilter.GaussianBlur(28))
            base_dark = ImageEnhance.Brightness(base_blur).enhance(0.48)
            base_graded = ImageEnhance.Contrast(base_dark).enhance(1.20)

            vignette = Image.new("L", (width, height), 0)
            vdraw = ImageDraw.Draw(vignette)
            vdraw.ellipse([60, 140, width - 60, height - 230], fill=255)
            vignette = vignette.filter(ImageFilter.GaussianBlur(140))
            v_arr = np.array(vignette, dtype=float) / 255.0
            bg_arr = np.array(base_graded, dtype=float)
            darkened = bg_arr * (0.35 + 0.65 * v_arr[..., None])
            canvas = Image.fromarray(np.clip(darkened, 0, 255).astype(np.uint8)).convert("RGBA")
        else:
            canvas = Image.new("RGBA", (width, height), (10, 8, 18, 255))

        # Pedestal Base
        pedestal = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(pedestal)
        c_bl, c_br = (110, 1260), (970, 1260)
        b_bl, b_br = (110, 1298), (970, 1298)
        pdraw.polygon([c_bl, c_br, b_br, b_bl], fill=(22, 16, 12, 235))
        pdraw.line([b_bl, b_br], fill=(160, 120, 40, 200), width=2)
        pdraw.line([c_bl, b_bl], fill=(120, 90, 30, 160), width=2)
        pdraw.line([c_br, b_br], fill=(120, 90, 30, 160), width=2)

        altar_shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        as_draw = ImageDraw.Draw(altar_shadow)
        as_draw.polygon([(100, 1290), (980, 1290), (1010, 1335), (70, 1335)], fill=(5, 3, 2, 190))
        altar_shadow = altar_shadow.filter(ImageFilter.GaussianBlur(16))
        canvas = Image.alpha_composite(canvas, altar_shadow)
        canvas = Image.alpha_composite(canvas, pedestal)

        # Highlight House Selection (NEVER invent House 1 when no house is established!)
        primary_h = plan.primary_house
        target_h = plan.target_house

        # Active Chamber Volumetric Glow
        active_houses: List[int] = []
        if plan.intent == "ASPECT":
            if target_h:
                active_houses.append(target_h)
            if primary_h:
                active_houses.append(primary_h)
        elif primary_h:
            active_houses.append(primary_h)

        for act_h in active_houses:
            target_poly_uv = uv_polygons.get(act_h, uv_polygons[1])
            proj_poly = project_poly(target_poly_uv, h=0)
            uc, vc = get_uv_centroid(target_poly_uv)
            scx, scy, _ = project_pt(uc, vc, h=0)

            glow_rgb = (240, 165, 35)
            halo_rgb = (130, 80, 15)
            border_rgb = (255, 230, 110)
            if plan.planets and plan.planets[0] == "mars":
                glow_rgb = (240, 60, 25)
                halo_rgb = (140, 25, 10)
                border_rgb = (255, 120, 60)

            bloom = Image.new("RGB", (width, height), (0, 0, 0))
            bdraw = ImageDraw.Draw(bloom)
            bdraw.ellipse([scx - 220, scy - 220, scx + 220, scy + 220], fill=halo_rgb)
            bdraw.polygon(proj_poly, fill=glow_rgb)
            bdraw.line(proj_poly + [proj_poly[0]], fill=border_rgb, width=10)
            bloom_blur = bloom.filter(ImageFilter.GaussianBlur(32))

            sharp = Image.new("RGB", (width, height), (0, 0, 0))
            sdraw = ImageDraw.Draw(sharp)
            sdraw.polygon(proj_poly, fill=glow_rgb)
            sdraw.line(proj_poly + [proj_poly[0]], fill=border_rgb, width=4)
            sharp_blur = sharp.filter(ImageFilter.GaussianBlur(4))

            bg_rgb = np.array(canvas.convert("RGB"), dtype=float)
            b_arr = (np.array(bloom_blur, dtype=float) + np.array(sharp_blur, dtype=float)) / 255.0
            screened = 1.0 - (1.0 - bg_rgb / 255.0) * (1.0 - np.clip(b_arr, 0.0, 0.95))
            canvas = Image.fromarray(np.clip(screened * 255.0, 0, 255).astype(np.uint8)).convert("RGBA")

            # Volumetric Light Shaft
            pillar = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            pildraw = ImageDraw.Draw(pillar)
            poly_elev = project_poly(target_poly_uv, h=80)
            for p0, p1 in zip(proj_poly, poly_elev):
                pildraw.line([p0, p1], fill=(255, 215, 60, 65), width=2)
            pildraw.polygon(poly_elev, fill=(255, 200, 40, 30))
            pillar = pillar.filter(ImageFilter.GaussianBlur(8))
            canvas = Image.alpha_composite(canvas, pillar)

        # 3D Engraved Gold Lines
        draw = ImageDraw.Draw(canvas)
        def _draw_3d_line(u1: float, v1: float, u2: float, v2: float, w: int = 3) -> None:
            p1 = project_pt(u1, v1, h=0)[:2]
            p2 = project_pt(u2, v2, h=0)[:2]
            draw.line([p1, p2], fill=(15, 10, 5, 140), width=w + 2)
            draw.line([p1, p2], fill=(230, 190, 65, 245), width=w)

        _draw_3d_line(0, 0, 1000, 0, 4)
        _draw_3d_line(1000, 0, 1000, 1000, 4)
        _draw_3d_line(1000, 1000, 0, 1000, 4)
        _draw_3d_line(0, 1000, 0, 0, 4)
        _draw_3d_line(0, 0, 1000, 1000, 3)
        _draw_3d_line(1000, 0, 0, 1000, 3)
        _draw_3d_line(500, 0, 1000, 500, 3)
        _draw_3d_line(1000, 500, 500, 1000, 3)
        _draw_3d_line(500, 1000, 0, 500, 3)
        _draw_3d_line(0, 500, 500, 0, 3)

        # Roman Numerals
        for h_num, poly_uv in uv_polygons.items():
            h_uc, h_vc = get_uv_centroid(poly_uv)
            du = (h_uc - 500.0) * 0.35
            dv = (h_vc - 500.0) * 0.35
            nx_pt, ny_pt, _ = project_pt(h_uc + du, h_vc + dv, h=0)
            rom = ROMAN_NUMS[h_num]
            bbox = draw.textbbox((0, 0), rom, font=font_num)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            is_active = (h_num in active_houses)
            col = (255, 245, 180, 245) if is_active else (160, 135, 100, 150)
            draw.text((nx_pt - tw / 2, ny_pt - th / 2), rom, fill=col, font=font_num)

        # -------------------------------------------------------------
        # MODE A: HOUSE_ONLY
        # -------------------------------------------------------------
        if plan.intent == "HOUSE_ONLY":
            if primary_h is not None:
                h_active = primary_h
                uc_a, vc_a = get_uv_centroid(uv_polygons.get(h_active, uv_polygons[1]))
                sx_fl, sy_fl, _ = project_pt(uc_a, vc_a, h=0)

                particles = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                p_draw = ImageDraw.Draw(particles)
                for p_r, p_a, p_sz_dot in [
                    (60, 20, 6), (120, 45, 8), (180, -10, 6), (240, 60, 9),
                    (90, -35, 5), (150, 15, 8), (210, 30, 7), (130, 70, 7), (80, 50, 5)
                ]:
                    pr = math.radians(p_a)
                    px = sx_fl + math.cos(pr) * p_r * 0.7
                    py = sy_fl - math.sin(pr) * p_r
                    p_draw.ellipse([px - p_sz_dot, py - p_sz_dot, px + p_sz_dot, py + p_sz_dot], fill=(255, 235, 130, 230))
                p_blur = particles.filter(ImageFilter.GaussianBlur(4))
                canvas = Image.alpha_composite(canvas, p_blur)
                canvas = Image.alpha_composite(canvas, particles)

                cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                return cls._save_scene_output(canvas, topic, scene_idx, f"h{h_active}_only", output_path)
            else:
                cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                return cls._save_scene_output(canvas, topic, scene_idx, "general_chart", output_path)

        # -------------------------------------------------------------
        # MODE C: PLANET_IN_HOUSE
        # -------------------------------------------------------------
        elif plan.intent == "PLANET_IN_HOUSE":
            if primary_h is not None and plan.planets:
                p_key = plan.planets[0]
                h_active = primary_h
                uc_c, vc_c = get_uv_centroid(uv_polygons.get(h_active, uv_polygons[1]))
                sx_fl, sy_fl, _ = project_pt(uc_c, vc_c, h=0)
                sx_pl, sy_pl, scale_p = project_pt(uc_c, vc_c, h=105)

                # Floor Contact Shadow directly below
                sh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                shdraw = ImageDraw.Draw(sh)
                shdraw.ellipse([sx_fl - 95, sy_fl - 25, sx_fl + 95, sy_fl + 25], fill=(10, 5, 2, 175))
                sh = sh.filter(ImageFilter.GaussianBlur(16))
                canvas = Image.alpha_composite(canvas, sh)

                # Render Planet Sphere
                p_sz = int(210 * scale_p)
                p_sphere = cls.render_celestial_sphere(p_key, p_sz)

                # Planet Aura
                p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                p_adraw = ImageDraw.Draw(p_aura)
                glow_col = cls._get_planet_glow(p_key)
                p_adraw.ellipse([sx_pl - p_sz // 2 - 30, sy_pl - p_sz // 2 - 30, sx_pl + p_sz // 2 + 30, sy_pl + p_sz // 2 + 30], fill=glow_col)
                if p_key == "sun":
                    for a in range(0, 360, 12):
                        rad = math.radians(a)
                        flen = p_sz // 2 + 35 + (a % 30) * 2
                        p_adraw.line([(sx_pl, sy_pl), (sx_pl + math.cos(rad) * flen, sy_pl + math.sin(rad) * flen)], fill=(255, 220, 70, 160), width=3)
                p_aura = p_aura.filter(ImageFilter.GaussianBlur(24))
                canvas = Image.alpha_composite(canvas, p_aura)

                canvas.paste(p_sphere, (int(sx_pl - p_sphere.width // 2), int(sy_pl - p_sphere.height // 2)), p_sphere)

                cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                return cls._save_scene_output(canvas, topic, scene_idx, f"h{h_active}_{p_key}", output_path)
            elif plan.planets:
                # Planet known, house unknown -> DO NOT INVENT A HOUSE! Render in celestial space
                plan_copy = AstrologyScenePlan(
                    intent="PLANET_ONLY",
                    primary_house=None,
                    planets=plan.planets,
                    badge_title=plan.badge_title,
                    subtitle=plan.subtitle,
                    relationship="archetype",
                )
                return cls._render_planet_only_scene(canvas, plan_copy, topic, scene_idx, output_path, font_title, font_sub, font_header)
            elif primary_h is not None:
                # House known, planet unknown -> DO NOT INVENT A PLANET!
                plan_copy = AstrologyScenePlan(
                    intent="HOUSE_ONLY",
                    primary_house=primary_h,
                    planets=[],
                    badge_title=plan.badge_title,
                    subtitle=plan.subtitle,
                    relationship="house_activation",
                )
                cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                return cls._save_scene_output(canvas, topic, scene_idx, f"h{primary_h}_only", output_path)
            else:
                cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                return cls._save_scene_output(canvas, topic, scene_idx, "general_chart", output_path)

        # -------------------------------------------------------------
        # MODE D: CONJUNCTION (All Identified Planets Together in One House)
        # -------------------------------------------------------------
        elif plan.intent == "CONJUNCTION":
            if plan.planets:
                planets = plan.planets
                if primary_h is not None:
                    h_active = primary_h
                    uc_d, vc_d = get_uv_centroid(uv_polygons.get(h_active, uv_polygons[1]))
                    sx_fl, sy_fl, _ = project_pt(uc_d, vc_d, h=0)

                    # Floor Contact Shadow
                    sh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    shdraw = ImageDraw.Draw(sh)
                    shdraw.ellipse([sx_fl - 140, sy_fl - 32, sx_fl + 140, sy_fl + 32], fill=(10, 5, 2, 185))
                    sh = sh.filter(ImageFilter.GaussianBlur(18))
                    canvas = Image.alpha_composite(canvas, sh)

                    # Support ALL planets (2, 3, 4, 5+) in conjunction cleanly without truncation!
                    n_p = len(planets)
                    if n_p == 1:
                        offsets = [(0.0, 0.0)]
                        scale_factor = 1.0
                    elif n_p == 2:
                        offsets = [(-48.0, 0.0), (48.0, 0.0)]
                        scale_factor = 0.82
                    elif n_p == 3:
                        offsets = [(-56.0, 15.0), (0.0, -32.0), (56.0, 15.0)]
                        scale_factor = 0.70
                    elif n_p == 4:
                        offsets = [(-48.0, 0.0), (0.0, -34.0), (48.0, 0.0), (0.0, 34.0)]
                        scale_factor = 0.58
                    else:
                        offsets = []
                        for i in range(n_p):
                            ang = i * (2.0 * math.pi / n_p)
                            offsets.append((55.0 * math.cos(ang), 30.0 * math.sin(ang)))
                        scale_factor = max(0.42, 0.58 - (n_p - 4) * 0.04)

                    planet_positions = []
                    for idx, p_key in enumerate(planets):
                        u_off, v_off = offsets[idx] if idx < len(offsets) else (0.0, 0.0)
                        sx_pl, sy_pl, scale_p = project_pt(uc_d + u_off, vc_d + v_off, h=105)
                        planet_positions.append((sx_pl, sy_pl))

                        p_sz = int(190 * scale_p * scale_factor)
                        p_sphere = cls.render_celestial_sphere(p_key, p_sz)

                        p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                        p_adraw = ImageDraw.Draw(p_aura)
                        glow_col = cls._get_planet_glow(p_key)
                        p_adraw.ellipse([sx_pl - p_sz // 2 - 20, sy_pl - p_sz // 2 - 20, sx_pl + p_sz // 2 + 20, sy_pl + p_sz // 2 + 20], fill=glow_col)
                        p_aura = p_aura.filter(ImageFilter.GaussianBlur(20))
                        canvas = Image.alpha_composite(canvas, p_aura)
                        canvas.paste(p_sphere, (int(sx_pl - p_sphere.width // 2), int(sy_pl - p_sphere.height // 2)), p_sphere)

                    # Golden Linking Energy Arc connecting all conjoined planets
                    if len(planet_positions) >= 2:
                        arc_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                        adraw = ImageDraw.Draw(arc_layer)
                        for i in range(len(planet_positions) - 1):
                            adraw.line([planet_positions[i], planet_positions[i + 1]], fill=(255, 235, 140, 220), width=4)
                        if len(planet_positions) >= 3:
                            adraw.line([planet_positions[-1], planet_positions[0]], fill=(255, 235, 140, 160), width=2)
                        arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(4))
                        canvas = Image.alpha_composite(canvas, arc_layer)

                    cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                    return cls._save_scene_output(canvas, topic, scene_idx, f"h{h_active}_conj", output_path)
                else:
                    # Conjunction established without a house -> DO NOT INVENT A HOUSE! Render in celestial space
                    return cls._render_celestial_conjunction(canvas, plan, topic, scene_idx, output_path, font_title, font_sub, font_header)
            else:
                cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                return cls._save_scene_output(canvas, topic, scene_idx, "general_chart", output_path)

        # -------------------------------------------------------------
        # MODE E: ASPECT / DRISHTI
        # -------------------------------------------------------------
        elif plan.intent == "ASPECT":
            src_h = plan.primary_house
            tgt_h = plan.target_house
            p_key = plan.planets[0] if plan.planets else None

            if tgt_h is not None:
                # Target House Coordinates
                uc_tgt, vc_tgt = get_uv_centroid(uv_polygons.get(tgt_h, uv_polygons[1]))
                tx, ty, _ = project_pt(uc_tgt, vc_tgt, h=0)

                # Impact Shockwave Mandala on Target House
                beam_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                bdraw = ImageDraw.Draw(beam_layer)
                bdraw.ellipse([tx - 50, ty - 18, tx + 50, ty + 18], fill=(255, 215, 60, 130), outline=(255, 245, 140, 245), width=2)
                bdraw.ellipse([tx - 75, ty - 26, tx + 75, ty + 26], outline=(255, 215, 60, 160), width=1)

                # Case 1: Verified/Explicit source house is known
                if src_h is not None:
                    uc_src, vc_src = get_uv_centroid(uv_polygons.get(src_h, uv_polygons[1]))
                    sx_fl, sy_fl, _ = project_pt(uc_src, vc_src, h=0)
                    sx_pl, sy_pl, scale_p = project_pt(uc_src, vc_src, h=105)

                    if p_key:
                        # Floor shadow and planet sphere
                        sh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                        shdraw = ImageDraw.Draw(sh)
                        shdraw.ellipse([sx_fl - 100, sy_fl - 26, sx_fl + 100, sy_fl + 26], fill=(10, 5, 2, 175))
                        sh = sh.filter(ImageFilter.GaussianBlur(16))
                        canvas = Image.alpha_composite(canvas, sh)

                        p_sz = int(210 * scale_p)
                        p_sphere = cls.render_celestial_sphere(p_key, p_sz)
                        canvas.paste(p_sphere, (int(sx_pl - p_sphere.width // 2), int(sy_pl - p_sphere.height // 2)), p_sphere)

                    # Parabolic Aspect Ray from Source to Target
                    steps = 32
                    arc_pts = []
                    apex_h = 160.0
                    for s in range(steps):
                        t_val = s / float(steps - 1)
                        u_curr = uc_src + t_val * (uc_tgt - uc_src)
                        v_curr = vc_src + t_val * (vc_tgt - vc_src)
                        h_curr = (1.0 - t_val) * 105.0 + t_val * 0.0 + 4.0 * apex_h * t_val * (1.0 - t_val)
                        ax, ay, _ = project_pt(u_curr, v_curr, h=h_curr)
                        arc_pts.append((ax, ay))

                    for idx in range(len(arc_pts) - 1):
                        p_a, p_b = arc_pts[idx], arc_pts[idx + 1]
                        bdraw.line([p_a, p_b], fill=(255, 190, 30, 160), width=8)
                        bdraw.line([p_a, p_b], fill=(255, 250, 180, 250), width=3)

                    # Arrowhead
                    p_penultimate = arc_pts[-2]
                    angle = math.atan2(ty - p_penultimate[1], tx - p_penultimate[0])
                    tip_sz = 22
                    tip1 = (tx - tip_sz * math.cos(angle - math.pi / 6), ty - tip_sz * math.sin(angle - math.pi / 6))
                    tip2 = (tx - tip_sz * math.cos(angle + math.pi / 6), ty - tip_sz * math.sin(angle + math.pi / 6))
                    bdraw.polygon([(tx, ty), tip1, tip2], fill=(255, 245, 180, 255))

                    # Ray Tag Pill (Upright, NEVER mirrored!)
                    tag_text = plan.aspect_type or "ASPECT DRISHTI"
                    mid_pt = arc_pts[len(arc_pts) // 2]
                    tag_x, tag_y = mid_pt[0] + (35 if uc_tgt >= uc_src else -35), mid_pt[1] - 15
                    bbox_t = bdraw.textbbox((0, 0), tag_text, font=font_badge)
                    tw, th = bbox_t[2] - bbox_t[0], bbox_t[3] - bbox_t[1]
                    px, py = int(tag_x - tw // 2), int(tag_y - th // 2)
                    bdraw.rounded_rectangle([px - 12, py - 6, px + tw + 12, py + th + 6], radius=6, fill=(15, 10, 22, 235), outline=(255, 215, 0, 210), width=1)
                    bdraw.text((px, py), tag_text, fill=(255, 235, 140), font=font_badge)

                    tag_out = f"aspect_{src_h}_to_{tgt_h}"

                # Case 2: Target is known, planet is known, but source is UNKNOWN (e.g. Case F)
                # DO NOT INVENT A SOURCE HOUSE! Render planet in celestial space above chart.
                elif p_key is not None:
                    cx_cel, cy_cel = width // 2, 420
                    p_sz = 230
                    p_sphere = cls.render_celestial_sphere(p_key, p_sz)

                    # Planet celestial aura
                    p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    p_adraw = ImageDraw.Draw(p_aura)
                    p_adraw.ellipse([cx_cel - 160, cy_cel - 160, cx_cel + 160, cy_cel + 160], fill=(245, 180, 50, 130))
                    p_aura = p_aura.filter(ImageFilter.GaussianBlur(28))
                    canvas = Image.alpha_composite(canvas, p_aura)
                    canvas.paste(p_sphere, (cx_cel - p_sz // 2, cy_cel - p_sz // 2), p_sphere)

                    # Focused celestial ray descending from planet to target house
                    p_src_ray = (cx_cel, cy_cel + p_sz // 2 - 20)
                    bdraw.line([p_src_ray, (tx, ty)], fill=(255, 195, 45, 150), width=8)
                    bdraw.line([p_src_ray, (tx, ty)], fill=(255, 250, 180, 245), width=3)

                    # Arrowhead
                    angle = math.atan2(ty - p_src_ray[1], tx - p_src_ray[0])
                    tip_sz = 22
                    tip1 = (tx - tip_sz * math.cos(angle - math.pi / 6), ty - tip_sz * math.sin(angle - math.pi / 6))
                    tip2 = (tx - tip_sz * math.cos(angle + math.pi / 6), ty - tip_sz * math.sin(angle + math.pi / 6))
                    bdraw.polygon([(tx, ty), tip1, tip2], fill=(255, 245, 180, 255))

                    # Ray Tag Pill (Upright, NEVER mirrored!)
                    p_hi, p_en = PLANET_DISPLAY_NAMES.get(p_key, (p_key.upper(), p_key.upper()))
                    tag_text = f"{p_en} DRISHTI"
                    mid_x = (p_src_ray[0] + tx) // 2 + 40
                    mid_y = (p_src_ray[1] + ty) // 2
                    bbox_t = bdraw.textbbox((0, 0), tag_text, font=font_badge)
                    tw, th = bbox_t[2] - bbox_t[0], bbox_t[3] - bbox_t[1]
                    px, py = int(mid_x - tw // 2), int(mid_y - th // 2)
                    bdraw.rounded_rectangle([px - 12, py - 6, px + tw + 12, py + th + 6], radius=6, fill=(15, 10, 22, 235), outline=(255, 215, 0, 210), width=1)
                    bdraw.text((px, py), tag_text, fill=(255, 235, 140), font=font_badge)

                    tag_out = f"aspect_celestial_{p_key}_to_h{tgt_h}"

                # Case 3: Target is known, but NO planet is identified (e.g. Case H: "The 12th house receives an aspect")
                # DO NOT INVENT A PLANET! Pure celestial ray descending onto target house.
                else:
                    p_src_ray = (width // 2, 290)
                    bdraw.line([p_src_ray, (tx, ty)], fill=(255, 215, 60, 140), width=8)
                    bdraw.line([p_src_ray, (tx, ty)], fill=(255, 250, 190, 240), width=3)

                    # Arrowhead
                    angle = math.atan2(ty - p_src_ray[1], tx - p_src_ray[0])
                    tip_sz = 22
                    tip1 = (tx - tip_sz * math.cos(angle - math.pi / 6), ty - tip_sz * math.sin(angle - math.pi / 6))
                    tip2 = (tx - tip_sz * math.cos(angle + math.pi / 6), ty - tip_sz * math.sin(angle + math.pi / 6))
                    bdraw.polygon([(tx, ty), tip1, tip2], fill=(255, 245, 180, 255))

                    # Ray Tag Pill (Upright, NEVER mirrored!)
                    tag_text = "ASPECT RECEIVED"
                    mid_x = (p_src_ray[0] + tx) // 2 + 40
                    mid_y = (p_src_ray[1] + ty) // 2
                    bbox_t = bdraw.textbbox((0, 0), tag_text, font=font_badge)
                    tw, th = bbox_t[2] - bbox_t[0], bbox_t[3] - bbox_t[1]
                    px, py = int(mid_x - tw // 2), int(mid_y - th // 2)
                    bdraw.rounded_rectangle([px - 12, py - 6, px + tw + 12, py + th + 6], radius=6, fill=(15, 10, 22, 235), outline=(255, 215, 0, 210), width=1)
                    bdraw.text((px, py), tag_text, fill=(255, 235, 140), font=font_badge)

                    tag_out = f"aspect_received_h{tgt_h}"

                beam_blur = beam_layer.filter(ImageFilter.GaussianBlur(6))
                canvas = Image.alpha_composite(canvas, beam_blur)
                canvas = Image.alpha_composite(canvas, beam_layer)

                cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                return cls._save_scene_output(canvas, topic, scene_idx, tag_out, output_path)
            else:
                # Target house is UNKNOWN! (DO NOT INVENT HOUSE 1!)
                if p_key is not None:
                    return cls._render_aspect_cosmic_only(canvas, plan, topic, scene_idx, output_path, font_title, font_sub, font_header)
                else:
                    cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
                    return cls._save_scene_output(canvas, topic, scene_idx, "aspect_general", output_path)

        # -------------------------------------------------------------
        # MODE F: GENERAL / FALLBACK
        # -------------------------------------------------------------
        else:
            cls._draw_floating_badge(canvas, plan.badge_title, font_header, width, top_y=170)
            return cls._save_scene_output(canvas, topic, scene_idx, "general_chart", output_path)

    @classmethod
    def _get_planet_glow(cls, p_key: str) -> Tuple[int, int, int, int]:
        glows = {
            "sun": (255, 195, 45, 140),
            "moon": (230, 240, 255, 140),
            "mars": (255, 60, 25, 140),
            "mercury": (60, 230, 140, 140),
            "jupiter": (255, 215, 60, 140),
            "venus": (255, 240, 220, 140),
            "saturn": (140, 170, 255, 140),
            "rahu": (160, 90, 240, 140),
            "ketu": (240, 130, 70, 140),
        }
        return glows.get(p_key, (255, 215, 100, 140))

    @classmethod
    def _render_planet_only_scene(
        cls,
        canvas: Image.Image,
        plan: AstrologyScenePlan,
        topic: str,
        scene_idx: int,
        output_path: Optional[Path],
        font_title: Any,
        font_sub: Any,
        font_header: Any,
    ) -> Path:
        width, height = canvas.size
        planet_key = plan.planets[0] if plan.planets else "jupiter"
        p_hi, p_en = PLANET_DISPLAY_NAMES.get(planet_key, (planet_key.upper(), planet_key.upper()))

        c_space = Image.new("RGBA", (width, height), (6, 4, 14, 255))
        nebula = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ndraw = ImageDraw.Draw(nebula)
        glow_col = cls._get_planet_glow(planet_key)
        ndraw.ellipse([width // 2 - 420, 850 - 420, width // 2 + 420, 850 + 420], fill=glow_col)
        nebula = nebula.filter(ImageFilter.GaussianBlur(110))
        c_space = Image.alpha_composite(c_space, nebula)

        sphere_sz = 520
        p_sphere = cls.render_celestial_sphere(planet_key, sphere_sz)

        p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        p_adraw = ImageDraw.Draw(p_aura)
        p_adraw.ellipse([width // 2 - 320, 850 - 320, width // 2 + 320, 850 + 320], fill=glow_col)
        if planet_key == "sun":
            for ang in range(0, 360, 8):
                rad = math.radians(ang)
                fl_len = 310 + (ang % 24) * 5
                p_adraw.line([(width // 2, 850), (width // 2 + math.cos(rad) * fl_len, 850 + math.sin(rad) * fl_len)], fill=(255, 225, 90, 180), width=4)
        p_aura = p_aura.filter(ImageFilter.GaussianBlur(34))
        c_space = Image.alpha_composite(c_space, p_aura)

        px0 = width // 2 - p_sphere.width // 2
        py0 = 850 - p_sphere.height // 2
        c_space.paste(p_sphere, (px0, py0), p_sphere)

        cls._draw_floating_badge(c_space, plan.badge_title, font_header, width, top_y=170)
        cls._draw_bottom_celestial_card(
            c_space,
            title=f"{p_hi} ({p_en}) • COSMIC RULERSHIP",
            subtitle=plan.subtitle,
            width=width,
            bottom_y=1420,
            font_title=font_title,
            font_sub=font_sub,
        )
        return cls._save_scene_output(c_space, topic, scene_idx, f"planet_{planet_key}", output_path)

    @classmethod
    def _render_celestial_conjunction(
        cls,
        canvas: Image.Image,
        plan: AstrologyScenePlan,
        topic: str,
        scene_idx: int,
        output_path: Optional[Path],
        font_title: Any,
        font_sub: Any,
        font_header: Any,
    ) -> Path:
        width, height = canvas.size
        planets = plan.planets
        n_p = len(planets)

        c_space = Image.new("RGBA", (width, height), (6, 4, 14, 255))
        nebula = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ndraw = ImageDraw.Draw(nebula)
        ndraw.ellipse([width // 2 - 450, 850 - 450, width // 2 + 450, 850 + 450], fill=(230, 180, 50, 90))
        nebula = nebula.filter(ImageFilter.GaussianBlur(120))
        c_space = Image.alpha_composite(c_space, nebula)

        if n_p == 1:
            centers = [(width // 2, 850)]
            p_sz = 340
        elif n_p == 2:
            centers = [(width // 2 - 210, 850), (width // 2 + 210, 850)]
            p_sz = 280
        elif n_p == 3:
            centers = [(width // 2 - 270, 850), (width // 2, 850), (width // 2 + 270, 850)]
            p_sz = 240
        elif n_p == 4:
            centers = [
                (width // 2 - 280, 850),
                (width // 2 - 90, 850),
                (width // 2 + 90, 850),
                (width // 2 + 280, 850),
            ]
            p_sz = 195
        else:
            centers = []
            spacing = min(200, (width - 160) // n_p)
            start_x = width // 2 - (n_p - 1) * spacing // 2
            for i in range(n_p):
                centers.append((start_x + i * spacing, 850))
            p_sz = max(130, spacing - 25)

        planet_positions = []
        for idx, p_key in enumerate(planets):
            cx, cy = centers[idx]
            planet_positions.append((cx, cy))
            p_sphere = cls.render_celestial_sphere(p_key, p_sz)
            p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            p_adraw = ImageDraw.Draw(p_aura)
            glow_col = cls._get_planet_glow(p_key)
            p_adraw.ellipse([cx - p_sz // 2 - 25, cy - p_sz // 2 - 25, cx + p_sz // 2 + 25, cy + p_sz // 2 + 25], fill=glow_col)
            p_aura = p_aura.filter(ImageFilter.GaussianBlur(24))
            c_space = Image.alpha_composite(c_space, p_aura)
            c_space.paste(p_sphere, (cx - p_sz // 2, cy - p_sz // 2), p_sphere)

        # Golden linking energy arcs
        if len(planet_positions) >= 2:
            arc_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            adraw = ImageDraw.Draw(arc_layer)
            for i in range(len(planet_positions) - 1):
                adraw.line([planet_positions[i], planet_positions[i + 1]], fill=(255, 235, 140, 220), width=4)
            if len(planet_positions) >= 3:
                adraw.line([planet_positions[-1], planet_positions[0]], fill=(255, 235, 140, 160), width=2)
            arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(4))
            c_space = Image.alpha_composite(c_space, arc_layer)

        cls._draw_floating_badge(c_space, plan.badge_title, font_header, width, top_y=170)
        cls._draw_bottom_celestial_card(
            c_space,
            title="CONJOINED CELESTIAL ALIGNMENT",
            subtitle=plan.subtitle,
            width=width,
            bottom_y=1420,
            font_title=font_title,
            font_sub=font_sub,
        )
        return cls._save_scene_output(c_space, topic, scene_idx, "celestial_conjunction", output_path)

    @classmethod
    def _render_aspect_cosmic_only(
        cls,
        canvas: Image.Image,
        plan: AstrologyScenePlan,
        topic: str,
        scene_idx: int,
        output_path: Optional[Path],
        font_title: Any,
        font_sub: Any,
        font_header: Any,
    ) -> Path:
        width, height = canvas.size
        p_key = plan.planets[0] if plan.planets else "saturn"
        p_hi, p_en = PLANET_DISPLAY_NAMES.get(p_key, (p_key.upper(), p_key.upper()))

        c_space = Image.new("RGBA", (width, height), (6, 4, 14, 255))
        nebula = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ndraw = ImageDraw.Draw(nebula)
        glow_col = cls._get_planet_glow(p_key)
        ndraw.ellipse([width // 2 - 420, 750 - 420, width // 2 + 420, 750 + 420], fill=glow_col)
        nebula = nebula.filter(ImageFilter.GaussianBlur(110))
        c_space = Image.alpha_composite(c_space, nebula)

        cx, cy = width // 2, 600
        p_sz = 340
        p_sphere = cls.render_celestial_sphere(p_key, p_sz)
        p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        p_adraw = ImageDraw.Draw(p_aura)
        p_adraw.ellipse([cx - p_sz // 2 - 30, cy - p_sz // 2 - 30, cx + p_sz // 2 + 30, cy + p_sz // 2 + 30], fill=glow_col)
        p_aura = p_aura.filter(ImageFilter.GaussianBlur(28))
        c_space = Image.alpha_composite(c_space, p_aura)
        c_space.paste(p_sphere, (cx - p_sz // 2, cy - p_sz // 2), p_sphere)

        # Cosmic aspect rays radiating outward into the cosmos
        ray_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        rdraw = ImageDraw.Draw(ray_layer)
        for target_angle in [45, 90, 135]:
            rad = math.radians(target_angle)
            ray_len = 540
            end_x = int(cx + math.cos(rad) * ray_len)
            end_y = int(cy + math.sin(rad) * ray_len)
            rdraw.line([(cx, cy + p_sz // 4), (end_x, end_y)], fill=(255, 215, 60, 140), width=6)
            rdraw.line([(cx, cy + p_sz // 4), (end_x, end_y)], fill=(255, 250, 180, 240), width=2)
        ray_layer = ray_layer.filter(ImageFilter.GaussianBlur(3))
        c_space = Image.alpha_composite(c_space, ray_layer)

        cls._draw_floating_badge(c_space, plan.badge_title, font_header, width, top_y=170)
        cls._draw_bottom_celestial_card(
            c_space,
            title=f"{p_en} DRISHTI • COSMIC GAZE",
            subtitle=plan.subtitle,
            width=width,
            bottom_y=1420,
            font_title=font_title,
            font_sub=font_sub,
        )
        return cls._save_scene_output(c_space, topic, scene_idx, f"aspect_cosmic_{p_key}", output_path)

    @classmethod
    def _draw_floating_badge(cls, canvas: Image.Image, text: str, font: Any, width: int, top_y: int = 170) -> None:
        """Draws a floating 3D badge pill with gold border and dark obsidian backing."""
        badge = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(badge)
        bbox = bdraw.textbbox((0, 0), text, font=font)
        hw = bbox[2] - bbox[0]
        card_w = max(460, hw + 60)
        cx_card = (width - card_w) // 2
        bdraw.rounded_rectangle(
            [cx_card, top_y, cx_card + card_w, top_y + 58],
            radius=14,
            fill=(14, 10, 22, 235),
            outline=(255, 215, 60, 220),
            width=2,
        )
        bdraw.text((cx_card + (card_w - hw) // 2, top_y + 13), text, fill=(255, 235, 140), font=font)
        canvas.paste(Image.alpha_composite(canvas, badge))

    @classmethod
    def _draw_bottom_celestial_card(
        cls,
        canvas: Image.Image,
        title: str,
        subtitle: str,
        width: int,
        bottom_y: int,
        font_title: Any,
        font_sub: Any,
    ) -> None:
        """Renders an elegant bottom metadata card for deep space celestial visual modes."""
        card = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(card)
        card_w = 900
        x0 = (width - card_w) // 2
        y0 = bottom_y
        cdraw.rounded_rectangle(
            [x0, y0, x0 + card_w, y0 + 130],
            radius=20,
            fill=(20, 14, 28, 235),
            outline=(255, 205, 55, 210),
            width=2,
        )
        cdraw.text((x0 + 40, y0 + 22), title.upper(), fill=(255, 225, 70, 255), font=font_title)
        cdraw.text((x0 + 40, y0 + 74), subtitle, fill=(235, 225, 210, 240), font=font_sub)
        canvas.paste(Image.alpha_composite(canvas, card))

    @classmethod
    def _save_scene_output(
        cls,
        canvas: Image.Image,
        topic: str,
        scene_idx: int,
        tag: str,
        output_path: Optional[Path],
    ) -> Path:
        """Saves canvas to high-quality JPEG and returns Path."""
        if output_path is None:
            slug = re.sub(r"[^\w]", "_", topic.lower())[:15].strip("_") or "kundli_3d"
            uid = hashlib.md5(f"{slug}_{scene_idx}_{tag}_{time.time_ns()}".encode()).hexdigest()[:8]
            output_path = GENERATED_BROLL_DIR / f"{slug}_sc{scene_idx + 1}_{tag}_{uid}.jpg"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(str(output_path), "JPEG", quality=95)
        logger.info(f"[KundliChartGenerator] Saved 3D scene visual: {output_path.name}")
        return output_path
