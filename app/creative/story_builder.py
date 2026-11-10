"""
Instagram Story Image Generator.

Renders 9:16 vertical (1080x1920) story cards with interactive zones
(polls, questions, quiz stickers, link cards).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont

from config.settings import OUTPUT_DIR
from app.niche.niche_profile import NicheProfile, get_default_niche

logger = logging.getLogger(__name__)


class StoryBuilder:
    """
    Renders high-engagement Instagram Story cards.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (OUTPUT_DIR / "stories")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        for name in ["arialbd.ttf" if bold else "arial.ttf", "calibri.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def build_poll_story(
        self,
        question: str,
        option_a: str,
        option_b: str,
        brand_handle: str = "@yourbrand",
        niche_profile: Optional[NicheProfile] = None,
    ) -> Path:
        """
        Renders a 9:16 Story card with a prominent interactive Poll sticker zone.
        """
        profile = niche_profile or get_default_niche()
        width, height = 1080, 1920
        canvas = Image.new("RGB", (width, height), (15, 12, 25))
        draw = ImageDraw.Draw(canvas)

        # 1. Dark Gradient
        for y in range(height):
            frac = y / height
            r = int(25 * (1 - frac) + 10 * frac)
            g = int(18 * (1 - frac) + 8 * frac)
            b = int(45 * (1 - frac) + 18 * frac)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Brand Header
        header_font = self._get_font(28, bold=True)
        draw.text((width // 2 - 100, 140), brand_handle, font=header_font, fill=(220, 220, 235))

        # 3. Question Banner
        q_box_top = 400
        draw.rounded_rectangle([80, q_box_top, width - 80, q_box_top + 320], radius=36, fill=(35, 28, 60))
        q_font = self._get_font(48, bold=True)
        import textwrap
        q_lines = textwrap.wrap(question, width=24)
        qy = q_box_top + 60
        for line in q_lines[:4]:
            lw = int(draw.textlength(line, font=q_font))
            draw.text(((width - lw) // 2, qy), line, font=q_font, fill=(255, 255, 255))
            qy += 60

        # 4. Interactive Poll Mockup Buttons
        poll_top = 850
        # Option A
        draw.rounded_rectangle([120, poll_top, width - 120, poll_top + 130], radius=28, fill=(255, 255, 255))
        opt_font = self._get_font(38, bold=True)
        aw = int(draw.textlength(option_a, font=opt_font))
        draw.text(((width - aw) // 2, poll_top + 42), option_a, font=opt_font, fill=(20, 20, 30))

        # Option B
        draw.rounded_rectangle([120, poll_top + 170, width - 120, poll_top + 300], radius=28, fill=(255, 255, 255))
        bw = int(draw.textlength(option_b, font=opt_font))
        draw.text(((width - bw) // 2, poll_top + 212), option_b, font=opt_font, fill=(20, 20, 30))

        # 5. Sticker Instruction
        inst_font = self._get_font(28, bold=False)
        inst_text = "TAP YOUR ANSWER ABOVE"
        iw = int(draw.textlength(inst_text, font=inst_font))
        draw.text(((width - iw) // 2, 1300), inst_text, font=inst_font, fill=(180, 180, 200))

        import re
        slug = re.sub(r"[^\w\-]", "_", question.lower())[:25]
        out_file = self.output_dir / f"story_poll_{slug}.jpg"
        canvas.save(out_file, quality=95)
        logger.info(f"Story Poll card rendered -> {out_file}")
        return out_file
