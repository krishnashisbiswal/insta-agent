import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    FRAMES_DIR,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)
from PIL import Image, ImageDraw, ImageFilter

THEMES = {
    "cosmic": {
        "bg_top": (8, 5, 22),
        "bg_mid": (22, 10, 50),
        "bg_bot": (4, 2, 12),
        "accent": (255, 215, 0),
        "glow": (130, 60, 210),
        "stars": True,
        "rings": True,
    },
    "dark_gold": {
        "bg_top": (18, 14, 8),
        "bg_mid": (38, 28, 12),
        "bg_bot": (10, 8, 4),
        "accent": (234, 179, 8),
        "glow": (161, 98, 7),
        "stars": False,
        "rings": True,
    },
    "neon_cyber": {
        "bg_top": (10, 15, 30),
        "bg_mid": (15, 23, 42),
        "bg_bot": (6, 9, 18),
        "accent": (6, 182, 212),
        "glow": (14, 116, 144),
        "stars": True,
        "rings": False,
    },
    "crimson_fire": {
        "bg_top": (25, 6, 6),
        "bg_mid": (45, 12, 12),
        "bg_bot": (12, 2, 2),
        "accent": (239, 68, 68),
        "glow": (185, 28, 28),
        "stars": True,
        "rings": True,
    },
    "minimalist_dark": {
        "bg_top": (18, 18, 22),
        "bg_mid": (28, 28, 34),
        "bg_bot": (10, 10, 12),
        "accent": (244, 244, 245),
        "glow": (63, 63, 70),
        "stars": False,
        "rings": False,
    },
}


def create_vertical_gradient(
    width: int,
    height: int,
    top_color: Tuple[int, int, int],
    mid_color: Tuple[int, int, int],
    bot_color: Tuple[int, int, int],
) -> Image.Image:
    """Create a smooth 3-stop vertical gradient background."""
    base = Image.new("RGB", (width, height), top_color)
    draw = ImageDraw.Draw(base)

    half = height // 2
    for y in range(height):
        if y < half:
            factor = y / half
            r = int(top_color[0] + (mid_color[0] - top_color[0]) * factor)
            g = int(top_color[1] + (mid_color[1] - top_color[1]) * factor)
            b = int(top_color[2] + (mid_color[2] - top_color[2]) * factor)
        else:
            factor = (y - half) / half
            r = int(mid_color[0] + (bot_color[0] - mid_color[0]) * factor)
            g = int(mid_color[1] + (bot_color[1] - mid_color[1]) * factor)
            b = int(mid_color[2] + (bot_color[2] - mid_color[2]) * factor)

        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return base


def add_ambient_glow(
    img: Image.Image,
    center_y: int,
    glow_color: Tuple[int, int, int],
    radius: int = 400,
    alpha: int = 120,
) -> Image.Image:
    """Add a luminous radial spotlight in center/focal zone to make text pop."""
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)

    center_x = img.width // 2

    # Draw radial gradient circles
    for r in range(radius, 0, -8):
        current_alpha = int(alpha * (1 - (r / radius) ** 1.5))
        color = glow_color + (max(0, min(255, current_alpha)),)
        draw.ellipse(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            fill=color,
        )

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(30))
    img_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(img_rgba, glow_layer)
    return composite.convert("RGB")


def add_geometric_rings(
    img: Image.Image,
    center_y: int,
    color: Tuple[int, int, int],
    scene_index: int = 0,
) -> Image.Image:
    """Add aesthetic cosmic/astrological orbit rings & subtle geometric elements."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    center_x = img.width // 2

    ring_color = color + (40,)
    bright_color = color + (90,)

    # Outer decorative rings
    radii = [280, 360, 440, 520]
    for i, r in enumerate(radii):
        c = bright_color if (i + scene_index) % 2 == 0 else ring_color
        draw.ellipse(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            outline=c,
            width=2,
        )

    # Planetary orbit arc
    arc_offset = (scene_index * 35) % 360
    draw.arc(
        [center_x - 480, center_y - 250, center_x + 480, center_y + 250],
        start=arc_offset,
        end=arc_offset + 140,
        fill=color + (130,),
        width=3,
    )

    # Accent dots along circle
    for angle_deg in range(0, 360, 45):
        rad = math.radians(angle_deg + arc_offset)
        px = int(center_x + 360 * math.cos(rad))
        py = int(center_y + 360 * math.sin(rad))
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=color + (180,))

    img_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(img_rgba, overlay)
    return composite.convert("RGB")


def add_starfield(
    img: Image.Image,
    seed: int = 42,
    count: int = 150,
) -> Image.Image:
    """Add random twinkling starlight dust to background."""
    rng = random.Random(seed)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for _ in range(count):
        x = rng.randint(0, img.width)
        y = rng.randint(0, img.height)
        size = rng.choice([1, 1, 2, 2, 3])
        opacity = rng.randint(60, 220)
        draw.ellipse([x, y, x + size, y + size], fill=(255, 255, 255, opacity))

    img_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(img_rgba, overlay)
    return composite.convert("RGB")


def generate_scene_frame(
    scene_index: int,
    theme_name: str = "cosmic",
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    output_path: Optional[Path] = None,
) -> Image.Image:
    """
    Generate a 1080x1920 high-aesthetic scene background frame.
    """
    theme = THEMES.get(theme_name, THEMES["cosmic"])

    # 1. Base vertical gradient
    frame = create_vertical_gradient(
        width=width,
        height=height,
        top_color=theme["bg_top"],
        mid_color=theme["bg_mid"],
        bot_color=theme["bg_bot"],
    )

    # 2. Ambient focal glow
    focus_y = int(height * 0.45)
    frame = add_ambient_glow(
        frame,
        center_y=focus_y,
        glow_color=theme["glow"],
        radius=480,
        alpha=130,
    )

    # 3. Geometric orbit rings
    if theme.get("rings", True):
        frame = add_geometric_rings(
            frame,
            center_y=focus_y,
            color=theme["accent"],
            scene_index=scene_index,
        )

    # 4. Starfield particles
    if theme.get("stars", True):
        frame = add_starfield(
            frame,
            seed=1000 + scene_index * 97,
            count=180,
        )

    # Save to disk if requested
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.save(output_path, "JPEG", quality=95)

    return frame


def generate_all_scene_frames(
    scenes: List[Dict[str, Any]],
    theme_name: str = "cosmic",
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Generate distinct background visual frames for all scenes of a Reel.
    """
    target_dir = output_dir or FRAMES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for idx, sc in enumerate(scenes):
        frame_file = target_dir / f"scene_{idx + 1:02d}.jpg"
        generate_scene_frame(
            scene_index=idx,
            theme_name=theme_name,
            output_path=frame_file,
        )
        saved_paths.append(frame_file)

    return saved_paths


if __name__ == "__main__":
    print("Testing Visual Generator...")
    test_scenes = [{"scene": 1}, {"scene": 2}, {"scene": 3}]
    paths = generate_all_scene_frames(test_scenes, theme_name="cosmic")
    print(f"Generated {len(paths)} scene frames:")
    for p in paths:
        print(" -", p)
