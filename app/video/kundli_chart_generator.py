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

    @staticmethod
    def _make_3d_sphere(img: Image.Image, sz: int, light_dir: Tuple[float, float, float] = (-0.45, -0.55, 0.7)) -> Image.Image:
        """
        Transforms a planar circular planet texture into a photorealistic 3D celestial sphere
        with diffuse Lambertian terminator, specular highlight, and atmospheric Fresnel limb haze.
        """
        img_res = img.resize((sz, sz), Image.Resampling.LANCZOS)
        arr = np.array(img_res).astype(np.float32)
        y, x = np.ogrid[:sz, :sz]
        r = sz / 2.0
        cx = cy = r
        nx = (x - cx) / r
        ny = (y - cy) / r
        r2 = nx * nx + ny * ny
        mask = r2 <= 1.0
        nz = np.zeros((sz, sz), dtype=np.float32)
        nz[mask] = np.sqrt(np.maximum(0.0, 1.0 - r2[mask]))

        lx, ly, lz = light_dir
        l_mag = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / l_mag, ly / l_mag, lz / l_mag

        diff = np.maximum(0.0, nx * lx + ny * ly + nz * lz)
        diff = 0.25 + 0.75 * diff

        vx, vy, vz = 0.0, 0.0, 1.0
        hx = lx + vx
        hy = ly + vy
        hz = lz + vz
        h_mag = np.sqrt(hx * hx + hy * hy + hz * hz)
        spec = np.maximum(0.0, (nx * hx + ny * hy + nz * hz) / np.maximum(1e-4, h_mag)) ** 16
        fresnel = (1.0 - nz) ** 2.5

        for c in range(3):
            arr[:, :, c] = arr[:, :, c] * diff + 255.0 * spec * 0.35 + 255.0 * fresnel * 0.2
        arr = np.clip(arr, 0, 255).astype(np.uint8)

        edge = np.clip((1.0 - np.sqrt(r2)) * sz * 0.5, 0.0, 1.0)
        alpha = (edge * 255).astype(np.uint8)

        res = Image.fromarray(arr).convert("RGBA")
        res.putalpha(Image.fromarray(alpha))
        return res

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
        Tilts the authentic Kundli chart in 3D perspective in the lower half of the frame,
        and renders a majestic 3D celestial planet in the top half, connected to the active house
        chamber via a volumetric light shaft, contact floor shadow, and aspect rays.
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
        is_jupiter = any(k in ctx for k in ["jupiter", "guru", "बृहस्पति", "गुरु"])

        # Determine target house
        if is_sun_rahu:
            target_house = 1
        elif is_12th:
            target_house = 12
        elif is_mars:
            target_house = 1
        elif is_saturn:
            target_house = 7
        elif is_jupiter:
            target_house = 9
        else:
            extracted_h, _ = cls.extract_house_and_planet(ctx)
            target_house = extracted_h or 1

        width, height = 1080, 1920
        box_size = 1000
        x0, y0 = 0, 0
        x1, y1 = box_size, box_size
        x_mid = box_size / 2.0
        y_mid = box_size / 2.0

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

        # 1. Draw flat Kundli chart on 1000x1000 buffer
        chart_img = Image.new("RGBA", (box_size, box_size), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(chart_img)

        # Base dark slate slab fill
        cdraw.rectangle([0, 0, box_size, box_size], fill=(12, 10, 20, 240))

        # Highlight active house
        glow_col = (255, 210, 60)
        if is_mars:
            glow_col = (255, 75, 30)
        elif is_12th:
            glow_col = (255, 220, 60)

        active_poly = polygons[target_house]
        cdraw.polygon(active_poly, fill=(glow_col[0], glow_col[1], glow_col[2], 120))

        def draw_g(p1: Tuple[float, float], p2: Tuple[float, float], w: int = 4) -> None:
            cdraw.line([p1, p2], fill=(245, 215, 95, 255), width=w)

        draw_g((x0, y0), (x1, y0), 6)
        draw_g((x1, y0), (x1, y1), 6)
        draw_g((x1, y1), (x0, y1), 6)
        draw_g((x0, y1), (x0, y0), 6)
        draw_g((x0, y0), (x1, y1), 4)
        draw_g((x1, y0), (x0, y1), 4)
        draw_g((x_mid, y0), (x1, y_mid), 4)
        draw_g((x1, y_mid), (x_mid, y1), 4)
        draw_g((x_mid, y1), (x0, y_mid), 4)
        draw_g((x0, y_mid), (x_mid, y0), 4)

        ROMAN_NUMS = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"}
        try:
            font_num = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font_num = ImageFont.load_default()

        for h_num, poly_pts in polygons.items():
            xs = [pt[0] for pt in poly_pts]
            ys = [pt[1] for pt in poly_pts]
            hcx, hcy = sum(xs) / len(xs), sum(ys) / len(ys)
            dx = (hcx - x_mid) * 0.44
            dy = (hcy - y_mid) * 0.44
            rom = ROMAN_NUMS[h_num]
            bbox = cdraw.textbbox((0, 0), rom, font=font_num)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            col = (255, 250, 200, 255) if h_num == target_house else (180, 160, 120, 160)
            cdraw.text((hcx + dx - tw / 2, hcy + dy - th / 2), rom, fill=col, font=font_num)

        # 2. 3D Perspective Homography Transform
        src_quad = np.float32([[0, 0], [box_size, 0], [box_size, box_size], [0, box_size]])
        dst_quad = np.float32([[210, 800], [870, 800], [990, 1440], [90, 1440]])
        M = cv2.getPerspectiveTransform(src_quad, dst_quad)

        def to_screen(px: float, py: float) -> Tuple[float, float]:
            pts = np.array([[[px, py]]], dtype=np.float32)
            res = cv2.perspectiveTransform(pts, M)
            return float(res[0][0][0]), float(res[0][0][1])

        chart_np = np.array(chart_img)
        tilted_np = cv2.warpPerspective(chart_np, M, (width, height), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        tilted_chart = Image.fromarray(tilted_np)

        # 3. Canvas Composition
        canvas = Image.new("RGBA", (width, height), (7, 6, 14, 255))

        # Cosmic nebula
        nebula = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ndraw = ImageDraw.Draw(nebula)
        ndraw.ellipse([width // 2 - 450, 250, width // 2 + 450, 1150], fill=(45, 18, 70, 160))
        ndraw.ellipse([width // 2 - 320, 320, width // 2 + 320, 960], fill=(85, 45, 20, 140))
        nebula = nebula.filter(ImageFilter.GaussianBlur(130))
        canvas = Image.alpha_composite(canvas, nebula)

        # Cosmic stardust
        np.random.seed(108 + scene_idx)
        sdraw = ImageDraw.Draw(canvas)
        for _ in range(500):
            sx = int(np.random.randint(15, width - 15))
            sy = int(np.random.randint(30, height - 30))
            bright = int(np.random.randint(120, 255))
            sz = 1 if np.random.random() > 0.08 else 2
            sdraw.rectangle([sx, sy, sx + sz, sy + sz], fill=(bright, bright, min(255, bright + 35), 210))

        # 4. 3D Pedestal / Extrusion under tilted chart
        pedestal = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(pedestal)
        p_poly = [
            (90, 1440), (990, 1440),
            (990, 1485), (90, 1485)
        ]
        pdraw.polygon(p_poly, fill=(20, 15, 30, 255))
        pdraw.line([(90, 1440), (990, 1440)], fill=(255, 215, 95, 230), width=4)
        pdraw.line([(90, 1485), (990, 1485)], fill=(180, 140, 50, 180), width=2)

        # Pedestal drop shadow
        p_shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        psdraw = ImageDraw.Draw(p_shadow)
        psdraw.ellipse([60, 1450, 1020, 1550], fill=(0, 0, 0, 200))
        p_shadow = p_shadow.filter(ImageFilter.GaussianBlur(25))
        canvas = Image.alpha_composite(canvas, p_shadow)
        canvas = Image.alpha_composite(canvas, pedestal)

        # Composite tilted Kundli chart
        canvas = Image.alpha_composite(canvas, tilted_chart)

        # Active house floor centroid & contact shadow
        xs = [pt[0] for pt in active_poly]
        ys = [pt[1] for pt in active_poly]
        ah_cx, ah_cy = sum(xs) / len(xs), sum(ys) / len(ys)
        hx_floor, hy_floor = to_screen(ah_cx, ah_cy)

        floor_eff = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        fedraw = ImageDraw.Draw(floor_eff)
        fedraw.ellipse([hx_floor - 95, hy_floor - 38, hx_floor + 95, hy_floor + 38], fill=(0, 0, 0, 180))
        fedraw.ellipse([hx_floor - 110, hy_floor - 45, hx_floor + 110, hy_floor + 45], fill=(glow_col[0], glow_col[1], glow_col[2], 100))
        fedraw.ellipse([hx_floor - 60, hy_floor - 25, hx_floor + 60, hy_floor + 25], fill=(255, 250, 200, 160))
        floor_eff = floor_eff.filter(ImageFilter.GaussianBlur(16))
        canvas = Image.alpha_composite(canvas, floor_eff)

        # 5. Top Celestial Planet
        px_top = 540 + (hx_floor - 540) * 0.28
        px_top = max(420.0, min(660.0, px_top))
        py_top = 400.0

        # Volumetric Connecting Light Shaft from Floor to Planet
        beam = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(beam)
        beam_quad = [
            (px_top - 60, py_top + 100),
            (px_top + 60, py_top + 100),
            (hx_floor + 90, hy_floor),
            (hx_floor - 90, hy_floor)
        ]
        bdraw.polygon(beam_quad, fill=(glow_col[0], glow_col[1], glow_col[2], 75))
        bdraw.line([(px_top, py_top + 80), (hx_floor, hy_floor)], fill=(255, 250, 210, 190), width=3)
        beam = beam.filter(ImageFilter.GaussianBlur(22))
        canvas = Image.alpha_composite(canvas, beam)

        # Planet Archetype Rendering
        header_text = ""
        if is_saturn:
            header_text = "7TH HOUSE • SHANI KARMIC DRISHTI"
            sat_p = broll_dir / "planet_saturn.jpg"
            if sat_p.exists():
                sat_raw = Image.open(sat_p).convert("RGB")
            else:
                sat_raw = Image.new("RGB", (400, 400), (190, 160, 110))
            p_sz = 260
            sat_sphere = cls._make_3d_sphere(sat_raw, p_sz)

            halo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            hdraw = ImageDraw.Draw(halo)
            hdraw.ellipse([px_top - 200, py_top - 170, px_top + 200, py_top + 170], fill=(255, 205, 50, 130))
            halo = halo.filter(ImageFilter.GaussianBlur(35))
            canvas = Image.alpha_composite(canvas, halo)

            rings = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            rdraw = ImageDraw.Draw(rings)
            rx, ry = px_top, py_top
            rw, rh = 230, 68
            for rad_x, rad_y, col, wid in [
                (rw + 25, rh + 7, (230, 200, 130, 160), 3),
                (rw + 15, rh + 5, (215, 180, 110, 220), 5),
                (rw - 5, rh - 2, (160, 130, 80, 120), 2),
                (rw - 20, rh - 7, (225, 195, 120, 210), 6),
                (rw - 38, rh - 13, (190, 160, 95, 150), 4),
            ]:
                rdraw.ellipse([rx - rad_x, ry - rad_y, rx + rad_x, ry + rad_y], outline=col, width=wid)

            canvas.paste(sat_sphere, (int(px_top - p_sz // 2), int(py_top - p_sz // 2)), sat_sphere)
            canvas = Image.alpha_composite(canvas, rings)

            # 3 Parabolic Aspect Arcs: Houses 9, 1, 4
            poly9 = polygons[9]; xs = [pt[0] for pt in poly9]; ys = [pt[1] for pt in poly9]
            h9x, h9y = to_screen(sum(xs)/len(xs), sum(ys)/len(ys))
            poly1 = polygons[1]; xs = [pt[0] for pt in poly1]; ys = [pt[1] for pt in poly1]
            h1x, h1y = to_screen(sum(xs)/len(xs), sum(ys)/len(ys))
            poly4 = polygons[4]; xs = [pt[0] for pt in poly4]; ys = [pt[1] for pt in poly4]
            h4x, h4y = to_screen(sum(xs)/len(xs), sum(ys)/len(ys))

            aspect_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            adraw = ImageDraw.Draw(aspect_layer)

            def draw_arc(p_start: Tuple[float, float], p_end: Tuple[float, float], peak_y: float, label: str) -> None:
                pts = []
                steps = 40
                for i in range(steps + 1):
                    t = i / float(steps)
                    ctrl_x = (p_start[0] + p_end[0]) / 2.0
                    ctrl_y = peak_y
                    bx = (1 - t)**2 * p_start[0] + 2 * (1 - t) * t * ctrl_x + t**2 * p_end[0]
                    by = (1 - t)**2 * p_start[1] + 2 * (1 - t) * t * ctrl_y + t**2 * p_end[1]
                    pts.append((bx, by))
                for i in range(len(pts) - 1):
                    adraw.line([pts[i], pts[i + 1]], fill=(255, 200, 40, 180), width=7)
                    adraw.line([pts[i], pts[i + 1]], fill=(255, 250, 190, 255), width=3)

                tx, ty = p_end
                adraw.ellipse([tx - 45, ty - 18, tx + 45, ty + 18], fill=(255, 210, 50, 110), outline=(255, 245, 160, 230), width=2)
                ang = math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0])
                tip_sz = 22
                tip1 = (tx - tip_sz * math.cos(ang - math.pi / 6), ty - tip_sz * math.sin(ang - math.pi / 6))
                tip2 = (tx - tip_sz * math.cos(ang + math.pi / 6), ty - tip_sz * math.sin(ang + math.pi / 6))
                adraw.polygon([(tx, ty), tip1, tip2], fill=(255, 245, 180, 255))

                mid_pt = pts[steps // 2]
                try:
                    f_arc = ImageFont.truetype("arial.ttf", 20)
                except Exception:
                    f_arc = ImageFont.load_default()
                bbox = adraw.textbbox((0, 0), label, font=f_arc)
                bw = bbox[2] - bbox[0]
                bh = bbox[3] - bbox[1]
                adraw.rounded_rectangle([mid_pt[0] - bw//2 - 10, mid_pt[1] - bh//2 - 6, mid_pt[0] + bw//2 + 10, mid_pt[1] + bh//2 + 6], radius=6, fill=(16, 12, 24, 230), outline=(255, 215, 60, 220), width=1)
                adraw.text((mid_pt[0] - bw//2, mid_pt[1] - bh//2), label, fill=(255, 235, 140), font=f_arc)

            draw_arc((px_top + 40, py_top + 50), (h9x, h9y), 520, "3RD DRISHTI")
            draw_arc((px_top, py_top + 70), (h1x, h1y), 480, "7TH DRISHTI")
            draw_arc((px_top - 40, py_top + 50), (h4x, h4y), 520, "10TH DRISHTI")

            arc_blur = aspect_layer.filter(ImageFilter.GaussianBlur(6))
            canvas = Image.alpha_composite(canvas, arc_blur)
            canvas = Image.alpha_composite(canvas, aspect_layer)

        elif is_sun_rahu:
            header_text = "1ST HOUSE • SUN & RAHU ECLIPSE"
            p_sz = 260
            sun_p = broll_dir / "planet_sun.jpg"
            if sun_p.exists():
                sun_raw = Image.open(sun_p).convert("RGB")
            else:
                sun_raw = Image.new("RGB", (400, 400), (255, 180, 50))
            sun_sphere = cls._make_3d_sphere(sun_raw, p_sz)

            solar_glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            sgdraw = ImageDraw.Draw(solar_glow)
            sgdraw.ellipse([px_top - 180, py_top - 180, px_top + 180, py_top + 180], fill=(255, 195, 40, 140))
            for ang in range(0, 360, 12):
                rad = math.radians(ang)
                rlen = 180 + (ang % 30) * 4
                sgdraw.line([(px_top, py_top), (px_top + math.cos(rad) * rlen, py_top + math.sin(rad) * rlen)], fill=(255, 220, 70, 160), width=3)
            solar_glow = solar_glow.filter(ImageFilter.GaussianBlur(22))
            canvas = Image.alpha_composite(canvas, solar_glow)
            canvas.paste(sun_sphere, (int(px_top - p_sz // 2), int(py_top - p_sz // 2)), sun_sphere)

            rahu_p = broll_dir / "planet_rahu.jpg"
            if rahu_p.exists():
                rahu_raw = Image.open(rahu_p).convert("RGB")
            else:
                rahu_raw = Image.new("RGB", (400, 400), (35, 25, 45))
            rahu_sz = int(p_sz * 0.92)
            rahu_sphere = cls._make_3d_sphere(rahu_raw, rahu_sz)
            r_x0 = int(px_top + 28 - rahu_sz // 2)
            r_y0 = int(py_top - 20 - rahu_sz // 2)
            canvas.paste(rahu_sphere, (r_x0, r_y0), rahu_sphere)

        elif is_12th:
            header_text = "12TH HOUSE • VYAYA ENERGY DRAIN"
            vortex = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vortex)
            for ang in range(-70, 110, 2):
                rad = math.radians(ang)
                for length, alpha, wid in [(480, 180, 4), (360, 210, 3), (240, 255, 2)]:
                    ex = hx_floor + math.cos(rad) * length * 0.7
                    ey = hy_floor - math.sin(rad) * length
                    vdraw.line([(hx_floor, hy_floor), (ex, ey)], fill=(255, 215, 60, alpha), width=wid)
            for p_r, p_a, p_sz_dot in [
                (70, 15, 6), (150, 35, 8), (220, -5, 6), (300, 50, 9), (110, -25, 5),
                (190, 20, 8), (370, 10, 7), (170, 65, 8), (260, 35, 9), (320, 75, 7),
                (90, 45, 5), (210, -15, 7), (290, 25, 8), (380, 60, 6)
            ]:
                pr = math.radians(p_a)
                px = hx_floor + math.cos(pr) * p_r * 0.7
                py = hy_floor - math.sin(pr) * p_r
                vdraw.ellipse([px - p_sz_dot, py - p_sz_dot, px + p_sz_dot, py + p_sz_dot], fill=(255, 245, 140, 250))
            v_blur = vortex.filter(ImageFilter.GaussianBlur(6))
            canvas = Image.alpha_composite(canvas, v_blur)
            canvas = Image.alpha_composite(canvas, vortex)

        elif is_mars:
            header_text = "1ST HOUSE • MARS FIERCE ENERGY"
            p_sz = 300
            mars_p = broll_dir / "planet_mars.jpg"
            if mars_p.exists():
                mars_raw = Image.open(mars_p).convert("RGB")
            else:
                mars_raw = Image.new("RGB", (400, 400), (220, 60, 20))
            mars_sphere = cls._make_3d_sphere(mars_raw, p_sz)

            m_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            mdraw = ImageDraw.Draw(m_aura)
            mdraw.ellipse([px_top - 200, py_top - 200, px_top + 200, py_top + 200], fill=(255, 60, 20, 170))
            mdraw.ellipse([px_top - 240, py_top - 240, px_top + 240, py_top + 240], fill=(255, 120, 30, 90))
            m_aura = m_aura.filter(ImageFilter.GaussianBlur(32))
            canvas = Image.alpha_composite(canvas, m_aura)
            canvas.paste(mars_sphere, (int(px_top - p_sz // 2), int(py_top - p_sz // 2)), mars_sphere)

        elif is_jupiter:
            header_text = "9TH HOUSE • GURU JUPITER BLESSINGS"
            p_sz = 310
            jup_p = broll_dir / "planet_jupiter.jpg"
            if jup_p.exists():
                jup_raw = Image.open(jup_p).convert("RGB")
            else:
                jup_raw = Image.new("RGB", (400, 400), (240, 190, 80))
            jup_sphere = cls._make_3d_sphere(jup_raw, p_sz)

            j_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            jdraw = ImageDraw.Draw(j_aura)
            jdraw.ellipse([px_top - 210, py_top - 210, px_top + 210, py_top + 210], fill=(255, 215, 60, 170))
            j_aura = j_aura.filter(ImageFilter.GaussianBlur(34))
            canvas = Image.alpha_composite(canvas, j_aura)
            canvas.paste(jup_sphere, (int(px_top - p_sz // 2), int(py_top - p_sz // 2)), jup_sphere)

        else:
            # Universal Planetary Mapper for Mercury, Venus, Moon, Sun, Ketu, etc.
            planet_file_map = {
                "mercury": ("planet_mercury.jpg", (100, 240, 160), "BUDHA MERCURY"),
                "budha": ("planet_mercury.jpg", (100, 240, 160), "BUDHA MERCURY"),
                "venus": ("planet_venus.jpg", (255, 235, 170), "SHUKRA VENUS"),
                "shukra": ("planet_venus.jpg", (255, 235, 170), "SHUKRA VENUS"),
                "moon": ("planet_moon.jpg", (210, 230, 255), "CHANDRA MOON"),
                "chandra": ("planet_moon.jpg", (210, 230, 255), "CHANDRA MOON"),
                "ketu": ("planet_ketu.jpg", (180, 120, 240), "KETU SHADOW"),
                "sun": ("planet_sun.jpg", (255, 200, 40), "SURYA SUN"),
                "surya": ("planet_sun.jpg", (255, 200, 40), "SURYA SUN"),
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
                else:
                    p_img = Image.new("RGB", (400, 400), p_glow)
                p_sz = 290
                p_sphere = cls._make_3d_sphere(p_img, p_sz)

                p_aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                pdraw = ImageDraw.Draw(p_aura)
                pdraw.ellipse([px_top - 190, py_top - 190, px_top + 190, py_top + 190], fill=(p_glow[0], p_glow[1], p_glow[2], 150))
                p_aura = p_aura.filter(ImageFilter.GaussianBlur(30))
                canvas = Image.alpha_composite(canvas, p_aura)
                canvas.paste(p_sphere, (int(px_top - p_sz // 2), int(py_top - p_sz // 2)), p_sphere)
            else:
                header_text = f"{target_house}TH HOUSE • CELESTIAL ALIGNMENT"

        # 6. Top English Floating 3D Badge Pill
        try:
            font_h = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            font_h = font_num
        badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(badge)
        bbox_h = bdraw.textbbox((0, 0), header_text, font=font_h)
        hw = bbox_h[2] - bbox_h[0]
        card_w = max(440, hw + 60)
        cx_card = (width - card_w) // 2
        top_y = 170
        bdraw.rounded_rectangle([cx_card, top_y, cx_card + card_w, top_y + 58], radius=14, fill=(14, 10, 22, 235), outline=(255, 215, 60, 220), width=2)
        bdraw.text((cx_card + (card_w - hw) // 2, top_y + 13), header_text, fill=(255, 235, 140), font=font_h)
        canvas = Image.alpha_composite(canvas, badge)

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
