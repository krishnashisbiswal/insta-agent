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
) -> Image.Image:
    """
    Render transparent RGBA layer containing high-conversion on-screen card, badges, and progress indicators.
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = width, height

    # 1. Top High-Impact Category/Alert Badge
    SCENE_BADGES = {
        1: ("✦ URGENT WARNING ✦", (239, 68, 68)),    # High-urgency red
        2: ("✦ DANGER CHECK ✦", (249, 115, 22)),     # Warning orange
        3: ("✦ CHART REVELATION ✦", (234, 179, 8)), # Gold discovery
        4: ("✦ ZERO-COST REMEDY ✦", (16, 185, 129)),# Emerald solution
        5: ("✦ COMMENT YOUR SIGN ✦", (147, 92, 255)),# Algorithmic CTA purple
    }

    if scene_number in SCENE_BADGES:
        badge_text, badge_color = SCENE_BADGES[scene_number]
    elif topic_badge:
        badge_text, badge_color = f"✦ {topic_badge.upper()} ✦", accent_color
    else:
        badge_text, badge_color = "✦ VEDIC ASTROLOGY ✦", accent_color

    badge_font = get_font(32, bold=True)
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = badge_bbox[2] - badge_bbox[0] + 52
    bh = badge_bbox[3] - badge_bbox[1] + 26
    bx = (w - bw) // 2
    by = int(h * 0.16)

    # Glowing outer badge pill
    draw.rounded_rectangle(
        [bx - 3, by - 3, bx + bw + 3, by + bh + 3],
        radius=20,
        fill=(0, 0, 0, 0),
        outline=badge_color + (90,),
        width=2,
    )
    draw.rounded_rectangle(
        [bx, by, bx + bw, by + bh],
        radius=18,
        fill=(10, 10, 18, 230),
        outline=badge_color + (240,),
        width=2,
    )
    draw.text(
        ((w - (badge_bbox[2] - badge_bbox[0])) // 2, by + 12),
        badge_text,
        font=badge_font,
        fill=badge_color + (255,),
    )

    # 1B. Brand / Creator Watermark (@neovibestore.in)
    if BRAND_WATERMARK:
        wm_font = get_font(24, bold=True)
        wm_text = BRAND_WATERMARK.strip()
        wm_bbox = draw.textbbox((0, 0), wm_text, font=wm_font)
        wm_w = wm_bbox[2] - wm_bbox[0]
        wm_h = wm_bbox[3] - wm_bbox[1]
        wm_x = (w - wm_w) // 2
        wm_y = by + bh + 16

        wm_px, wm_py = 20, 6
        draw.rounded_rectangle(
            [wm_x - wm_px, wm_y - wm_py, wm_x + wm_w + wm_px, wm_y + wm_h + wm_py],
            radius=14,
            fill=(10, 8, 16, 175),
            outline=(255, 255, 255, 100),
            width=1,
        )
        draw.text((wm_x, wm_y), wm_text, font=wm_font, fill=(255, 255, 255, 235))

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
    audio_path: str,
    output_filename: Optional[str] = None,
    theme_name: str = "cosmic",
) -> Path:
    """
    Assemble the complete 1080x1920 vertical Reel video.
    Synchronizes visual scenes and on-screen cards with the voiceover audio.
    """
    scenes = script_data.get("scenes", [])
    if not scenes:
        raise ValueError("Script data contains no scenes.")

    topic = script_data.get("topic", "Instagram Reel")
    total_scenes = len(scenes)

    # 1. Load audio clip to get exact duration
    audio_clip = AudioFileClip(audio_path)
    total_audio_duration = audio_clip.duration
    logger.info(f"Loaded master audio duration: {total_audio_duration:.2f} seconds")

    # 2. Calculate durations per scene
    # Check if timing metadata exists from script_agent or allocate proportionally
    timing_rows = script_data.get("timing", {}).get("rows", [])
    if len(timing_rows) == total_scenes:
        raw_durations = [r["dur"] for r in timing_rows]
    else:
        # Check estimated_seconds in scenes
        raw_durations = [float(s.get("estimated_seconds", 4.0)) for s in scenes]

    total_est = sum(raw_durations)
    scaling_factor = total_audio_duration / total_est if total_est > 0 else 1.0
    scene_durations = [round(d * scaling_factor, 3) for d in raw_durations]

    # Adjust rounding discrepancy on final scene
    durations_sum = sum(scene_durations)
    scene_durations[-1] += round(total_audio_duration - durations_sum, 3)

    # Theme accent color
    accent_colors = {
        "cosmic": (255, 215, 0),        # Gold on dark purple
        "dark_gold": (255, 223, 77),     # Bright gold
        "neon_cyber": (0, 240, 255),     # Electric Cyan
        "crimson_fire": (255, 107, 53),  # Fiery Orange
        "minimalist_dark": (255, 255, 255),
    }
    accent = accent_colors.get(theme_name, (255, 215, 0))

    # 3. Check visual theme configuration
    is_3d_theme = theme_name in ("3d_space", "cosmic_3d", "3d", "space_3d") or script_data.get("use_3d", False)

    if is_3d_theme:
        from app.video.engine_3d import Engine3D
        niche_str = script_data.get("niche", "")
        detected_object = Engine3D.detect_3d_object_type(topic=topic, niche=niche_str)

        w, h = VIDEO_WIDTH, VIDEO_HEIGHT
        cx, cy = w // 2, int(h * 0.42)
        radius = 240
        px, py = cx - radius, cy - radius

        # Base space backdrop with stars
        base_space = Engine3D.create_space_backdrop(w, h, t=0.0, style="space")

        # Saturn rings and glow precomputations for planet scenes
        back_rings = Engine3D.render_saturn_rings(w, h, tilt_deg=26.0, inner_r=int(radius * 1.25), outer_r=int(radius * 2.1), center=(cx, cy), back_only=True)
        front_rings = Engine3D.render_saturn_rings(w, h, tilt_deg=26.0, inner_r=int(radius * 1.25), outer_r=int(radius * 2.1), center=(cx, cy), front_only=True)

        glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.ellipse([px - 14, py - 14, px + radius * 2 + 14, py + radius * 2 + 14], outline=(180, 140, 255, 90), width=10)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(16))
        front_overlay = Image.alpha_composite(glow_layer, front_rings) if front_rings else glow_layer

        orbits = [
            {"rx": 360, "ry": 160, "color": (255, 215, 0, 110), "speed": 1.2, "node_color": (255, 215, 0)},
            {"rx": 450, "ry": 200, "color": (147, 92, 255, 90), "speed": -0.8, "node_color": (230, 180, 255)},
            {"rx": 530, "ry": 235, "color": (239, 68, 68, 80), "speed": 0.6, "node_color": (255, 100, 100)},
        ]

    # Generate visual clips for each scene
    video_clips = []
    current_time_offset = 0.0

    for idx, sc in enumerate(scenes):
        scene_num = idx + 1
        scene_dur = max(1.5, scene_durations[idx])
        screen_text = sc.get("on_screen_text", topic)

        if is_3d_theme:
            # 1. Detect scene-specific 3D thematic object (Gemstone, Kundli, Planet, Karmic Vortex, Sri Yantra)
            scene_visual = Engine3D.detect_scene_theme_3d(
                scene_idx=idx,
                total_scenes=total_scenes,
                scene_text=sc.get("spoken_line", "") + " " + screen_text,
                topic=topic,
                niche=niche_str,
            )
            v_type = scene_visual["type"]
            scene_accent = scene_visual.get("accent", accent)
            scene_badge = scene_visual.get("badge", script_data.get("niche", "VEDIC ASTROLOGY"))

            # Pre-render the transparent scene card layer once for this scene
            card_overlay = render_card_overlay_layer(
                width=w,
                height=h,
                on_screen_text=screen_text,
                scene_number=scene_num,
                total_scenes=total_scenes,
                accent_color=scene_accent,
                topic_badge=scene_badge,
            )

            # Pre-cache or setup the visual generator for this scene
            if v_type == "gemstone_3d":
                gem_t = scene_visual.get("gem_type", "blue_sapphire")
                gem_cache = Engine3D.preload_gemstone_cache(gem_type=gem_t, steps=36, radius=radius)
            elif v_type == "kundli_chart_3d":
                h_num = scene_visual.get("highlight_house", 8)
                kundli_cache = Engine3D.preload_kundli_cache(highlight_house=h_num, steps=24, size=480)
            elif v_type == "karmic_vortex_3d":
                vortex_cache = Engine3D.preload_vortex_cache(steps=24, radius=280)
            elif v_type == "sacred_yantra_3d":
                yantra_cache = Engine3D.preload_yantra_cache(steps=24, radius=260)
            elif v_type == "zodiac_wheel_3d":
                zodiac_cache = Engine3D.preload_zodiac_cache(steps=36, radius=270)
            else:  # planet_3d
                p_type = scene_visual.get("planet_type", detected_object)
                planet_cache = Engine3D.preload_3d_rotation_cache(planet_type=p_type, steps=36, radius=radius)

            # Capture scene start time for continuous motion
            scene_start = current_time_offset

            def make_scene_frame(t, start_time=scene_start, card=card_overlay, vtype=v_type):
                global_t = start_time + t
                frame = base_space.copy()

                if vtype == "gemstone_3d":
                    rot_speed = 1.0 / 6.0
                    f_idx = int((global_t * rot_speed) % 1.0 * len(gem_cache))
                    gem_frame = gem_cache[f_idx]
                    frame.paste(gem_frame, (0, 0), gem_frame)

                elif vtype == "kundli_chart_3d":
                    pulse_speed = 1.0 / 1.5
                    f_idx = int((global_t * pulse_speed) % 1.0 * len(kundli_cache))
                    k_frame = kundli_cache[f_idx]
                    frame.paste(k_frame, (0, 0), k_frame)

                elif vtype == "karmic_vortex_3d":
                    rot_speed = 1.0 / 4.0
                    f_idx = int((global_t * rot_speed) % 1.0 * len(vortex_cache))
                    v_frame = vortex_cache[f_idx]
                    frame.paste(v_frame, (0, 0), v_frame)

                elif vtype == "sacred_yantra_3d":
                    rot_speed = 1.0 / 6.0
                    f_idx = int((global_t * rot_speed) % 1.0 * len(yantra_cache))
                    y_frame = yantra_cache[f_idx]
                    frame.paste(y_frame, (0, 0), y_frame)

                elif vtype == "zodiac_wheel_3d":
                    rot_speed = 1.0 / 8.0
                    f_idx = int((global_t * rot_speed) % 1.0 * len(zodiac_cache))
                    z_frame = zodiac_cache[f_idx]
                    frame.paste(z_frame, (0, 0), z_frame)

                else:  # planet_3d
                    if back_rings:
                        frame = Image.alpha_composite(frame, back_rings)
                    rot_speed = 1.0 / 7.5
                    f_idx = int((global_t * rot_speed) % 1.0 * len(planet_cache))
                    p_img = planet_cache[f_idx]
                    frame.paste(p_img, (px, py), p_img)
                    frame.paste(front_overlay, (0, 0), front_overlay)
                    # Orbits & nodes
                    draw = ImageDraw.Draw(frame)
                    for orb in orbits:
                        rx, ry = orb["rx"], orb["ry"]
                        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=orb["color"], width=2)
                        angle = global_t * orb["speed"]
                        node_x = int(cx + rx * math.cos(angle))
                        node_y = int(cy + ry * math.sin(angle))
                        nr = 9
                        draw.ellipse([node_x - nr - 3, node_y - nr - 3, node_x + nr + 3, node_y + nr + 3], fill=orb["node_color"] + (100,))
                        draw.ellipse([node_x - nr, node_y - nr, node_x + nr, node_y + nr], fill=orb["node_color"] + (255,))
                        draw.line([(cx, cy), (node_x, node_y)], fill=orb["color"], width=1)

                # 4. Paste pre-computed scene text card
                frame.paste(card, (0, 0), card)

                return np.array(frame.convert("RGB"))

            scene_clip = VideoClip(make_scene_frame, duration=scene_dur)
            video_clips.append(scene_clip)

        else:
            # Generate 2D procedural background frame
            base_frame = generate_scene_frame(
                scene_index=idx,
                theme_name=theme_name,
                width=VIDEO_WIDTH,
                height=VIDEO_HEIGHT,
            )

            # Render overlay card & UI
            composed_image = render_scene_overlay(
                bg_image=base_frame,
                on_screen_text=screen_text,
                scene_number=scene_num,
                total_scenes=total_scenes,
                accent_color=accent,
                topic_badge=script_data.get("niche", "Vedic Astrology") if idx == 0 else None,
            )

            # Convert PIL Image to numpy array for MoviePy
            frame_np = np.array(composed_image)
            scene_clip = ImageClip(frame_np).with_duration(scene_dur)
            video_clips.append(scene_clip)

        current_time_offset += scene_dur

    # 4. Concatenate all scene clips
    final_video = concatenate_videoclips(video_clips, method="compose")

    # 5. Attach master voiceover audio
    final_video = final_video.with_audio(audio_clip)

    # 6. Determine output file path
    if not output_filename:
        safe_topic = re.sub(r"[^\w\-]", "_", topic[:20].lower()).strip("_")
        timestamp = int(time.time())
        output_filename = f"reel_{safe_topic}_{timestamp}.mp4"

    output_path = REELS_DIR / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Rendering final Reel video to {output_path}...")
    print(f"\n[VIDEO ENGINE] Rendering 1080x1920 Reel: {output_filename}...")

    # Export using optimized H.264 & AAC parameters for Instagram Reels (veryfast preset for speed & quality)
    final_video.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="veryfast",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-b:v", "4500k", "-b:a", "192k"],
        logger="bar",
    )

    # Close clips
    audio_clip.close()
    final_video.close()
    for c in video_clips:
        c.close()

    print(f"[VIDEO ENGINE] Successfully rendered Reel -> {output_path}")
    return output_path


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
