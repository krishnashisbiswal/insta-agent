"""
Instagram Carousel Slide Generator.

Renders high-fidelity 4:5 vertical (1080x1350) or 1:1 square (1080x1080) multi-slide
content decks with branded typography, slide counters, and swipe cues.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config.settings import OUTPUT_DIR
from app.niche.niche_profile import NicheProfile, get_default_niche

logger = logging.getLogger(__name__)


class CarouselBuilder:
    """
    Renders high-retention multi-slide Instagram carousel decks.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (OUTPUT_DIR / "carousels")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        font_names = [
            "arialbd.ttf" if bold else "arial.ttf",
            "seguiemj.ttf",
            "calibri.ttf",
        ]
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def build_deck(
        self,
        topic: str,
        slides_data: List[Dict[str, str]],  # [{"title": "...", "body": "...", "tag": "..."}]
        brand_handle: str = "@yourbrand",
        niche_profile: Optional[NicheProfile] = None,
        aspect_ratio: str = "4:5",  # "4:5" (1080x1350) or "1:1" (1080x1080)
    ) -> List[Path]:
        """
        Renders all slides in the deck and saves them as JPEG files.
        """
        profile = niche_profile or get_default_niche()
        width = 1080
        height = 1350 if aspect_ratio == "4:5" else 1080

        total_slides = len(slides_data)
        out_paths: List[Path] = []
        import re
        slug = re.sub(r"[^\w\-]", "_", topic.lower())[:25]
        deck_dir = self.output_dir / slug
        deck_dir.mkdir(parents=True, exist_ok=True)

        # Palettes based on niche
        palettes = {
            "tech_ai": {
                "bg_top": (10, 15, 30),
                "bg_bottom": (5, 8, 16),
                "accent": (0, 220, 255),
                "text_primary": (255, 255, 255),
                "text_secondary": (180, 195, 215),
                "card_bg": (20, 28, 50),
            },
            "fitness_wellness": {
                "bg_top": (25, 25, 28),
                "bg_bottom": (12, 12, 14),
                "accent": (255, 204, 0),
                "text_primary": (255, 255, 255),
                "text_secondary": (200, 200, 200),
                "card_bg": (38, 38, 42),
            },
            "personal_finance": {
                "bg_top": (12, 28, 22),
                "bg_bottom": (6, 15, 12),
                "accent": (52, 211, 153),
                "text_primary": (255, 255, 255),
                "text_secondary": (190, 210, 200),
                "card_bg": (20, 42, 34),
            },
            "astrology_vedic": {
                "bg_top": (22, 10, 30),
                "bg_bottom": (8, 4, 14),
                "accent": (255, 195, 80),
                "text_primary": (255, 255, 255),
                "text_secondary": (220, 195, 235),
                "card_bg": (36, 18, 48),
            },
        }
        palette = palettes.get(profile.niche_id, palettes["tech_ai"])

        for idx, slide in enumerate(slides_data, start=1):
            slide_path = deck_dir / f"slide_{idx:02d}.jpg"
            img = self._render_slide(
                slide_num=idx,
                total_slides=total_slides,
                title=slide.get("title", ""),
                body=slide.get("body", ""),
                tag=slide.get("tag", profile.name.upper()),
                brand_handle=brand_handle,
                palette=palette,
                width=width,
                height=height,
            )
            img.save(slide_path, quality=95)
            out_paths.append(slide_path)

        logger.info(f"Carousel deck rendered ({len(out_paths)} slides) -> {deck_dir}")
        return out_paths

    def _render_slide(
        self,
        slide_num: int,
        total_slides: int,
        title: str,
        body: str,
        tag: str,
        brand_handle: str,
        palette: Dict[str, Tuple[int, int, int]],
        width: int,
        height: int,
    ) -> Image.Image:
        canvas = Image.new("RGB", (width, height), palette["bg_bottom"])
        draw = ImageDraw.Draw(canvas)

        # 1. Subtle Gradient Background
        for y in range(height):
            frac = y / height
            r = int(palette["bg_top"][0] * (1 - frac) + palette["bg_bottom"][0] * frac)
            g = int(palette["bg_top"][1] * (1 - frac) + palette["bg_bottom"][1] * frac)
            b = int(palette["bg_top"][2] * (1 - frac) + palette["bg_bottom"][2] * frac)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Top Header: Tag Pill (Left) and Slide Counter (Right)
        header_y = 70
        tag_font = self._get_font(24, bold=True)
        counter_font = self._get_font(26, bold=True)

        # Tag pill
        tag_w = int(draw.textlength(tag, font=tag_font)) + 30
        draw.rounded_rectangle([70, header_y, 70 + tag_w, header_y + 44], radius=22, fill=palette["card_bg"])
        draw.text((85, header_y + 10), tag, font=tag_font, fill=palette["accent"])

        # Counter chip: "01 / 05"
        counter_str = f"{slide_num:02d} / {total_slides:02d}"
        draw.text((width - 180, header_y + 10), counter_str, font=counter_font, fill=palette["text_secondary"])

        # 3. Main Content Card
        card_top = 180
        card_bottom = height - 160
        draw.rounded_rectangle(
            [60, card_top, width - 60, card_bottom],
            radius=32,
            fill=palette["card_bg"],
            outline=palette["accent"],
            width=2,
        )

        # 4. Title
        title_font = self._get_font(52, bold=True)
        title_y = card_top + 80
        import textwrap
        title_lines = textwrap.wrap(title, width=28)
        for line in title_lines[:3]:
            draw.text((110, title_y), line, font=title_font, fill=palette["text_primary"])
            title_y += 66

        # Accent separator line
        draw.line([(110, title_y + 20), (240, title_y + 20)], fill=palette["accent"], width=4)
        body_y = title_y + 50

        # 5. Body text
        body_font = self._get_font(32, bold=False)
        body_lines = textwrap.wrap(body, width=42)
        for line in body_lines[:9]:
            draw.text((110, body_y), line, font=body_font, fill=palette["text_secondary"])
            body_y += 48

        # 6. Bottom Navigation Bar
        footer_y = height - 100
        handle_font = self._get_font(26, bold=True)
        draw.text((70, footer_y), brand_handle, font=handle_font, fill=palette["text_secondary"])

        cue_font = self._get_font(24, bold=True)
        if slide_num < total_slides:
            cue_text = "SWIPE ➔"
        else:
            cue_text = "SAVE THIS POST ★"

        cue_w = int(draw.textlength(cue_text, font=cue_font))
        draw.text((width - 70 - cue_w, footer_y), cue_text, font=cue_font, fill=palette["accent"])

        return canvas
