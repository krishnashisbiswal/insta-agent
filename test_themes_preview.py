import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DEFAULT_FONT_PATH, FALLBACK_FONT_PATH, IMPACT_FONT_PATH, VIDEO_HEIGHT, VIDEO_WIDTH


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    paths = [DEFAULT_FONT_PATH, IMPACT_FONT_PATH, FALLBACK_FONT_PATH] if bold else [FALLBACK_FONT_PATH, DEFAULT_FONT_PATH]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


# =====================================================================
# 1. 3D FACETED GEMSTONE ENGINE (Blue Sapphire, Pukhraj, Ruby, Emerald)
# =====================================================================
def render_3d_gemstone(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    t: float = 0.0,
    center: Tuple[int, int] = (VIDEO_WIDTH // 2, int(VIDEO_HEIGHT * 0.42)),
    radius: int = 240,
    gem_type: str = "blue_sapphire",
) -> Image.Image:
    """
    Renders an authentic 3D multi-faceted rotating crystal gemstone with
    specular reflections, prism dispersion, internal depth, and glowing aura.
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = center

    # Color definitions for various Vedic gemstones
    gem_palettes = {
        "blue_sapphire": {  # Neelam / Shani
            "base": (15, 45, 175),
            "mid": (35, 95, 235),
            "light": (120, 200, 255),
            "glint": (220, 245, 255),
            "glow": (30, 80, 255, 90),
            "aura_beams": (80, 140, 255, 120),
        },
        "yellow_sapphire": {  # Pukhraj / Guru
            "base": (180, 120, 10),
            "mid": (245, 185, 25),
            "light": (255, 230, 120),
            "glint": (255, 255, 220),
            "glow": (255, 190, 30, 90),
            "aura_beams": (255, 210, 60, 120),
        },
        "ruby": {  # Manik / Surya
            "base": (160, 15, 45),
            "mid": (230, 35, 75),
            "light": (255, 110, 150),
            "glint": (255, 220, 235),
            "glow": (255, 30, 70, 90),
            "aura_beams": (255, 70, 100, 120),
        },
        "emerald": {  # Panna / Budh
            "base": (10, 110, 60),
            "mid": (20, 190, 110),
            "light": (80, 245, 170),
            "glint": (210, 255, 235),
            "glow": (20, 230, 130, 90),
            "aura_beams": (40, 245, 150, 120),
        },
        "diamond": {  # Heera / Shukra
            "base": (130, 150, 190),
            "mid": (195, 215, 245),
            "light": (240, 250, 255),
            "glint": (255, 255, 255),
            "glow": (180, 220, 255, 90),
            "aura_beams": (200, 230, 255, 120),
        },
    }
    palette = gem_palettes.get(gem_type, gem_palettes["blue_sapphire"])

    # Geometry parameters
    # 8-sided brilliant crystal (table, crown facets, girdle, pavilion to culet)
    n_facets = 8
    r_table = radius * 0.52
    r_girdle = radius * 0.95
    h_table = -radius * 0.50
    h_girdle = -radius * 0.05
    h_culet = radius * 0.90

    # 3D Rotation matrices:
    # Rotate around Y axis by angle rot_y, tilt forward by rot_x
    rot_y = t * 1.2
    rot_x = math.radians(24.0 + 4.0 * math.sin(t * 1.5))  # Dynamic breathing tilt

    cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
    cos_x, sin_x = math.cos(rot_x), math.sin(rot_x)

    def transform_point(x, y, z):
        # Rotate around Y
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y
        # Tilt around X
        y2 = y * cos_x - z1 * sin_x
        z2 = y * sin_x + z1 * cos_x
        # Perspective projection
        fov = 1000.0
        scale = fov / (fov - z2)
        px = cx + x1 * scale
        py = cy + y2 * scale
        return (px, py, z2)

    # 1. Define 3D vertices
    # Table vertices (top octagon)
    table_pts = []
    for i in range(n_facets):
        ang = (2 * math.pi * i) / n_facets
        table_pts.append((r_table * math.cos(ang), h_table, r_table * math.sin(ang)))

    # Girdle upper vertices (16 points for high facet count)
    girdle_pts = []
    for i in range(n_facets * 2):
        ang = (2 * math.pi * i) / (n_facets * 2)
        girdle_pts.append((r_girdle * math.cos(ang), h_girdle, r_girdle * math.sin(ang)))

    # Culet vertex (bottom tip)
    culet_pt = (0.0, h_culet, 0.0)

    # Transform all vertices
    t_table = [transform_point(*p) for p in table_pts]
    t_girdle = [transform_point(*p) for p in girdle_pts]
    t_culet = transform_point(*culet_pt)

    # 2. Build list of 3D polygon facets
    # Each facet: list of (x, y, z) transformed vertices
    facets = []

    # Table polygon (8 vertices)
    facets.append({"pts": t_table, "type": "table"})

    # Crown triangles & kites connecting table to girdle
    for i in range(n_facets):
        i_next = (i + 1) % n_facets
        g_mid = i * 2 + 1
        g_left = i * 2
        g_right = (i * 2 + 2) % (n_facets * 2)

        # Star triangle
        facets.append({"pts": [t_table[i], t_table[i_next], t_girdle[g_mid]], "type": "crown_star"})
        # Kite left
        facets.append({"pts": [t_table[i], t_girdle[g_mid], t_girdle[g_left]], "type": "crown_kite"})
        # Kite right
        facets.append({"pts": [t_table[i_next], t_girdle[g_right], t_girdle[g_mid]], "type": "crown_kite"})

    # Pavilion facets connecting girdle to culet point
    for i in range(n_facets * 2):
        i_next = (i + 1) % (n_facets * 2)
        facets.append({"pts": [t_girdle[i], t_girdle[i_next], t_culet], "type": "pavilion"})

    # 3. Sort facets by average Z depth (Painter's algorithm: draw farthest first)
    def facet_depth(f):
        return sum(p[2] for p in f["pts"]) / len(f["pts"])

    facets.sort(key=facet_depth)

    # 4. Background aura & laser rays behind the gemstone
    # Radiating energetic aura beams
    for beam_idx in range(12):
        beam_ang = (2 * math.pi * beam_idx / 12) + (t * 0.6)
        beam_len = radius * 2.2 + 20 * math.sin(t * 3.0 + beam_idx)
        bx = cx + beam_len * math.cos(beam_ang)
        by = cy + beam_len * math.sin(beam_ang)
        draw.line([(cx, cy), (bx, by)], fill=palette["aura_beams"], width=2)

    # Ambient glow orb
    glow_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    gr = int(radius * 1.35)
    glow_draw.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=palette["glow"])
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(36))
    canvas = Image.alpha_composite(canvas, glow_img)
    draw = ImageDraw.Draw(canvas)

    # Light direction vector (normalized)
    lx, ly, lz = -0.5, -0.6, 0.8
    l_mag = math.sqrt(lx**2 + ly**2 + lz**2)
    lx, ly, lz = lx / l_mag, ly / l_mag, lz / l_mag

    # 5. Render shaded facets
    for f in facets:
        pts = f["pts"]
        if len(pts) < 3:
            continue

        # Normal vector via cross product of first two edges in 3D
        v0 = pts[0]
        v1 = pts[1]
        v2 = pts[2]

        ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
        bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]

        # Screen space cross product to check if facing front
        cross_z = ax * by - ay * bx
        # Back-face culling check or allow translucency
        is_front = cross_z < 0  # In screen coords with Y down

        # Normal vector in 3D
        nx = ay * bz - az * by
        ny = az * bx - ax * bz
        nz = ax * by - ay * bx
        n_mag = math.sqrt(nx**2 + ny**2 + nz**2)
        if n_mag > 0.001:
            nx, ny, nz = nx / n_mag, ny / n_mag, nz / n_mag
        else:
            nx, ny, nz = 0.0, 0.0, 1.0

        # Diffuse dot product
        diffuse = max(0.12, abs(nx * lx + ny * ly + nz * lz))
        # Specular reflection dot product
        # View vector is (0, 0, 1)
        # R = 2*(N.L)*N - L
        dot_nl = nx * lx + ny * ly + nz * lz
        rx = 2 * dot_nl * nx - lx
        ry = 2 * dot_nl * ny - ly
        rz = 2 * dot_nl * nz - lz
        specular = max(0.0, rz) ** 14

        # Compute facet color
        base_c = palette["base"]
        mid_c = palette["mid"]
        glint_c = palette["glint"]

        # Alpha: front facets more opaque, back facets translucent
        alpha = 240 if is_front else 110

        r_col = int(min(255, base_c[0] * (1 - diffuse) + mid_c[0] * diffuse + glint_c[0] * specular * 1.2))
        g_col = int(min(255, base_c[1] * (1 - diffuse) + mid_c[1] * diffuse + glint_c[1] * specular * 1.2))
        b_col = int(min(255, base_c[2] * (1 - diffuse) + mid_c[2] * diffuse + glint_c[2] * specular * 1.2))

        polygon_2d = [(p[0], p[1]) for p in pts]
        draw.polygon(polygon_2d, fill=(r_col, g_col, b_col, alpha))

        # Edge lines: crisp crystalline facets
        edge_alpha = 255 if is_front else 120
        edge_col = (
            min(255, r_col + 50),
            min(255, g_col + 50),
            min(255, b_col + 50),
            edge_alpha,
        )
        draw.line(polygon_2d + [polygon_2d[0]], fill=edge_col, width=2)

    # 6. Sparkle glint star on top vertex when aligned with light
    glint_time = (t * 2.5) % (math.pi * 2)
    if math.sin(glint_time) > 0.8:
        # Pick prominent top vertex
        gp = t_table[0]
        gx, gy = gp[0], gp[1]
        g_size = int(18 + 12 * math.sin(glint_time * 4))
        # 4-pointed diamond glint
        draw.polygon([(gx, gy - g_size), (gx + 3, gy), (gx, gy + g_size), (gx - 3, gy)], fill=(255, 255, 255, 240))
        draw.polygon([(gx - g_size, gy), (gx, gy + 3), (gx + g_size, gy), (gx, gy - 3)], fill=(255, 255, 255, 240))
        draw.ellipse([gx - 4, gy - 4, gx + 4, gy + 4], fill=(255, 255, 255, 255))

    return canvas


# =====================================================================
# 2. 3D VEDIC KUNDALI 12-HOUSE BIRTH CHART ENGINE
# =====================================================================
def render_3d_kundli_chart(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    t: float = 0.0,
    center: Tuple[int, int] = (VIDEO_WIDTH // 2, int(VIDEO_HEIGHT * 0.42)),
    size: int = 480,
    highlight_house: int = 8,
    house_warning_label: str = "8TH HOUSE KARMA",
) -> Image.Image:
    """
    Renders an authentic traditional North Indian Vedic Kundali diamond chart
    with glowing gold sacred grid lines, Sanskrit symbols, 12 houses (bhavas),
    and an electric pulsing warning aura around the specific house (e.g. 8th House).
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cx, cy = center

    # 3D floating perspective tilt: chart floats and bobs gently in cosmic space
    bob_y = math.sin(t * 1.8) * 12
    tilt_rad = math.radians(16.0 + 3.0 * math.cos(t * 1.2))

    # Render base on a localized square image
    chart_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(chart_img)

    s = size
    half = s / 2.0
    pad = 16

    # 1. Background dark cosmic plate
    draw.rectangle([pad, pad, s - pad, s - pad], fill=(12, 10, 24, 210), outline=(212, 175, 55, 220), width=3)

    # 2. Kundli standard geometric diamond & diagonal coordinates
    p_tl = (pad, pad)
    p_tr = (s - pad, pad)
    p_br = (s - pad, s - pad)
    p_bl = (pad, s - pad)

    p_tm = (half, pad)
    p_rm = (s - pad, half)
    p_bm = (half, s - pad)
    p_lm = (pad, half)

    p_center = (half, half)

    # Outer diagonals
    draw.line([p_tl, p_br], fill=(212, 175, 55, 200), width=2)
    draw.line([p_tr, p_bl], fill=(212, 175, 55, 200), width=2)

    # Inner diamond connecting midpoints
    draw.line([p_tm, p_rm, p_bm, p_lm, p_tm], fill=(212, 175, 55, 240), width=3)

    # 3. House polygons mapping in North Indian Vedic system:
    # House 1 (Lagna / Tanu): Top center diamond [p_center, p_tm, etc] -> [half, pad] to center
    # House 2: Top left outer triangle [p_tl, p_tm, (p_tl+p_tm)/2 ...]
    # House 8: Lower right / bottom-right house (Randhra Bhava: transformation, secrets, death & karma)
    house_polygons = {
        1: [p_center, (pad + half) / 2, (pad + half) / 2],  # simplified coordinates
        8: [p_center, p_bm, p_br],  # 8th house quadrant
        6: [p_bl, p_lm, p_center],  # 6th house (debts/enemies)
        12: [p_tr, p_tm, p_center],  # 12th house (losses/moksha)
    }

    # Specifically highlight House 8 (or whichever is requested)
    pulse = 0.5 + 0.5 * math.sin(t * 4.5)  # Fast warning pulse
    warn_color = (
        int(235 + 20 * pulse),
        int(40 + 20 * pulse),
        int(40),
        int(140 + 80 * pulse),
    )

    # House 8 polygon in North Indian Kundali:
    # Bottom right inner diamond flank
    h8_pts = [p_center, p_bm, p_rm]
    draw.polygon(h8_pts, fill=warn_color)
    draw.line(h8_pts + [p_center], fill=(255, 60, 60, 255), width=3)

    # Label font
    f_num = get_font(26, bold=True)
    f_badge = get_font(22, bold=True)

    # Draw House Numbers & Sanskrit Glyphs
    # House 1 (Lagna)
    draw.text((half - 10, half - 70), "1", font=f_num, fill=(255, 215, 0, 230))
    # House 8 (Highlighted Danger)
    h8_center_x = (half + s - pad) / 2 - 12
    h8_center_y = (half + s - pad) / 2 + 10
    draw.text((h8_center_x - 10, h8_center_y - 20), "8", font=f_num, fill=(255, 255, 255, 255))
    draw.text((h8_center_x - 30, h8_center_y + 10), "⚠️ KARMA", font=f_badge, fill=(255, 230, 0, 255))

    # Corner Vedic accents
    draw.text((pad + 12, pad + 10), "ॐ", font=get_font(28, bold=True), fill=(255, 215, 0, 200))
    draw.text((s - pad - 36, pad + 10), "卐", font=get_font(26, bold=True), fill=(255, 215, 0, 200))

    # 4. Apply 3D Perspective Transform to canvas
    # Warp 2D chart onto tilted 3D plane
    chart_np = np.array(chart_img)
    # Tilted 3D perspective mapping using affine / mesh
    # Pillow allows perspective transform with quad transform
    # Quad: [TL, BL, BR, TR]
    dx = int(math.sin(tilt_rad) * 60)
    dy = int(math.cos(tilt_rad) * size * 0.82)
    quad = [
        dx,
        0,  # Top Left
        0,
        dy,  # Bottom Left
        size,
        dy,  # Bottom Right
        size - dx,
        0,  # Top Right
    ]
    tilted_chart = chart_img.transform(
        (size, int(dy)),
        Image.Transform.QUAD,
        quad,
        resample=Image.Resampling.BICUBIC,
    )

    # Paste at center with floating bob
    paste_x = cx - size // 2
    paste_y = int(cy - dy // 2 + bob_y)

    # Aura glow behind chart
    glow_chart = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_chart)
    glow_draw.ellipse(
        [cx - size // 2 - 40, cy - dy // 2 - 30, cx + size // 2 + 40, cy + dy // 2 + 30],
        fill=(180, 40, 255, 80),
    )
    glow_chart = glow_chart.filter(ImageFilter.GaussianBlur(32))
    canvas = Image.alpha_composite(canvas, glow_chart)

    canvas.paste(tilted_chart, (paste_x, paste_y), tilted_chart)
    return canvas


# =====================================================================
# 3. 3D SACRED SRI YANTRA / DIVINE DEVOTIONAL MANDALA
# =====================================================================
def render_3d_sacred_yantra(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    t: float = 0.0,
    center: Tuple[int, int] = (VIDEO_WIDTH // 2, int(VIDEO_HEIGHT * 0.42)),
    radius: int = 260,
) -> Image.Image:
    """
    Renders the sacred 3D Sri Yantra mandala with interlocking golden triangles,
    concentric lotus circles, and divine radiating spiritual particle rays.
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cx, cy = center

    # Golden spiritual particle beams radiating from Bindu
    draw = ImageDraw.Draw(canvas)
    for i in range(16):
        ang = (2 * math.pi * i / 16) + (t * 0.3)
        b_len = radius * 1.8 + 15 * math.sin(t * 2.0 + i)
        bx = cx + b_len * math.cos(ang)
        by = cy + b_len * math.sin(ang)
        draw.line([(cx, cy), (bx, by)], fill=(255, 215, 0, 60), width=2)

    # Concentric sacred circles (Trivritta)
    for r_mult in [1.0, 0.92, 0.84]:
        r = int(radius * r_mult)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 215, 0, 180), width=2)

    # 16-petaled outer lotus ring (concentric breathing)
    n_petals = 16
    rot_lotus = t * 0.2
    for i in range(n_petals):
        ang = (2 * math.pi * i / n_petals) + rot_lotus
        pr = radius * 0.92
        px = cx + pr * math.cos(ang)
        py = cy + pr * math.sin(ang)
        draw.ellipse([px - 14, py - 14, px + 14, py + 14], outline=(255, 223, 100, 140), width=2)

    # 9 Interlocking Sri Yantra Triangles (4 pointing UP Shiva, 5 pointing DOWN Shakti)
    # Slow harmonic counter-rotation
    shiva_rot = t * 0.4
    shakti_rot = -t * 0.4

    # 4 Shiva Triangles (Pointing UP)
    up_triangles = [
        {"r": radius * 0.72, "w_mult": 1.15, "y_off": 15},
        {"r": radius * 0.58, "w_mult": 1.10, "y_off": 25},
        {"r": radius * 0.44, "w_mult": 1.05, "y_off": 30},
        {"r": radius * 0.30, "w_mult": 1.00, "y_off": 35},
    ]
    for tri in up_triangles:
        r = tri["r"]
        w_m = tri["w_mult"]
        y_o = tri["y_off"]
        p_top = (cx, cy - r + y_o)
        p_bl = (cx - r * w_m * 0.866, cy + r * 0.5 + y_o)
        p_br = (cx + r * w_m * 0.866, cy + r * 0.5 + y_o)
        draw.polygon([p_top, p_bl, p_br], outline=(255, 215, 0, 220), width=2)

    # 5 Shakti Triangles (Pointing DOWN)
    down_triangles = [
        {"r": radius * 0.78, "w_mult": 1.18, "y_off": -15},
        {"r": radius * 0.65, "w_mult": 1.12, "y_off": -22},
        {"r": radius * 0.52, "w_mult": 1.08, "y_off": -28},
        {"r": radius * 0.38, "w_mult": 1.02, "y_off": -32},
        {"r": radius * 0.24, "w_mult": 0.98, "y_off": -36},
    ]
    for tri in down_triangles:
        r = tri["r"]
        w_m = tri["w_mult"]
        y_o = tri["y_off"]
        p_bot = (cx, cy + r + y_o)
        p_tl = (cx - r * w_m * 0.866, cy - r * 0.5 + y_o)
        p_tr = (cx + r * w_m * 0.866, cy - r * 0.5 + y_o)
        draw.polygon([p_bot, p_tl, p_tr], outline=(255, 180, 50, 220), width=2)

    # Central Bindu (Divine origin point)
    bindu_r = int(12 + 4 * math.sin(t * 5.0))
    draw.ellipse([cx - bindu_r, cy - bindu_r, cx + bindu_r, cy + bindu_r], fill=(255, 255, 220, 255))
    draw.ellipse([cx - bindu_r - 6, cy - bindu_r - 6, cx + bindu_r + 6, cy + bindu_r + 6], outline=(255, 215, 0, 160), width=2)

    return canvas


# =====================================================================
# 4. 3D ROTATING ZODIAC KALPURUSHA WHEEL
# =====================================================================
def render_3d_zodiac_wheel(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    t: float = 0.0,
    center: Tuple[int, int] = (VIDEO_WIDTH // 2, int(VIDEO_HEIGHT * 0.42)),
    radius: int = 270,
) -> Image.Image:
    """
    Renders a 3D tilted rotating Kalpurusha Zodiac Wheel with 12 Rashi divisions,
    golden astrological glyphs, constellation nodes, and radiant planetary beams.
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cx, cy = center
    draw = ImageDraw.Draw(canvas)

    zodiac_signs = [
        ("ARIES", "♈"),
        ("TAURUS", "♉"),
        ("GEMINI", "♊"),
        ("CANCER", "♋"),
        ("LEO", "♌"),
        ("VIRGO", "♍"),
        ("LIBRA", "♎"),
        ("SCORPIO", "♏"),
        ("SAGITTARIUS", "♐"),
        ("CAPRICORN", "♑"),
        ("AQUARIUS", "♒"),
        ("PISCES", "♓"),
    ]

    # 3D Tilt parameters: tilted astrological dial
    tilt_rad = math.radians(35.0)
    rot_speed = t * 0.4

    # Concentric golden tracks
    r_outer = radius
    r_inner = int(radius * 0.72)
    ry_outer = int(r_outer * math.cos(tilt_rad))
    ry_inner = int(r_inner * math.cos(tilt_rad))

    draw.ellipse([cx - r_outer, cy - ry_outer, cx + r_outer, cy + ry_outer], outline=(255, 215, 0, 220), width=3)
    draw.ellipse([cx - r_inner, cy - ry_inner, cx + r_inner, cy + ry_inner], outline=(255, 215, 0, 180), width=2)

    # 12 Rashi sectors
    font_glyph = get_font(30, bold=True)
    font_sign = get_font(18, bold=True)

    for i, (name, glyph) in enumerate(zodiac_signs):
        angle = (2 * math.pi * i / 12) + rot_speed

        # 3D projected coordinates on tilted ellipse
        px_out = cx + r_outer * math.cos(angle)
        py_out = cy + ry_outer * math.sin(angle)

        px_in = cx + r_inner * math.cos(angle)
        py_in = cy + ry_inner * math.sin(angle)

        # Sector boundary line
        draw.line([(px_in, py_in), (px_out, py_out)], fill=(255, 215, 0, 140), width=2)

        # Midpoint for glyph
        mid_ang = angle + (math.pi / 12)
        r_mid = (r_outer + r_inner) / 2.0
        ry_mid = (ry_outer + ry_inner) / 2.0
        gx = cx + r_mid * math.cos(mid_ang)
        gy = cy + ry_mid * math.sin(mid_ang)

        # Active sign illumination if in front (sin > 0)
        is_front = math.sin(mid_ang) > 0.0
        g_alpha = 255 if is_front else 110
        g_col = (255, 230, 80, g_alpha) if is_front else (180, 180, 190, g_alpha)

        draw.text((gx - 12, gy - 16), glyph, font=font_glyph, fill=g_col)

    # Center cosmic jewel / sun
    cr = 30
    draw.ellipse([cx - cr, cy - int(cr * math.cos(tilt_rad)), cx + cr, cy + int(cr * math.cos(tilt_rad))], fill=(255, 215, 50, 240))
    return canvas


# =====================================================================
# 5. 3D KARMIC COSMIC VORTEX / ECLIPSE WORMHOLE (Rahu / Ketu / Karma)
# =====================================================================
def render_3d_karmic_vortex(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    t: float = 0.0,
    center: Tuple[int, int] = (VIDEO_WIDTH // 2, int(VIDEO_HEIGHT * 0.42)),
    radius: int = 280,
) -> Image.Image:
    """
    Renders an intense, swirling 3D cosmic karmic black hole / shadow vortex
    with logarithmic particle spirals, relativistic accretion disk, and violet flares.
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cx, cy = center
    draw = ImageDraw.Draw(canvas)

    # Logarithmic spiral arms
    n_arms = 4
    for arm in range(n_arms):
        arm_base_ang = (2 * math.pi * arm / n_arms) - (t * 1.8)
        pts = []
        for step in range(25):
            frac = step / 25.0
            r = radius * frac
            ang = arm_base_ang + (frac * 3.5)
            x = cx + r * math.cos(ang)
            y = cy + int(r * 0.65 * math.sin(ang))  # tilted perspective
            pts.append((x, y))

        for j in range(len(pts) - 1):
            alpha = int(220 * (j / len(pts)))
            col = (180, 30, 255, alpha) if arm % 2 == 0 else (255, 50, 80, alpha)
            draw.line([pts[j], pts[j + 1]], fill=col, width=int(2 + 4 * (j / len(pts))))

    # Blinding Event Horizon Accretion Disk (glowing ellipse)
    for r_disk in range(int(radius * 0.6), int(radius * 0.15), -4):
        alpha = int(90 * (1.0 - (r_disk / (radius * 0.6))))
        draw.ellipse([cx - r_disk, cy - int(r_disk * 0.45), cx + r_disk, cy + int(r_disk * 0.45)], fill=(140, 20, 255, alpha))

    # Black hole shadow core
    bh_r = int(radius * 0.22)
    draw.ellipse([cx - bh_r, cy - int(bh_r * 0.45), cx + bh_r, cy + int(bh_r * 0.45)], fill=(0, 0, 0, 255), outline=(255, 80, 200, 220), width=2)
    return canvas


# =====================================================================
# TEST HARNESS: GENERATE PREVIEWS FOR ALL 5 THEMES
# =====================================================================
if __name__ == "__main__":
    out_dir = PROJECT_ROOT / "insta content" / "3d_previews"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generating 3D Theme Previews...")

    themes = [
        ("gemstone_neelam", lambda: render_3d_gemstone(t=1.5, gem_type="blue_sapphire")),
        ("kundli_8th_house", lambda: render_3d_kundli_chart(t=1.2, highlight_house=8)),
        ("sacred_yantra", lambda: render_3d_sacred_yantra(t=2.0)),
        ("zodiac_wheel", lambda: render_3d_zodiac_wheel(t=1.0)),
        ("karmic_vortex", lambda: render_3d_karmic_vortex(t=2.5)),
    ]

    for name, gen_fn in themes:
        # Create dark space base
        base = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (6, 4, 16, 255))
        theme_layer = gen_fn()
        final_img = Image.alpha_composite(base, theme_layer)

        dest = out_dir / f"preview_{name}.jpg"
        final_img.convert("RGB").save(dest, quality=92)
        print(f" -> Saved: {dest}")

    print("\nAll 5 Theme Previews successfully generated!")
