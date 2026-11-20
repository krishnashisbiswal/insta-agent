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
        box_size = 820
        x0 = (width - box_size) // 2
        x1 = x0 + box_size
        center_y = 780
        y0 = center_y - (box_size // 2)
        y1 = y0 + box_size
        x_mid = (x0 + x1) / 2.0
        y_mid = (y0 + y1) / 2.0

        p_tl = ((x0 + x_mid) / 2.0, (y0 + y_mid) / 2.0)
        p_tr = ((x1 + x_mid) / 2.0, (y0 + y_mid) / 2.0)
        p_bl = ((x0 + x_mid) / 2.0, (y1 + y_mid) / 2.0)
        p_br = ((x1 + x_mid) / 2.0, (y1 + y_mid) / 2.0)

        polygons = {
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

        # 1. Base ancient parchment graded with cinematic bokeh
        parchment_path = broll_dir / "authentic_vedic_kundli_parchment.jpg"
        if parchment_path.exists():
            from PIL import ImageEnhance, ImageOps
            base_raw = Image.open(parchment_path).convert("RGB")
            base_raw = ImageOps.fit(base_raw, (width, height), Image.Resampling.LANCZOS)
            base_blur = base_raw.filter(ImageFilter.GaussianBlur(28))
            base_dark = ImageEnhance.Brightness(base_blur).enhance(0.48)
            base_graded = ImageEnhance.Contrast(base_dark).enhance(1.20)
            
            # Radial vignette to darken edges and focus on central Kundli
            vignette = Image.new("L", (width, height), 0)
            vdraw = ImageDraw.Draw(vignette)
            vdraw.ellipse([60, 150, width - 60, height - 250], fill=255)
            vignette = vignette.filter(ImageFilter.GaussianBlur(140))
            v_arr = np.array(vignette, dtype=float) / 255.0
            bg_arr = np.array(base_graded, dtype=float)
            darkened = bg_arr * (0.35 + 0.65 * v_arr[..., None])
            canvas = Image.fromarray(np.clip(darkened, 0, 255).astype(np.uint8)).convert("RGBA")
        else:
            canvas = Image.new("RGBA", (width, height), (10, 8, 18, 255))

        poly = polygons.get(target_house, polygons[1])
        cx, cy = cls.get_centroid(poly)

        # 2. Multi-tier Volumetric Golden Bloom with Screen Blending
        bloom = Image.new("RGB", (width, height), (0, 0, 0))
        b_draw = ImageDraw.Draw(bloom)
        b_draw.ellipse([cx - 260, cy - 260, cx + 260, cy + 260], fill=(120, 75, 10))
        b_draw.polygon(poly, fill=(240, 160, 30))
        b_draw.line(poly + [poly[0]], fill=(255, 230, 100), width=10)
        bloom_blur = bloom.filter(ImageFilter.GaussianBlur(35))

        sharp_line = Image.new("RGB", (width, height), (0, 0, 0))
        s_draw = ImageDraw.Draw(sharp_line)
        s_draw.polygon(poly, fill=(160, 100, 15))
        s_draw.line(poly + [poly[0]], fill=(255, 225, 90), width=4)
        sharp_blur = sharp_line.filter(ImageFilter.GaussianBlur(4))

        bg_rgb = np.array(canvas.convert("RGB"), dtype=float)
        b_arr = (np.array(bloom_blur, dtype=float) + np.array(sharp_blur, dtype=float)) / 255.0
        screened = 1.0 - (1.0 - bg_rgb / 255.0) * (1.0 - np.clip(b_arr, 0.0, 0.95))
        canvas = Image.fromarray(np.clip(screened * 255.0, 0, 255).astype(np.uint8)).convert("RGBA")

        # 3. Metallic Gold Lines with Soft Ambient Depth
        gold_draw = ImageDraw.Draw(canvas)
        def _draw_gold_line(p1, p2, w=3):
            gold_draw.line([p1, p2], fill=(20, 12, 5, 120), width=w + 2)
            gold_draw.line([p1, p2], fill=(225, 185, 60, 240), width=w)

        _draw_gold_line((x0, y0), (x1, y0), 4)
        _draw_gold_line((x1, y0), (x1, y1), 4)
        _draw_gold_line((x1, y1), (x0, y1), 4)
        _draw_gold_line((x0, y1), (x0, y0), 4)
        _draw_gold_line((x0, y0), (x1, y1), 3)
        _draw_gold_line((x1, y0), (x0, y1), 3)
        _draw_gold_line((x_mid, y0), (x1, y_mid), 3)
        _draw_gold_line((x1, y_mid), (x_mid, y1), 3)
        _draw_gold_line((x_mid, y1), (x0, y_mid), 3)
        _draw_gold_line((x0, y_mid), (x_mid, y0), 3)

        # 4. Clean Roman Numerals
        try:
            font_num = ImageFont.truetype("arial.ttf", 26)
            font_badge = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font_num = ImageFont.load_default()
            font_badge = ImageFont.load_default()

        for h_num, poly_pts in polygons.items():
            hcx, hcy = cls.get_centroid(poly_pts)
            dx = (hcx - x_mid) * 0.35
            dy = (hcy - y_mid) * 0.35
            rom = ROMAN_NUMS.get(h_num, str(h_num))
            bbox = gold_draw.textbbox((0, 0), rom, font=font_num)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            col = (255, 245, 180, 240) if h_num == target_house else (160, 135, 100, 150)
            gold_draw.text((hcx + dx - tw / 2, hcy + dy - th / 2), rom, fill=col, font=font_num)

        def _make_sphere(src_p: Path, target_size: int, glow_c: Tuple[int, int, int]) -> Image.Image:
            src = Image.open(src_p).convert("RGB")
            w_s, h_s = src.size
            md = min(w_s, h_s)
            crop = src.crop(((w_s - md) // 2, (h_s - md) // 2, (w_s + md) // 2, (h_s + md) // 2))
            crop = crop.resize((target_size, target_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (target_size * 2, target_size * 2), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse([6, 6, target_size * 2 - 6, target_size * 2 - 6], fill=255)
            mask = mask.resize((target_size, target_size), Image.Resampling.LANCZOS)
            sph = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
            sph.paste(crop, (0, 0), mask)
            return sph

        def _draw_light_beam(dr: ImageDraw.ImageDraw, start: Tuple[float, float], end: Tuple[float, float], color: Tuple[int, int, int] = (255, 220, 50)) -> None:
            dr.line([start, end], fill=(*color, 240), width=4)
            tip_size = 22
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            tip1 = (end[0] - tip_size * math.cos(angle - math.pi / 6), end[1] - tip_size * math.sin(angle - math.pi / 6))
            tip2 = (end[0] - tip_size * math.cos(angle + math.pi / 6), end[1] - tip_size * math.sin(angle + math.pi / 6))
            dr.polygon([end, tip1, tip2], fill=(*color, 255))

        def _draw_aspect_tag(dr: ImageDraw.ImageDraw, txt: str, pt: Tuple[float, float]) -> None:
            bbox = dr.textbbox((0, 0), txt, font=font_badge)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            px, py = int(pt[0] - tw // 2), int(pt[1] - th // 2)
            dr.rounded_rectangle([px - 10, py - 4, px + tw + 10, py + th + 4], radius=6, fill=(15, 10, 22, 230), outline=(255, 215, 0, 200), width=1)
            dr.text((px, py), txt, fill=(255, 235, 140), font=font_badge)

        cx1, cy1 = cls.get_centroid(polygons[1])
        cx7, cy7 = cls.get_centroid(polygons[7])
        cx9, cy9 = cls.get_centroid(polygons[9])
        cx4, cy4 = cls.get_centroid(polygons[4])
        cx12, cy12 = cls.get_centroid(polygons[12])

        # 5. Composite 3D Planet Celestial Features based on context
        if is_sun_rahu:
            sun_p = broll_dir / "planet_sun.jpg"
            rahu_p = broll_dir / "planet_rahu.jpg"
            if sun_p.exists() and rahu_p.exists():
                sun = _make_sphere(sun_p, 140, (255, 205, 30))
                rahu = _make_sphere(rahu_p, 130, (190, 85, 230))
                halo2 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                h2_draw = ImageDraw.Draw(halo2)
                h2_draw.ellipse([cx1 - 130, cy1 - 80, cx1 + 10, cy1 + 60], fill=(255, 190, 30, 160))
                h2_draw.ellipse([cx1 - 10, cy1 - 75, cx1 + 130, cy1 + 65], fill=(160, 80, 220, 140))
                halo2 = halo2.filter(ImageFilter.GaussianBlur(24))
                canvas = Image.alpha_composite(canvas, halo2)
                sh2 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                sh2_draw = ImageDraw.Draw(sh2)
                sh2_draw.ellipse([cx1 - 130, cy1 + 45, cx1 + 130, cy1 + 80], fill=(10, 5, 2, 140))
                sh2 = sh2.filter(ImageFilter.GaussianBlur(16))
                canvas = Image.alpha_composite(canvas, sh2)
                canvas.paste(sun, (int(cx1 - 125), int(cy1 - 70)), sun)
                canvas.paste(rahu, (int(cx1 - 5), int(cy1 - 65)), rahu)

        elif is_12th:
            vortex = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            v_draw = ImageDraw.Draw(vortex)
            for ang in range(-45, 85, 6):
                rad = math.radians(ang)
                for length, alpha, wid in [(320, 180, 5), (260, 220, 3), (180, 250, 2)]:
                    ex = cx12 + math.cos(rad) * length
                    ey = cy12 - math.sin(rad) * length
                    v_draw.line([(cx12, cy12), (ex, ey)], fill=(255, 220, 60, alpha), width=wid)
            for p_r, p_a, p_sz in [(90, 15, 6), (150, 35, 7), (210, -5, 5), (260, 50, 8), (130, -25, 4), (190, 20, 6), (290, 10, 5)]:
                pr = math.radians(p_a)
                px = cx12 + math.cos(pr) * p_r
                py = cy12 - math.sin(pr) * p_r
                v_draw.ellipse([px - p_sz, py - p_sz, px + p_sz, py + p_sz], fill=(255, 245, 140, 240))
            v_blur = vortex.filter(ImageFilter.GaussianBlur(8))
            canvas = Image.alpha_composite(canvas, v_blur)
            canvas = Image.alpha_composite(canvas, vortex)

        elif is_mars:
            mars_p = broll_dir / "fresh_planet_mars_hubble.jpg"
            if not mars_p.exists():
                mars_p = broll_dir / "planet_mars.jpg"
            if mars_p.exists():
                mars_sp = _make_sphere(mars_p, 200, (255, 75, 20))
                sh4 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                sh4_draw = ImageDraw.Draw(sh4)
                sh4_draw.ellipse([cx1 - 90, cy1 + 75, cx1 + 90, cy1 + 115], fill=(10, 5, 2, 160))
                sh4 = sh4.filter(ImageFilter.GaussianBlur(18))
                canvas = Image.alpha_composite(canvas, sh4)
                halo4 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                h4_draw = ImageDraw.Draw(halo4)
                h4_draw.ellipse([cx1 - 120, cy1 - 120, cx1 + 120, cy1 + 120], fill=(255, 75, 20, 150))
                halo4 = halo4.filter(ImageFilter.GaussianBlur(25))
                canvas = Image.alpha_composite(canvas, halo4)
                canvas.paste(mars_sp, (int(cx1 - 100), int(cy1 - 100)), mars_sp)

        elif is_saturn:
            sat_seamless_p = PROJECT_ROOT / "output" / "saturn_seamless.png"
            if not sat_seamless_p.exists():
                sat_raw_p = broll_dir / "3_shani_saturn.jpg"
                if sat_raw_p.exists():
                    sat_raw = Image.open(sat_raw_p).convert("RGB")
                    w_r, h_r = sat_raw.size
                    crop_sat = sat_raw.crop((0, int(h_r * 0.22), w_r, int(h_r * 0.72)))
                    arr_sat = np.array(crop_sat.convert("RGBA"))
                    r_s, g_s, b_s, a_s = arr_sat.T
                    lum = 0.299 * r_s + 0.587 * g_s + 0.114 * b_s
                    alpha_s = np.clip((lum - 12) * (255.0 / 30.0), 0, 255).astype(np.uint8)
                    arr_sat[..., 3] = alpha_s.T
                    sat_clean = Image.fromarray(arr_sat)
                    cw_s, ch_s = sat_clean.size
                    ell_mask = Image.new("L", (cw_s, ch_s), 0)
                    edraw = ImageDraw.Draw(ell_mask)
                    edraw.ellipse([10, 10, cw_s - 10, ch_s - 10], fill=255)
                    ell_mask = ell_mask.filter(ImageFilter.GaussianBlur(15))
                    sat_clean.putalpha(Image.fromarray(np.minimum(np.array(sat_clean.split()[-1]), np.array(ell_mask))))
                    sat_clean.save(sat_seamless_p)

            if sat_seamless_p.exists():
                sat_trans = Image.open(sat_seamless_p)
                sat_w, sat_h = 260, int(260 * sat_trans.height / sat_trans.width)
                sat_resized = sat_trans.resize((sat_w, sat_h), Image.Resampling.LANCZOS)
                sh5 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                sh5_draw = ImageDraw.Draw(sh5)
                sh5_draw.ellipse([cx7 - 120, cy7 + 55, cx7 + 120, cy7 + 95], fill=(10, 5, 2, 170))
                sh5 = sh5.filter(ImageFilter.GaussianBlur(20))
                canvas = Image.alpha_composite(canvas, sh5)
                canvas.paste(sat_resized, (int(cx7 - sat_w // 2), int(cy7 - sat_h // 2)), sat_resized)

                beam_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                bdraw = ImageDraw.Draw(beam_layer)
                _draw_light_beam(bdraw, (cx7 + 45, cy7 - 20), (cx9 - 25, cy9 + 25), color=(255, 220, 50))
                _draw_light_beam(bdraw, (cx7, cy7 - 65), (cx1, cy1 + 75), color=(255, 220, 50))
                _draw_light_beam(bdraw, (cx7 - 45, cy7 - 20), (cx4 + 25, cy4 + 25), color=(255, 220, 50))
                _draw_aspect_tag(bdraw, "3RD DRISHTI", ((cx7 + cx9) // 2 + 40, (cy7 + cy9) // 2))
                _draw_aspect_tag(bdraw, "7TH DRISHTI", (x_mid, (cy7 + cy1) // 2 - 10))
                _draw_aspect_tag(bdraw, "10TH DRISHTI", ((cx7 + cx4) // 2 - 40, (cy7 + cy4) // 2))

                beam_blur = beam_layer.filter(ImageFilter.GaussianBlur(6))
                canvas = Image.alpha_composite(canvas, beam_blur)
                canvas = Image.alpha_composite(canvas, beam_layer)

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
