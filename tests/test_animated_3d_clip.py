import math
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from moviepy import VideoClip
from app.video.engine_3d import Engine3D

print("Testing Dynamic 3D Frame Generator...")

# 1. Preload 60-step smooth 3D rotation bank
planet_type = "saturn"
steps = 60
radius = 240
print(f"Pre-rendering {steps} rotation steps for '{planet_type}'...")
t0 = time.time()
cache = Engine3D.preload_3d_rotation_cache(planet_type=planet_type, steps=steps, radius=radius)
print(f"Preloaded in {time.time() - t0:.2f}s!")

# 2. Pre-render static base layers: space background and rings
width, height = 1080, 1920
cx, cy = width // 2, int(height * 0.42)
px, py = cx - radius, cy - radius

base_space = Engine3D.create_space_backdrop(width, height, t=0.0)

back_rings = Engine3D.render_saturn_rings(
    outer_width=width,
    outer_height=height,
    tilt_deg=26.0,
    inner_r=int(radius * 1.25),
    outer_r=int(radius * 2.1),
    center=(cx, cy),
    back_only=True,
)

front_rings = Engine3D.render_saturn_rings(
    outer_width=width,
    outer_height=height,
    tilt_deg=26.0,
    inner_r=int(radius * 1.25),
    outer_r=int(radius * 2.1),
    center=(cx, cy),
    front_only=True,
)

glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_layer)
glow_draw.ellipse(
    [px - 14, py - 14, px + radius * 2 + 14, py + radius * 2 + 14],
    outline=(180, 140, 255, 90),
    width=10,
)
glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(16))

# Pre-composite the background behind planet
bg_with_back_rings = Image.alpha_composite(base_space, back_rings)
front_overlay = Image.alpha_composite(glow_layer, front_rings)

# Card overlay on transparent RGBA
from app.video.video_composer import render_scene_overlay
empty_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
card_with_bg = render_scene_overlay(
    bg_image=empty_canvas.convert("RGB"),
    on_screen_text="⚠️ NEVER WEAR NEELAM!",
    scene_number=1,
    total_scenes=5,
    accent_color=(255, 215, 0),
)

def make_dynamic_frame(t: float) -> np.ndarray:
    """Render a fully animated frame at timestamp t."""
    frame = bg_with_back_rings.copy()

    # 1. Rotating 3D Sphere (Full 360 deg rotation every 6 seconds)
    rot_speed = 1.0 / 6.0
    frame_idx = int((t * rot_speed) % 1.0 * steps)
    planet_img = cache[frame_idx]
    frame.paste(planet_img, (px, py), planet_img)

    # 2. Front overlay (atmosphere glow + front rings)
    frame.paste(front_overlay, (0, 0), front_overlay)

    # 3. Dynamic Orbit Tracks with moving planetary nodes
    draw = ImageDraw.Draw(frame)
    orbits = [
        {"rx": 360, "ry": 160, "color": (255, 215, 0, 110), "speed": 1.2, "node_color": (255, 215, 0)},
        {"rx": 450, "ry": 200, "color": (147, 92, 255, 90), "speed": -0.8, "node_color": (230, 180, 255)},
        {"rx": 530, "ry": 235, "color": (239, 68, 68, 80), "speed": 0.6, "node_color": (255, 100, 100)},
    ]
    for orb in orbits:
        rx, ry = orb["rx"], orb["ry"]
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=orb["color"], width=2)
        angle = t * orb["speed"]
        node_x = int(cx + rx * math.cos(angle))
        node_y = int(cy + ry * math.sin(angle))
        nr = 9
        draw.ellipse([node_x - nr - 3, node_y - nr - 3, node_x + nr + 3, node_y + nr + 3], fill=orb["node_color"] + (100,))
        draw.ellipse([node_x - nr, node_y - nr, node_x + nr, node_y + nr], fill=orb["node_color"] + (255,))
        draw.line([(cx, cy), (node_x, node_y)], fill=orb["color"], width=1)

    # 4. Render text card overlay on top of frame
    final_frame = render_scene_overlay(
        bg_image=frame.convert("RGB"),
        on_screen_text="⚠️ NEVER WEAR NEELAM!",
        scene_number=1,
        total_scenes=5,
        accent_color=(255, 215, 0),
    )

    return np.array(final_frame)

print("\nComposing 3-second animated VideoClip...")
t_start = time.time()
clip = VideoClip(make_dynamic_frame, duration=3.0)
out_test = PROJECT_ROOT / "output" / "test_motion_reel.mp4"
clip.write_videofile(
    str(out_test),
    fps=30,
    codec="libx264",
    preset="ultrafast",
    logger=None,
)
print(f"Rendered 3-second 90-frame 3D ANIMATED Video in {time.time() - t_start:.2f}s -> {out_test} (Size: {out_test.stat().st_size} bytes)")
