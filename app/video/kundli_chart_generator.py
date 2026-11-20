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

        # 3D Perspective Projection Setup
        src_quad = np.float32([[0, 0], [1000, 0], [1000, 1000], [0, 1000]])
        dst_quad = np.float32([[210, 560], [870, 560], [970, 1260], [110, 1260]])
        M = cv2.getPerspectiveTransform(src_quad, dst_quad)

        def project_pt(u: float, v: float, h: float = 0.0) -> Tuple[float, float, float]:
            pt = np.array([[[u, v]]], dtype=np.float32)
            proj = cv2.perspectiveTransform(pt, M)[0][0]
            depth_scale = 0.74 + (v / 1000.0) * 0.36
            sx = float(proj[0])
            sy = float(proj[1]) - (h * depth_scale)
            return sx, sy, float(depth_scale)

        def project_poly(pts_uv: List[Tuple[float, float]], h: float = 0.0) -> List[Tuple[float, float]]:
            return [project_pt(u, v, h)[:2] for u, v in pts_uv]

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

            # Radial vignette to darken edges and focus on central 3D Kundli
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

        # 2. 3D Pedestal Base Extrusion (Slab depth beneath Kundli)
        pedestal = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(pedestal)
        c_bl, c_br = (110, 1260), (970, 1260)
        b_bl, b_br = (110, 1298), (970, 1298)
        pdraw.polygon([c_bl, c_br, b_br, b_bl], fill=(22, 16, 12, 235))
        pdraw.line([b_bl, b_br], fill=(160, 120, 40, 200), width=2)
        pdraw.line([c_bl, b_bl], fill=(120, 90, 30, 160), width=2)
        pdraw.line([c_br, b_br], fill=(120, 90, 30, 160), width=2)

        # Soft drop shadow under the 3D altar
        altar_shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        as_draw = ImageDraw.Draw(altar_shadow)
        as_draw.polygon([(100, 1290), (980, 1290), (1010, 1335), (70, 1335)], fill=(5, 3, 2, 190))
        altar_shadow = altar_shadow.filter(ImageFilter.GaussianBlur(16))
        canvas = Image.alpha_composite(canvas, altar_shadow)
        canvas = Image.alpha_composite(canvas, pedestal)

        # 3. 3D House Chamber Volumetric Glow (Screen Blending)
        target_poly_uv = uv_polygons.get(target_house, uv_polygons[1])
        proj_poly = project_poly(target_poly_uv, h=0)
        uc, vc = get_uv_centroid(target_poly_uv)
        scx, scy, _ = project_pt(uc, vc, h=0)

        bloom = Image.new("RGB", (width, height), (0, 0, 0))
        bdraw = ImageDraw.Draw(bloom)
        bdraw.ellipse([scx - 220, scy - 220, scx + 220, scy + 220], fill=(130, 80, 15))
        bdraw.polygon(proj_poly, fill=(240, 165, 35))
        bdraw.line(proj_poly + [proj_poly[0]], fill=(255, 230, 110), width=10)
        bloom_blur = bloom.filter(ImageFilter.GaussianBlur(32))

        sharp = Image.new("RGB", (width, height), (0, 0, 0))
        sdraw = ImageDraw.Draw(sharp)
        sdraw.polygon(proj_poly, fill=(170, 110, 20))
        sdraw.line(proj_poly + [proj_poly[0]], fill=(255, 230, 90), width=4)
        sharp_blur = sharp.filter(ImageFilter.GaussianBlur(4))

        bg_rgb = np.array(canvas.convert("RGB"), dtype=float)
        b_arr = (np.array(bloom_blur, dtype=float) + np.array(sharp_blur, dtype=float)) / 255.0
        screened = 1.0 - (1.0 - bg_rgb / 255.0) * (1.0 - np.clip(b_arr, 0.0, 0.95))
        canvas = Image.fromarray(np.clip(screened * 255.0, 0, 255).astype(np.uint8)).convert("RGBA")

        # 4. 3D Vertical Volumetric Light Shaft from the Active Chamber
        pillar = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pildraw = ImageDraw.Draw(pillar)
        poly_elev = project_poly(target_poly_uv, h=75)
        for p0, p1 in zip(proj_poly, poly_elev):
            pildraw.line([p0, p1], fill=(255, 215, 60, 60), width=2)
        pildraw.polygon(poly_elev, fill=(255, 200, 40, 25))
        pillar = pillar.filter(ImageFilter.GaussianBlur(8))
        canvas = Image.alpha_composite(canvas, pillar)

        # 5. 3D Engraved Gold Kundli Framework
        draw = ImageDraw.Draw(canvas)
        def _draw_3d_line(u1: float, v1: float, u2: float, v2: float, w: int = 3) -> None:
            p1 = project_pt(u1, v1, h=0)[:2]
            p2 = project_pt(u2, v2, h=0)[:2]
            draw.line([p1, p2], fill=(15, 10, 5, 140), width=w + 2)
            draw.line([p1, p2], fill=(230, 190, 65, 245), width=w)

        # Perimeter
        _draw_3d_line(0, 0, 1000, 0, 4)
        _draw_3d_line(1000, 0, 1000, 1000, 4)
        _draw_3d_line(1000, 1000, 0, 1000, 4)
        _draw_3d_line(0, 1000, 0, 0, 4)
        # Inner diagonals & diamonds
        _draw_3d_line(0, 0, 1000, 1000, 3)
        _draw_3d_line(1000, 0, 0, 1000, 3)
        _draw_3d_line(500, 0, 1000, 500, 3)
        _draw_3d_line(1000, 500, 500, 1000, 3)
        _draw_3d_line(500, 1000, 0, 500, 3)
        _draw_3d_line(0, 500, 500, 0, 3)

        # 6. Roman Numerals in 3D perspective
        try:
            font_num = ImageFont.truetype("arial.ttf", 24)
            font_badge = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font_num = ImageFont.load_default()
            font_badge = ImageFont.load_default()

        for h_num, poly_uv in uv_polygons.items():
            h_uc, h_vc = get_uv_centroid(poly_uv)
            du = (h_uc - 500.0) * 0.35
            dv = (h_vc - 500.0) * 0.35
            nx, ny, depth = project_pt(h_uc + du, h_vc + dv, h=0)
            rom = ROMAN_NUMS[h_num]
            bbox = draw.textbbox((0, 0), rom, font=font_num)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            col = (255, 245, 180, 240) if h_num == target_house else (160, 135, 100, 150)
            draw.text((nx - tw / 2, ny - th / 2), rom, fill=col, font=font_num)

        def _make_3d_sphere(src_p: Path, target_size: int, glow_c: Tuple[int, int, int] = (255, 200, 30)) -> Image.Image:
            src = Image.open(src_p).convert("RGB")
            w_s, h_s = src.size
            md = min(w_s, h_s)
            crop = src.crop(((w_s - md) // 2, (h_s - md) // 2, (w_s + md) // 2, (h_s + md) // 2))
            crop = crop.resize((target_size, target_size), Image.Resampling.LANCZOS)

            y, x = np.ogrid[:target_size, :target_size]
            r = target_size / 2.0
            dx = (x - r) / r
            dy = (y - r) / r
            dist2 = dx**2 + dy**2
            mask = (dist2 <= 1.0).astype(float)
            dz = np.sqrt(np.maximum(0.0, 1.0 - dist2))

            lx, ly, lz = -0.4, -0.5, 0.77
            nl = math.sqrt(lx**2 + ly**2 + lz**2)
            lx, ly, lz = lx / nl, ly / nl, lz / nl
            diffuse = np.maximum(0.15, dx * lx + dy * ly + dz * lz)
            spec = np.maximum(0.0, (dx * lx + dy * ly + dz * lz)) ** 8 * 0.4
            fresnel = ((1.0 - dz) ** 2.5) * 0.55

            arr = np.array(crop, dtype=float)
            shaded = arr * (diffuse[..., None] * 0.85 + 0.15) + spec[..., None] * 255.0
            for c in range(3):
                shaded[..., c] += fresnel * glow_c[c]
            shaded = np.clip(shaded, 0, 255).astype(np.uint8)

            res = Image.fromarray(shaded).convert("RGBA")
            alpha = (mask * 255).astype(np.uint8)
            res.putalpha(Image.fromarray(alpha))
            return res

        # 7. Composite 3D Celestial Objects & Aspects
        if is_sun_rahu:
            h_elev = 115
            sx_fl, sy_fl, _ = project_pt(500, 250, h=0)
            sx_pl, sy_pl, scale_p = project_pt(500, 250, h=h_elev)

            # 3D Contact Shadow on floor
            sh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shdraw = ImageDraw.Draw(sh)
            shdraw.ellipse([sx_fl - 120, sy_fl - 28, sx_fl + 120, sy_fl + 28], fill=(10, 5, 2, 160))
            sh = sh.filter(ImageFilter.GaussianBlur(14))
            canvas = Image.alpha_composite(canvas, sh)

            sun_sz = int(145 * scale_p)
            rahu_sz = int(135 * scale_p)
            sun_sp = _make_3d_sphere(broll_dir / "planet_sun.jpg", sun_sz, (255, 215, 40))
            rahu_sp = _make_3d_sphere(broll_dir / "planet_rahu.jpg", rahu_sz, (190, 80, 230))

            halo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            hdraw = ImageDraw.Draw(halo)
            hdraw.ellipse([sx_pl - 120, sy_pl - 80, sx_pl + 10, sy_pl + 50], fill=(255, 190, 30, 160))
            hdraw.ellipse([sx_pl - 10, sy_pl - 75, sx_pl + 120, sy_pl + 55], fill=(160, 80, 220, 140))
            halo = halo.filter(ImageFilter.GaussianBlur(25))
            canvas = Image.alpha_composite(canvas, halo)

            canvas.paste(sun_sp, (int(sx_pl - 110), int(sy_pl - sun_sz // 2)), sun_sp)
            canvas.paste(rahu_sp, (int(sx_pl + 5), int(sy_pl - rahu_sz // 2)), rahu_sp)

        elif is_12th:
            uc12, vc12 = get_uv_centroid(uv_polygons[12])
            sx_fl, sy_fl, _ = project_pt(uc12, vc12, h=0)

            vortex = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vortex)

            for h_step in range(10, 320, 12):
                t = h_step / 320.0
                r_spread = 30 + t * 240
                for ang in range(-20, 80, 12):
                    rad = math.radians(ang)
                    u_p = uc12 + math.cos(rad) * r_spread * 0.8
                    v_p = vc12 - math.sin(rad) * r_spread * 0.5
                    sx_v, sy_v, _ = project_pt(u_p, v_p, h=h_step)
                    vdraw.line([(sx_fl, sy_fl), (sx_v, sy_v)], fill=(255, 220, 70, int(220 * (1 - t * 0.6))), width=max(1, int(4 * (1 - t * 0.5))))

            np.random.seed(42)
            for _ in range(35):
                h_rnd = np.random.uniform(20, 300)
                t_rnd = h_rnd / 300.0
                ang_rnd = math.radians(np.random.uniform(-30, 85))
                dist_rnd = np.random.uniform(20, 40 + t_rnd * 220)
                u_pt = uc12 + math.cos(ang_rnd) * dist_rnd * 0.8
                v_pt = vc12 - math.sin(ang_rnd) * dist_rnd * 0.5
                px, py, _ = project_pt(u_pt, v_pt, h=h_rnd)
                p_sz = np.random.randint(4, 9)
                vdraw.ellipse([px - p_sz, py - p_sz, px + p_sz, py + p_sz], fill=(255, 245, 150, 245))

            v_blur = vortex.filter(ImageFilter.GaussianBlur(7))
            canvas = Image.alpha_composite(canvas, v_blur)
            canvas = Image.alpha_composite(canvas, vortex)

        elif is_mars:
            h_elev = 110
            sx_fl, sy_fl, _ = project_pt(500, 250, h=0)
            sx_pl, sy_pl, scale_p = project_pt(500, 250, h=h_elev)

            sh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shdraw = ImageDraw.Draw(sh)
            shdraw.ellipse([sx_fl - 90, sy_fl - 24, sx_fl + 90, sy_fl + 24], fill=(10, 5, 2, 170))
            sh = sh.filter(ImageFilter.GaussianBlur(16))
            canvas = Image.alpha_composite(canvas, sh)

            mars_sz = int(200 * scale_p)
            mars_p = broll_dir / "fresh_planet_mars_hubble.jpg"
            if not mars_p.exists():
                mars_p = broll_dir / "planet_mars.jpg"
            mars_sp = _make_3d_sphere(mars_p, mars_sz, (255, 75, 20))

            halo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            hdraw = ImageDraw.Draw(halo)
            hdraw.ellipse([sx_pl - mars_sz // 2 - 25, sy_pl - mars_sz // 2 - 25, sx_pl + mars_sz // 2 + 25, sy_pl + mars_sz // 2 + 25], fill=(255, 70, 20, 160))
            halo = halo.filter(ImageFilter.GaussianBlur(24))
            canvas = Image.alpha_composite(canvas, halo)

            canvas.paste(mars_sp, (int(sx_pl - mars_sz // 2), int(sy_pl - mars_sz // 2)), mars_sp)

        elif is_saturn:
            uc7, vc7 = get_uv_centroid(uv_polygons[7])
            sx_fl, sy_fl, _ = project_pt(uc7, vc7, h=0)
            sx_sat, sy_sat, scale_sat = project_pt(uc7, vc7, h=105)

            sh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shdraw = ImageDraw.Draw(sh)
            shdraw.ellipse([sx_fl - 110, sy_fl - 28, sx_fl + 110, sy_fl + 28], fill=(10, 5, 2, 180))
            sh = sh.filter(ImageFilter.GaussianBlur(18))
            canvas = Image.alpha_composite(canvas, sh)

            sat_p = Path("output/saturn_3d_feathered.png")
            if not sat_p.exists():
                sat_p = Path("output/saturn_seamless.png")
            if sat_p.exists():
                sat_trans = Image.open(sat_p)
                sat_w = int(270 * scale_sat)
                sat_h = int(sat_w * sat_trans.height / sat_trans.width)
                sat_resized = sat_trans.resize((sat_w, sat_h), Image.Resampling.LANCZOS)
                canvas.paste(sat_resized, (int(sx_sat - sat_w // 2), int(sy_sat - sat_h // 2)), sat_resized)

            # 3D PARABOLIC ASPECT ARCS: Saturn (H7) -> H9 (3rd), H1 (7th), H4 (10th)
            aspects = [
                ("3RD DRISHTI", uv_polygons[9], 160),
                ("7TH DRISHTI", uv_polygons[1], 190),
                ("10TH DRISHTI", uv_polygons[4], 160),
            ]

            beam_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            bdraw = ImageDraw.Draw(beam_layer)

            for tag, target_poly, apex_h in aspects:
                u_t, v_t = get_uv_centroid(target_poly)
                tx, ty, _ = project_pt(u_t, v_t, h=0)

                # 3D Impact Mandala / Shockwave Ring on target house floor
                bdraw.ellipse([tx - 40, ty - 14, tx + 40, ty + 14], fill=(255, 215, 60, 110), outline=(255, 245, 140, 230), width=2)
                bdraw.ellipse([tx - 65, ty - 22, tx + 65, ty + 22], outline=(255, 215, 60, 140), width=1)

                steps = 32
                arc_pts = []
                for s in range(steps):
                    t = s / float(steps - 1)
                    u_curr = uc7 + t * (u_t - uc7)
                    v_curr = vc7 + t * (v_t - vc7)
                    h_curr = (1.0 - t) * 105 + t * 0.0 + 4.0 * apex_h * t * (1.0 - t)
                    ax, ay, _ = project_pt(u_curr, v_curr, h=h_curr)
                    arc_pts.append((ax, ay))

                for idx in range(len(arc_pts) - 1):
                    p_a, p_b = arc_pts[idx], arc_pts[idx + 1]
                    bdraw.line([p_a, p_b], fill=(255, 190, 30, 150), width=8)
                    bdraw.line([p_a, p_b], fill=(255, 250, 180, 245), width=3)

                p_penultimate = arc_pts[-2]
                angle = math.atan2(ty - p_penultimate[1], tx - p_penultimate[0])
                tip_sz = 22
                tip1 = (tx - tip_sz * math.cos(angle - math.pi / 6), ty - tip_sz * math.sin(angle - math.pi / 6))
                tip2 = (tx - tip_sz * math.cos(angle + math.pi / 6), ty - tip_sz * math.sin(angle + math.pi / 6))
                bdraw.polygon([(tx, ty), tip1, tip2], fill=(255, 245, 180, 255))

                mid_pt = arc_pts[len(arc_pts) // 2]
                tag_x, tag_y = mid_pt[0] + (35 if u_t >= uc7 else -35), mid_pt[1] - 15
                bbox = bdraw.textbbox((0, 0), tag, font=font_badge)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                px, py = int(tag_x - tw // 2), int(tag_y - th // 2)
                bdraw.rounded_rectangle([px - 10, py - 4, px + tw + 10, py + th + 4], radius=6, fill=(15, 10, 22, 230), outline=(255, 215, 0, 200), width=1)
                bdraw.text((px, py), tag, fill=(255, 235, 140), font=font_badge)

            beam_blur = beam_layer.filter(ImageFilter.GaussianBlur(7))
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
