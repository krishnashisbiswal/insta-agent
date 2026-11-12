import logging
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    BRAND_WATERMARK,
    DEFAULT_FONT_PATH,
    FALLBACK_FONT_PATH,
    IMPACT_FONT_PATH,
    REELS_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)
from app.video.visual_generator import generate_scene_frame
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    concatenate_videoclips,
)

logger = logging.getLogger(__name__)


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Load system font with fallbacks."""
    paths_to_try = []
    if bold:
        paths_to_try.extend([DEFAULT_FONT_PATH, IMPACT_FONT_PATH, FALLBACK_FONT_PATH])
    else:
        paths_to_try.extend([FALLBACK_FONT_PATH, DEFAULT_FONT_PATH])

    for p in paths_to_try:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue

    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> List[str]:
    """Wrap text so it fits within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))

    return lines


def render_card_overlay_layer(
    width: int,
    height: int,
    on_screen_text: str,
    scene_number: int,
    total_scenes: int,
    accent_color: Tuple[int, int, int] = (255, 215, 0),
    topic_badge: Optional[str] = None,
    brand_watermark: Optional[str] = None,
) -> Image.Image:
    """
    Render transparent RGBA layer containing high-conversion on-screen card, badges, and progress indicators.
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = width, height

    # 1. Top High-Impact Category/Alert Badge
    SCENE_BADGES = {
        1: ("URGENT WARNING", (239, 68, 68)),    # High-urgency red
        2: ("DANGER CHECK", (249, 115, 22)),     # Warning orange
        3: ("CHART REVELATION", (234, 179, 8)), # Gold discovery
        4: ("ZERO-COST REMEDY", (16, 185, 129)),# Emerald solution
        5: ("COMMENT YOUR SIGN", (147, 92, 255)),# Algorithmic CTA purple
    }

    # 1. Top Creator Watermark (Cleanly anchored at top safe zone)
    brand_handle = (brand_watermark or BRAND_WATERMARK or "").strip()
    wm_h = 0
    wm_y = int(h * 0.07)  # Top safe zone (~135px)

    if brand_handle:
        wm_font = get_font(26, bold=True)
        wm_bbox = draw.textbbox((0, 0), brand_handle, font=wm_font)
        wm_w = wm_bbox[2] - wm_bbox[0]
        wm_h = wm_bbox[3] - wm_bbox[1]
        wm_x = (w - wm_w) // 2

        wm_px, wm_py = 24, 8
        draw.rounded_rectangle(
            [wm_x - wm_px, wm_y - wm_py, wm_x + wm_w + wm_px, wm_y + wm_h + wm_py],
            radius=16,
            fill=(10, 8, 16, 200),
            outline=(255, 255, 255, 120),
            width=1,
        )
        draw.text((wm_x, wm_y), brand_handle, font=wm_font, fill=(255, 255, 255, 245))

    # 2. Scene Category/Insight Badge (Positioned with guaranteed clearance below watermark)
    badge_text = ""
    badge_color = accent_color
    if topic_badge:
        badge_text = topic_badge.strip().upper()
    elif scene_number in SCENE_BADGES:
        badge_text, badge_color = SCENE_BADGES[scene_number]

    if badge_text:
        badge_font = get_font(30, bold=True)
        badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw = badge_bbox[2] - badge_bbox[0] + 48
        bh = badge_bbox[3] - badge_bbox[1] + 22
        bx = (w - bw) // 2
        # Minimum 35px separation below watermark pill to prevent ANY overlap
        by = max(int(h * 0.15), wm_y + wm_h + 35) if brand_handle else int(h * 0.12)

        # Outer glow
        draw.rounded_rectangle(
            [bx - 2, by - 2, bx + bw + 2, by + bh + 2],
            radius=18,
            fill=(0, 0, 0, 0),
            outline=badge_color + (80,),
            width=2,
        )
        draw.rounded_rectangle(
            [bx, by, bx + bw, by + bh],
            radius=16,
            fill=(12, 10, 20, 235),
            outline=badge_color + (230,),
            width=2,
        )
        draw.text(
            ((w - (badge_bbox[2] - badge_bbox[0])) // 2, by + 10),
            badge_text,
            font=badge_font,
            fill=badge_color + (255,),
        )

    # 2. Main On-Screen Card in Safe Zone (Center)
    card_font = get_font(64, bold=True)
    card_max_w = int(w * 0.84)
    lines = wrap_text(on_screen_text.upper(), card_font, card_max_w, draw)

    if lines:
        line_height = 82
        total_text_h = len(lines) * line_height
        box_pad_x = 48
        box_pad_y = 38

        # Find widest line
        max_line_w = 0
        for l in lines:
            bbox = draw.textbbox((0, 0), l, font=card_font)
            lw = bbox[2] - bbox[0]
            if lw > max_line_w:
                max_line_w = lw

        card_w = max_line_w + (box_pad_x * 2)
        card_h = total_text_h + (box_pad_y * 2)

        card_x = (w - card_w) // 2
        card_y = int(h * 0.44) - (card_h // 2)

        # Ambient glow behind card
        draw.rounded_rectangle(
            [card_x - 6, card_y - 6, card_x + card_w + 6, card_y + card_h + 6],
            radius=30,
            fill=(0, 0, 0, 0),
            outline=accent_color + (70,),
            width=4,
        )

        # Deep drop shadow
        draw.rounded_rectangle(
            [card_x + 10, card_y + 14, card_x + card_w + 10, card_y + card_h + 14],
            radius=28,
            fill=(0, 0, 0, 190),
        )

        # High-contrast frosted glass container
        draw.rounded_rectangle(
            [card_x, card_y, card_x + card_w, card_y + card_h],
            radius=26,
            fill=(8, 8, 14, 245),
            outline=accent_color + (230,),
            width=3,
        )

        # Highlight keywords logic
        HIGHLIGHT_WORDS = {"STOP", "DON'T", "NEVER", "WARNING", "PUKHRAJ", "NEELAM", "RUIN", "ENEMY", "FREE", "REMEDY", "COMMENT", "90%", "DANGER", "SHIVA", "SHANI"}

        # Draw text lines
        text_start_y = card_y + box_pad_y
        for i, line in enumerate(lines):
            l_bbox = draw.textbbox((0, 0), line, font=card_font)
            l_w = l_bbox[2] - l_bbox[0]
            lx = (w - l_w) // 2
            ly = text_start_y + (i * line_height)

            # Strong drop shadow behind letters
            draw.text((lx + 4, ly + 4), line, font=card_font, fill=(0, 0, 0, 255))

            # Check if this line has highlight keywords
            has_kw = any(kw in line.split() for kw in HIGHLIGHT_WORDS)
            if has_kw or (i == 0 and len(lines) > 1):
                text_color = (255, 230, 0, 255) # Electric vibrant yellow
            else:
                text_color = (255, 255, 255, 255) # Crisp white

            draw.text((lx, ly), line, font=card_font, fill=text_color)

    # 3. Bottom Progress Bar Dots (Scene indicators)
    dot_radius = 7
    dot_gap = 22
    total_dots_w = (total_scenes * (dot_radius * 2)) + ((total_scenes - 1) * dot_gap)
    start_dot_x = (w - total_dots_w) // 2
    dots_y = int(h * 0.88)

    for idx in range(total_scenes):
        dx = start_dot_x + (idx * (dot_radius * 2 + dot_gap))
        if idx == (scene_number - 1):
            # Active scene dot (larger glowing pill)
            draw.rounded_rectangle(
                [dx - 8, dots_y - 4, dx + 20, dots_y + 8],
                radius=6,
                fill=accent_color + (255,),
            )
        else:
            draw.ellipse(
                [dx, dots_y, dx + dot_radius * 2, dots_y + dot_radius * 2],
                fill=(180, 180, 190, 120),
            )

    return overlay


def render_scene_overlay(
    bg_image: Image.Image,
    on_screen_text: str,
    scene_number: int,
    total_scenes: int,
    accent_color: Tuple[int, int, int] = (255, 215, 0),
    topic_badge: Optional[str] = None,
) -> Image.Image:
    """
    Render high-conversion on-screen card and aesthetic UI onto the scene background.
    """
    canvas = bg_image.copy().convert("RGBA")
    w, h = canvas.size
    overlay = render_card_overlay_layer(
        width=w,
        height=h,
        on_screen_text=on_screen_text,
        scene_number=scene_number,
        total_scenes=total_scenes,
        accent_color=accent_color,
        topic_badge=topic_badge,
    )
    final_canvas = Image.alpha_composite(canvas, overlay)
    return final_canvas.convert("RGB")


def create_reel_video(
    script_data: Dict[str, Any],
    audio_path: Optional[str] = None,
    output_filename: Optional[str] = None,
    theme_name: str = "cosmic",
) -> Path:
    """
    Assemble the complete 1080x1920 vertical Reel video using authentic photorealistic 4K visuals.
    All crude procedural 3D wireframes, polygon models, and pseudo-objects are completely removed.
    """
    from app.video.cinematic_composer import create_cinematic_reel_video
    return create_cinematic_reel_video(
        script_data=script_data,
        audio_path=audio_path,
        output_filename=output_filename,
    )


if __name__ == "__main__":
    print("Testing Video Composer...")
    # Test sample with dummy data
    sample_script = {
        "topic": "Shani Sade Sati Secrets",
        "niche": "Vedic Astrology",
        "scenes": [
            {"scene_num": 1, "on_screen_text": "DON'T FEAR SHANI", "estimated_seconds": 3},
            {"scene_num": 2, "on_screen_text": "HE TESTS YOUR KARMA", "estimated_seconds": 3},
        ],
    }
    # Check if voice file exists
    test_audio = PROJECT_ROOT / "output" / "audio" / "voice_saturn_delays_your_result.mp3"
    if test_audio.exists():
        vid = create_reel_video(sample_script, str(test_audio), "test_sample_reel.mp4")
        print("Generated video at:", vid)
    else:
        print("Please generate audio first.")
