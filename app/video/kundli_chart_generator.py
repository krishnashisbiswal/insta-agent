"""
Dynamic Vedic Kundli Chart Visual Generator.
Generates authentic, high-resolution 1080x1920 (9:16 vertical) North Indian
astrological Kundli birth charts with dynamic house highlighting and planet markers:

1. Dynamic House Highlighting: Illuminates any specified house (1 to 12) with
   radiant golden/amber light, Devanagari Sanskrit numerals, and signification banners.
2. Natural Language Script Extraction: Extracts house numbers and planetary placements
   from Hindi, English, and Hinglish narrations (including oblique cases like 'दूसरे', 'आठवें').
3. Viral Production Quality: Renders onto deep cosmic obsidian backgrounds with
   sacred geometry grids, outer atmospheric glows, and high-conversion callout cards.
"""

from __future__ import annotations

import hashlib
import cv2
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
        "significance": "Self, Physical Body, Vitality & Life Direction",
        "type": "Kendra & Trikona (Most Auspicious)",
    },
    2: {
        "name_hi": "द्वितीय भाव (धन)",
        "name_en": "2nd House (Dhana)",
        "sanskrit": "धन भाव",
        "significance": "Accumulated Wealth, Speech, Assets & Family Lineage",
        "type": "Maraka & Panapara",
    },
    3: {
        "name_hi": "तृतीय भाव (सहज)",
        "name_en": "3rd House (Sahaja)",
        "sanskrit": "पराक्रम भाव",
        "significance": "Courage, Willpower, Self-Effort & Communication",
        "type": "Upachaya",
    },
    4: {
        "name_hi": "चतुर्थ भाव (सुख)",
        "name_en": "4th House (Sukha)",
        "sanskrit": "मातृ भाव",
        "significance": "Inner Peace, Mother, Real Estate, Vehicles & Mind",
        "type": "Kendra",
    },
    5: {
        "name_hi": "पंचम भाव (पुत्र)",
        "name_en": "5th House (Putra)",
        "sanskrit": "बुद्धि भाव",
        "significance": "Intellect, Past-Life Karma (Purva Punya), Speculation",
        "type": "Trikona (Auspicious Dharma)",
    },
    6: {
        "name_hi": "षष्ठ भाव (रिपु)",
        "name_en": "6th House (Ripu)",
        "sanskrit": "शत्रु/ऋण भाव",
        "significance": "Debts, Enemies, Daily Struggles, Disease & Overcoming",
        "type": "Dusthana & Upachaya",
    },
    7: {
        "name_hi": "सप्तम भाव (जाया)",
        "name_en": "7th House (Kalatra)",
        "sanskrit": "कलत्र भाव",
        "significance": "Marriage, Long-Term Partnerships & Public Relations",
        "type": "Kendra & Maraka",
    },
    8: {
        "name_hi": "अष्टम भाव (आयु)",
        "name_en": "8th House (Ayu/Randhra)",
        "sanskrit": "रंध्र भाव",
        "significance": "Sudden Shifts, Occult, Longevity, Hidden Wealth & Rahu Depth",
        "type": "Major Dusthana (Transformation)",
    },
    9: {
        "name_hi": "नवम भाव (धर्म)",
        "name_en": "9th House (Bhagya)",
        "sanskrit": "भाग्य भाव",
        "significance": "Higher Fortune, Dharma, Guru's Grace & Pilgrimage",
        "type": "Supreme Trikona (Luck)",
    },
    10: {
        "name_hi": "दशम भाव (कर्म)",
        "name_en": "10th House (Karma)",
        "sanskrit": "राज्य भाव",
        "significance": "Career, Power, Authority, Public Status & Leadership",
        "type": "Supreme Kendra",
    },
    11: {
        "name_hi": "एकादश भाव (लाभ)",
        "name_en": "11th House (Labha)",
        "sanskrit": "आय भाव",
        "significance": "Massive Gains, Network Circles & Fulfillment of Desires",
        "type": "Upachaya (Growth)",
    },
    12: {
        "name_hi": "द्वादश भाव (व्यय)",
        "name_en": "12th House (Vyaya)",
        "sanskrit": "मोक्ष भाव",
        "significance": "Subconscious Mind, Foreign Travel, Isolation & Spiritual Liberation",
        "type": "Dusthana & Moksha",
    },
}

DEVANAGARI_NUMERALS: Dict[int, str] = {
    1: "१", 2: "२", 3: "३", 4: "४", 5: "५", 6: "६",
    7: "७", 8: "८", 9: "९", 10: "१०", 11: "११", 12: "१२"
}

PLANET_PATTERNS: Dict[str, Tuple[str, str]] = {
    "rahu": ("राहु", "RAHU"),
    "ketu": ("केतु", "KETU"),
    "shani": ("शनि", "SATURN"),
    "saturn": ("शनि", "SATURN"),
    "guru": ("गुरु", "JUPITER"),
    "jupiter": ("गुरु", "JUPITER"),
    "brihaspati": ("बृहस्पति", "JUPITER"),
    "mangal": ("मंगल", "MARS"),
    "mars": ("मंगल", "MARS"),
    "surya": ("सूर्य", "SUN"),
    "sun": ("सूर्य", "SUN"),
    "chandra": ("चंद्र", "MOON"),
    "moon": ("चंद्र", "MOON"),
    "shukra": ("शुक्र", "VENUS"),
    "venus": ("शुक्र", "VENUS"),
    "budh": ("बुध", "MERCURY"),
    "budha": ("बुध", "MERCURY"),
    "mercury": ("बुध", "MERCURY"),
}


class KundliChartGenerator:
    """
    Renders 1080x1920 dynamic Vedic astrology charts tailored to script context.
    """

    @classmethod
    def extract_house_and_planet(cls, text: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Extracts house number (1-12) and planetary entity from Hindi/English narration.
        Handles direct numbers, ordinals, and oblique Hindi inflections ('आठवें', 'दूसरे', etc.).
        """
        if not text:
            return None, None
        t = text.lower()

        # 1. Direct regex for numbers
        m_num = re.search(r"\b([1-9]|1[0-2])(?:st|nd|rd|th)?\s*(?:house|bhav|bhava|ghar|भाव|घर)\b", t)
        detected_house: Optional[int] = int(m_num.group(1)) if m_num else None

        if not detected_house:
            m_rev = re.search(r"\b(?:house|bhav|bhava|घर|भाव)\s*([1-9]|1[0-2])\b", t)
            if m_rev:
                detected_house = int(m_rev.group(1))

        # 2. Hindi & English Word Aliases (Must strictly refer to astrological houses, not generic numbers/signs)
        if not detected_house:
            alias_map: Dict[int, List[str]] = {
                1: ["प्रथम भाव", "पहला भाव", "पहले भाव", "पहला घर", "पहले घर", "लग्न भाव", "तनु भाव", "1st house", "first house"],
                2: ["द्वितीय भाव", "दूसरा भाव", "दूसरे भाव", "दूसरा घर", "दूसरे घर", "धन भाव", "2nd house", "second house"],
                3: ["तृतीय भाव", "तीसरा भाव", "तीसरे भाव", "तीसरा घर", "तीसरे घर", "सहज भाव", "पराक्रम भाव", "3rd house", "third house"],
                4: ["चतुर्थ भाव", "चौथा भाव", "चौथे भाव", "चौथा घर", "चौथे घर", "सुख भाव", "मातृ भाव", "4th house", "fourth house"],
                5: ["पंचम भाव", "पांचवा भाव", "पांचवां भाव", "पांचवे भाव", "पांचवें भाव", "पांचवा घर", "पुत्र भाव", "बुद्धि भाव", "5th house", "fifth house"],
                6: ["षष्ठ भाव", "छठा भाव", "छठे भाव", "छठा घर", "छठे घर", "शत्रु भाव", "ऋण भाव", "रोग भाव", "6th house", "sixth house"],
                7: ["सप्तम भाव", "सातवां भाव", "सातवा भाव", "सातवे भाव", "सातवें भाव", "सातवां घर", "कलत्र भाव", "जाया भाव", "7th house", "seventh house"],
                8: ["अष्टम भाव", "आठवां भाव", "आठवा भाव", "आठवे भाव", "आठवें भाव", "आठवां घर", "रंध्र भाव", "आयु भाव", "8th house", "eighth house"],
                9: ["नवम भाव", "नौवां भाव", "नौवा भाव", "नौवे भाव", "नौवें भाव", "नौवां घर", "भाग्य भाव", "धर्म भाव", "9th house", "ninth house"],
                10: ["दशम भाव", "दसवां भाव", "दसवा भाव", "दसवे भाव", "दसवें भाव", "दसवां घर", "कर्म भाव", "राज्य भाव", "10th house", "tenth house"],
                11: ["एकादश भाव", "ग्यारहवां भाव", "ग्यारहवा भाव", "ग्यारहवे भाव", "ग्यारहवें भाव", "ग्यारहवां घर", "लाभ भाव", "आय भाव", "11th house", "eleventh house"],
                12: ["द्वादश भाव", "बारहवां भाव", "बारहवा भाव", "बारहवे भाव", "बारहवें भाव", "बारहवां घर", "व्यय भाव", "मोक्ष भाव", "12th house", "twelfth house"],
            }
            for h_idx, aliases in alias_map.items():
                if any(re.search(r"\b" + re.escape(alias) + r"\b", t) or alias in t for alias in aliases):
                    detected_house = h_idx
                    break

        # 3. Detect Planet
        detected_planet: Optional[str] = None
        for p_key, (p_hi, p_en) in PLANET_PATTERNS.items():
            if re.search(r"\b" + re.escape(p_key) + r"\b", t) or p_hi in t or p_en.lower() in t:
                detected_planet = f"{p_hi} ({p_en})"
                break

        return detected_house, detected_planet

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
        Returns the absolute Path of the saved image.
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
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_title = ImageFont.load_default()
            font_badge = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        # 1. Base dark cosmic canvas
        canvas = Image.new("RGBA", (width, height), (8, 6, 16, 255))
        draw = ImageDraw.Draw(canvas)

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

            # Draw numeral
            draw.text((cx - 12, cy - 20), num_str, fill=num_color, font=font_large)

            if is_hl:
                # Glowing targeted reticle
                draw.ellipse([cx - 42, cy - 42, cx + 42, cy + 42], outline=(255, 235, 120, 240), width=3)
                meta = HOUSE_METADATA.get(h_num, {})
                tag_name = meta.get("sanskrit") or f"HOUSE {h_num}"
                draw.text((cx - 40, cy + 30), tag_name, fill=(255, 255, 200, 240), font=font_small)

                if planet_name:
                    draw.text((cx - 30, cy - 56), f"[{planet_name}]", fill=(255, 220, 0, 255), font=font_badge)

        # 7. Top High-Conversion Header
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
        # Center header text
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

    @classmethod
    def generate_3d_kundli_planet_scene(
        cls,
        scene_dict: Dict[str, Any],
        topic: str = "",
        scene_idx: int = 0,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Renders a viral, high-resolution 1080x1920 3D Planet in Vedic Kundli scene.
        Highlights the specific house in radiant golden amber and composites authentic
        3D celestial planet spheres directly into that astrological context.
        """
        from config.settings import BASE_DIR
        broll_dir = BASE_DIR / "assets" / "cinematic_broll"

        spoken = str(scene_dict.get("spoken_line", "")).lower()
        on_screen = str(scene_dict.get("on_screen_text", "")).lower()
        vis_desc = str(scene_dict.get("visual_description", "")).lower()
        ctx = f"{topic} {spoken} {on_screen} {vis_desc}".lower()

        # Detect specific scene archetype
        is_sun_rahu = any(k in ctx for k in ["rahu", "राहु"]) and any(k in ctx for k in ["sun", "surya", "सूर्य", "eclipse", "ग्रहण"]) or "sun rahu" in ctx
        is_12th = any(k in ctx for k in ["12th", "बारहवें", "बारहवां", "twelfth", "vyaya", "व्यय", "drain"])
        is_mars = any(k in ctx for k in ["mars", "mangal", "मंगल"])
        is_saturn = any(k in ctx for k in ["saturn", "shani", "शनि", "drishti", "दृष्टि", "aspect"])

        # Determine target house
        if is_sun_rahu:
            target_house = 1
        elif is_12th:
            target_house = 12
        elif is_mars:
            target_house = 1
        elif is_saturn:
            target_house = 7
        else:
            extracted_h, _ = cls.extract_house_and_planet(ctx)
            target_house = extracted_h or 1

        width, height = 1080, 1920
        box_size = 780
        x0 = (width - box_size) // 2
        x1 = x0 + box_size
        center_y = 860
        y0 = center_y - (box_size // 2)
        y1 = y0 + box_size
        x_mid = (x0 + x1) / 2.0
        y_mid = (y0 + y1) / 2.0

        p_tl = ((x0 + x_mid) / 2.0, (y0 + y_mid) / 2.0)
        p_tr = ((x1 + x_mid) / 2.0, (y0 + y_mid) / 2.0)
        p_bl = ((x0 + x_mid) / 2.0, (y1 + y_mid) / 2.0)
        p_br = ((x1 + x_mid) / 2.0, (y1 + y_mid) / 2.0)

        polygons: Dict[int, List[Tuple[float, float]]] = {
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

        ROMAN_NUMS = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"}

        # 1. Base Environment: Luxurious Cosmic Obsidian with Celestial Zodiac Ring
        canvas = Image.new("RGBA", (width, height), (8, 7, 15, 255))
        nebula = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ndraw = ImageDraw.Draw(nebula)
        ndraw.ellipse([width // 2 - 400, center_y - 450, width // 2 + 400, center_y + 450], fill=(45, 18, 68, 170))
        ndraw.ellipse([width // 2 - 280, center_y - 320, width // 2 + 280, center_y + 320], fill=(80, 48, 20, 150))
        nebula = nebula.filter(ImageFilter.GaussianBlur(120))
        canvas = Image.alpha_composite(canvas, nebula)

        # Outer celestial ring (sacred zodiac wheel)
        wheel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        wdraw = ImageDraw.Draw(wheel)
        rad_out = box_size // 2 + 55
        wdraw.ellipse([x_mid - rad_out, y_mid - rad_out, x_mid + rad_out, y_mid + rad_out], outline=(255, 215, 70, 75), width=2)
        rad_in = rad_out - 16
        wdraw.ellipse([x_mid - rad_in, y_mid - rad_in, x_mid + rad_in, y_mid + rad_in], outline=(255, 215, 70, 45), width=1)
        for ang in range(0, 360, 30):
            ar = math.radians(ang)
            x_o = x_mid + math.cos(ar) * rad_out
            y_o = y_mid + math.sin(ar) * rad_out
            x_i = x_mid + math.cos(ar) * rad_in
            y_i = y_mid + math.sin(ar) * rad_in
            wdraw.line([(x_i, y_i), (x_o, y_o)], fill=(255, 220, 80, 110), width=2)
        canvas = Image.alpha_composite(canvas, wheel)

        # Cosmic stardust
        np.random.seed(108 + scene_idx)
        sdraw = ImageDraw.Draw(canvas)
        for _ in range(450):
            sx = np.random.randint(15, width - 15)
            sy = np.random.randint(30, height - 30)
            bright = np.random.randint(120, 255)
            sz = 1 if np.random.random() > 0.08 else 2
            sdraw.rectangle([sx, sy, sx + sz, sy + sz], fill=(bright, bright, min(255, bright + 35), 210))

        # 2. House Golden Illumination (Volumetric screen bloom)
        glow_color = (255, 205, 45)
        if is_mars:
            glow_color = (255, 85, 25)
        elif is_12th:
            glow_color = (255, 215, 50)

        poly = polygons.get(target_house, polygons[1])
        cx, cy = cls.get_centroid(poly)

        bloom = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(bloom)
        bdraw.ellipse([cx - 240, cy - 240, cx + 240, cy + 240], fill=(glow_color[0], glow_color[1], glow_color[2], 80))
        bdraw.polygon(poly, fill=(glow_color[0], glow_color[1], glow_color[2], 150))
        bdraw.line(poly + [poly[0]], fill=(255, 245, 180, 245), width=6)
        bloom = bloom.filter(ImageFilter.GaussianBlur(30))
        canvas = Image.alpha_composite(canvas, bloom)

        inner = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        idraw = ImageDraw.Draw(inner)
        idraw.polygon(poly, fill=(glow_color[0], glow_color[1], glow_color[2], 65))
        canvas = Image.alpha_composite(canvas, inner)

        # 3. Dynamic 3D Celestial Objects & Phenomenon in Context
        header_text = ""
        if is_sun_rahu:
            header_text = "1ST HOUSE • SUN & RAHU ECLIPSE"
            rahu_p = broll_dir / "planet_rahu.jpg"
            if rahu_p.exists():
                rahu_img = Image.open(rahu_p).convert("RGB")
                rw, rh = rahu_img.size
                disc_sz = int(rw * 0.72)
                crop_x0 = int(rw * 0.5 - disc_sz // 2)
                crop_y0 = int(rh * 0.48 - disc_sz // 2)
                eclipse_crop = rahu_img.crop((crop_x0, crop_y0, crop_x0 + disc_sz, crop_y0 + disc_sz))

                target_sz = 280
                eclipse_resized = eclipse_crop.resize((target_sz, target_sz), Image.Resampling.LANCZOS)
                y_g, x_g = np.ogrid[:target_sz, :target_sz]
                r_g = target_sz / 2.0
                d2 = ((x_g - r_g) / r_g) ** 2 + ((y_g - r_g) / r_g) ** 2
                m = np.clip((1.0 - d2) * 6.0, 0.0, 1.0)
                m_arr = (m * 255).astype(np.uint8)
                eclipse_rgba = eclipse_resized.convert("RGBA")
                eclipse_rgba.putalpha(Image.fromarray(m_arr))

                solar_glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                sgdraw = ImageDraw.Draw(solar_glow)
                sgdraw.ellipse([cx - 180, cy - 180, cx + 180, cy + 180], fill=(255, 200, 40, 130))
                for ang in range(0, 360, 12):
                    rad = math.radians(ang)
                    rlen = 185 + (ang % 30) * 4
                    sgdraw.line([(cx, cy), (cx + math.cos(rad) * rlen, cy + math.sin(rad) * rlen)], fill=(255, 230, 80, 160), width=3)
                solar_glow = solar_glow.filter(ImageFilter.GaussianBlur(16))
                canvas = Image.alpha_composite(canvas, solar_glow)
                canvas.paste(eclipse_rgba, (int(cx - target_sz // 2), int(cy - target_sz // 2)), eclipse_rgba)

        elif is_12th:
            header_text = "12TH HOUSE • VITAL ENERGY DRAIN"
            vortex = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vortex)
            for ang in range(-65, 105, 2):
                rad = math.radians(ang)
                for length, alpha, wid in [(390, 190, 4), (290, 220, 3), (190, 255, 2)]:
                    ex = cx + math.cos(rad) * length
                    ey = cy - math.sin(rad) * length
                    vdraw.line([(cx, cy), (ex, ey)], fill=(255, 215, 60, alpha), width=wid)
            for p_r, p_a, p_sz in [
                (65, 15, 6), (135, 35, 8), (205, -5, 6), (275, 50, 9), (105, -25, 5),
                (175, 20, 8), (335, 10, 7), (155, 65, 8), (235, 35, 9), (295, 75, 7),
                (85, 45, 5), (195, -15, 7), (260, 25, 8), (350, 60, 6)
            ]:
                pr = math.radians(p_a)
                px = cx + math.cos(pr) * p_r
                py = cy - math.sin(pr) * p_r
                vdraw.ellipse([px - p_sz, py - p_sz, px + p_sz, py + p_sz], fill=(255, 245, 140, 250))
            v_blur = vortex.filter(ImageFilter.GaussianBlur(6))
            canvas = Image.alpha_composite(canvas, v_blur)
            canvas = Image.alpha_composite(canvas, vortex)

        elif is_mars:
            header_text = "1ST HOUSE • MARS FIERCE ENERGY"
            mars_p = broll_dir / "planet_mars.jpg"
            if mars_p.exists():
                mars_img = Image.open(mars_p).convert("RGB")
                mw, mh = mars_img.size
                mars_crop = mars_img.crop((0, int(mh * 0.16), mw, int(mh * 0.76)))
                mars_target_sz = 280
                mars_resized = mars_crop.resize((mars_target_sz, mars_target_sz), Image.Resampling.LANCZOS)
                y_m, x_m = np.ogrid[:mars_target_sz, :mars_target_sz]
                r_m = mars_target_sz / 2.0
                d2_m = ((x_m - r_m) / r_m) ** 2 + ((y_m - r_m) / r_m) ** 2
                m_m = np.clip((1.0 - d2_m) * 6.0, 0.0, 1.0)
                m_arr_m = (m_m * 255).astype(np.uint8)
                mars_rgba = mars_resized.convert("RGBA")
                mars_rgba.putalpha(Image.fromarray(m_arr_m))

                m_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                mdraw = ImageDraw.Draw(m_aura)
                mdraw.ellipse([cx - 170, cy - 170, cx + 170, cy + 170], fill=(255, 65, 20, 160))
                mdraw.ellipse([cx - 200, cy - 200, cx + 200, cy + 200], fill=(255, 120, 30, 90))
                m_aura = m_aura.filter(ImageFilter.GaussianBlur(26))
                canvas = Image.alpha_composite(canvas, m_aura)
                canvas.paste(mars_rgba, (int(cx - mars_target_sz // 2), int(cy - mars_target_sz // 2)), mars_rgba)

        elif is_saturn:
            header_text = "7TH HOUSE • SHANI KARMIC DRISHTI"
            cx7, cy7 = cls.get_centroid(polygons[7])
            cx9, cy9 = cls.get_centroid(polygons[9])
            cx1, cy1 = cls.get_centroid(polygons[1])
            cx4_h, cy4_h = cls.get_centroid(polygons[4])

            sat_p = Path("output/saturn_3d_feathered.png")
            if not sat_p.exists():
                sat_p = broll_dir / "planet_saturn.jpg"
            if sat_p.exists():
                sat_raw = Image.open(sat_p)
                sat_w = 350
                sat_h = int(sat_w * sat_raw.height / sat_raw.width)
                sat_resized = sat_raw.resize((sat_w, sat_h), Image.Resampling.LANCZOS)
                if sat_resized.mode != "RGBA":
                    sat_resized = sat_resized.convert("RGBA")

                shalo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                sdraw = ImageDraw.Draw(shalo)
                sdraw.ellipse([cx7 - 160, cy7 - 120, cx7 + 160, cy7 + 120], fill=(255, 195, 35, 140))
                shalo = shalo.filter(ImageFilter.GaussianBlur(24))
                canvas = Image.alpha_composite(canvas, shalo)
                canvas.paste(sat_resized, (int(cx7 - sat_w // 2), int(cy7 - sat_h // 2)), sat_resized)

            beam_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            bdraw = ImageDraw.Draw(beam_layer)

            def _draw_aspect_beam(start: Tuple[float, float], end: Tuple[float, float], tag: str) -> None:
                bdraw.line([start, end], fill=(255, 190, 30, 160), width=9)
                bdraw.line([start, end], fill=(255, 250, 190, 255), width=3)
                tx, ty = end
                bdraw.ellipse([tx - 40, ty - 22, tx + 40, ty + 22], fill=(255, 215, 60, 130), outline=(255, 245, 140, 240), width=2)
                angle = math.atan2(end[1] - start[1], end[0] - start[0])
                tip_sz = 26
                tip1 = (end[0] - tip_sz * math.cos(angle - math.pi / 6), end[1] - tip_sz * math.sin(angle - math.pi / 6))
                tip2 = (end[0] - tip_sz * math.cos(angle + math.pi / 6), end[1] - tip_sz * math.sin(angle + math.pi / 6))
                bdraw.polygon([end, tip1, tip2], fill=(255, 245, 180, 255))
                mx = (start[0] + end[0]) / 2.0
                my = (start[1] + end[1]) / 2.0
                try:
                    font_b = ImageFont.truetype("arial.ttf", 20)
                except Exception:
                    font_b = ImageFont.load_default()
                bbox = bdraw.textbbox((0, 0), tag, font=font_b)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                px, py = int(mx - tw // 2), int(my - th // 2)
                bdraw.rounded_rectangle([px - 10, py - 4, px + tw + 10, py + th + 4], radius=6, fill=(15, 10, 22, 230), outline=(255, 215, 0, 200), width=1)
                bdraw.text((px, py), tag, fill=(255, 235, 140), font=font_b)

            _draw_aspect_beam((cx7 + 60, cy7 - 30), (cx9 - 30, cy9 + 25), "3RD DRISHTI")
            _draw_aspect_beam((cx7, cy7 - 75), (cx1, cy1 + 75), "7TH DRISHTI")
            _draw_aspect_beam((cx7 - 60, cy7 - 30), (cx4_h + 30, cy4_h + 25), "10TH DRISHTI")

            b_blur = beam_layer.filter(ImageFilter.GaussianBlur(6))
            canvas = Image.alpha_composite(canvas, b_blur)
            canvas = Image.alpha_composite(canvas, beam_layer)

        else:
            # General Planetary & Astrological Placement
            planet_file_map = {
                "jupiter": ("planet_jupiter.jpg", (255, 215, 60), "GURU JUPITER"),
                "guru": ("planet_jupiter.jpg", (255, 215, 60), "GURU JUPITER"),
                "sun": ("planet_sun.jpg", (255, 200, 40), "SURYA SUN"),
                "surya": ("planet_sun.jpg", (255, 200, 40), "SURYA SUN"),
                "moon": ("planet_moon.jpg", (210, 230, 255), "CHANDRA MOON"),
                "chandra": ("planet_moon.jpg", (210, 230, 255), "CHANDRA MOON"),
                "mercury": ("planet_mercury.jpg", (100, 240, 160), "BUDHA MERCURY"),
                "budha": ("planet_mercury.jpg", (100, 240, 160), "BUDHA MERCURY"),
                "venus": ("planet_venus.jpg", (255, 235, 170), "SHUKRA VENUS"),
                "shukra": ("planet_venus.jpg", (255, 235, 170), "SHUKRA VENUS"),
                "ketu": ("planet_ketu.jpg", (180, 120, 240), "KETU SHADOW"),
            }
            matched_planet = None
            for pk, pinfo in planet_file_map.items():
                if pk in ctx:
                    matched_planet = pinfo
                    break

            if matched_planet:
                p_file, p_glow, p_label = matched_planet
                header_text = f"{target_house}TH HOUSE • {p_label}"
                p_path = broll_dir / p_file
                if p_path.exists():
                    p_img = Image.open(p_path).convert("RGB")
                    pw, ph = p_img.size
                    p_crop = p_img.crop((0, int(ph * 0.16), pw, int(ph * 0.76)))
                    p_target_sz = 280
                    p_resized = p_crop.resize((p_target_sz, p_target_sz), Image.Resampling.LANCZOS)
                    y_p, x_p = np.ogrid[:p_target_sz, :p_target_sz]
                    r_p = p_target_sz / 2.0
                    d2_p = ((x_p - r_p) / r_p) ** 2 + ((y_p - r_p) / r_p) ** 2
                    m_p = np.clip((1.0 - d2_p) * 6.0, 0.0, 1.0)
                    m_arr_p = (m_p * 255).astype(np.uint8)
                    p_rgba = p_resized.convert("RGBA")
                    p_rgba.putalpha(Image.fromarray(m_arr_p))

                    p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    pdraw = ImageDraw.Draw(p_aura)
                    pdraw.ellipse([cx - 170, cy - 170, cx + 170, cy + 170], fill=(p_glow[0], p_glow[1], p_glow[2], 150))
                    p_aura = p_aura.filter(ImageFilter.GaussianBlur(26))
                    canvas = Image.alpha_composite(canvas, p_aura)
                    canvas.paste(p_rgba, (int(cx - p_target_sz // 2), int(cy - p_target_sz // 2)), p_rgba)
            else:
                header_text = f"{target_house}TH HOUSE • ASTROLOGICAL ALIGNMENT"

        # 4. Kundli Framework Gold Lines & Roman Numerals
        grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(grid)
        def _draw_gold(p1: Tuple[float, float], p2: Tuple[float, float], w: int = 3) -> None:
            gdraw.line([p1, p2], fill=(6, 3, 1, 240), width=w + 4)
            gdraw.line([p1, p2], fill=(245, 215, 95, 255), width=w)

        _draw_gold((x0, y0), (x1, y0), 4)
        _draw_gold((x1, y0), (x1, y1), 4)
        _draw_gold((x1, y1), (x0, y1), 4)
        _draw_gold((x0, y1), (x0, y0), 4)
        _draw_gold((x0, y0), (x1, y1), 3)
        _draw_gold((x1, y0), (x0, y1), 3)
        _draw_gold((x_mid, y0), (x1, y_mid), 3)
        _draw_gold((x1, y_mid), (x_mid, y1), 3)
        _draw_gold((x_mid, y1), (x0, y_mid), 3)
        _draw_gold((x0, y_mid), (x_mid, y0), 3)

        try:
            font_num = ImageFont.truetype("arial.ttf", 24)
            font_h = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            font_num = ImageFont.load_default()
            font_h = font_num

        for h_num, poly_pts in polygons.items():
            hcx, hcy = cls.get_centroid(poly_pts)
            dx = (hcx - x_mid) * 0.44
            dy = (hcy - y_mid) * 0.44
            rom = ROMAN_NUMS[h_num]
            bbox = gdraw.textbbox((0, 0), rom, font=font_num)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            col = (255, 245, 180, 255) if h_num == target_house else (180, 155, 115, 140)
            gdraw.text((hcx + dx - tw / 2, hcy + dy - th / 2), rom, fill=col, font=font_num)

        # Top English Context Header Card
        if header_text:
            top_y = y0 - 110
            bbox_h = gdraw.textbbox((0, 0), header_text, font=font_h)
            hw = bbox_h[2] - bbox_h[0]
            card_w = max(420, hw + 50)
            cx_card = (width - card_w) // 2
            gdraw.rounded_rectangle([cx_card, top_y, cx_card + card_w, top_y + 56], radius=14, fill=(14, 10, 22, 235), outline=(255, 215, 60, 210), width=2)
            gdraw.text((cx_card + (card_w - hw) // 2, top_y + 12), header_text, fill=(255, 235, 140), font=font_h)

        canvas = Image.alpha_composite(canvas, grid)

        # 7. Final output persistence
        if output_path is None:
            slug = re.sub(r"[^\w]", "_", topic.lower())[:15].strip("_") or "kundli_3d"
            h_tag = f"sc{scene_idx + 1}_h{target_house}"
            uid = hashlib.md5(f"{slug}_{scene_idx}_{time.time_ns()}".encode()).hexdigest()[:8]
            output_path = GENERATED_BROLL_DIR / f"{slug}_{h_tag}_{uid}.jpg"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(str(output_path), "JPEG", quality=95)
        logger.info(f"[KundliChartGenerator] Generated 3D Planet Kundli visual ({output_path.name}) for house {target_house}")
        return output_path
