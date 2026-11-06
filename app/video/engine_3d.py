import math
import random
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

from config.settings import DEFAULT_FONT_PATH, FALLBACK_FONT_PATH, IMPACT_FONT_PATH, VIDEO_HEIGHT, VIDEO_WIDTH


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


class Engine3D:
    """
    Procedural 3D Astronomical & Spatial Rendering Engine for Python.
    Renders 3D rotating shaded spheres, inclined ring systems, orbital tracks,
    and celestial depth without needing external 3D software or Blender.
    Supports all 9 Vedic Grahas + Earth, plus 3D objects for Crypto, Tech, Health & Mindset!
    """

    @classmethod
    def detect_3d_object_type(cls, topic: str = "", niche: str = "") -> str:
        """
        Intelligently select the 3D procedural object based on topic keywords and niche.
        Supports all 9 Vedic Grahas + Earth, plus objects for Crypto, Tech, Biology, Mindset!
        """
        combined = f" {topic} {niche} ".lower()

        def contains_any(keywords):
            for k in keywords:
                pattern = r"\b" + re.escape(k) + r"\b"
                if re.search(pattern, combined):
                    return True
            return False

        # 1. Non-astrology niches first if explicitly specified in niche
        niche_lower = niche.lower()
        if any(k in niche_lower for k in ["crypto", "bitcoin", "finance", "money", "wealth", "investing", "trading", "stock"]):
            return "crypto_coin"
        if any(k in niche_lower for k in ["science", "biology", "dna", "fitness", "health", "workout", "biohack", "longevity"]):
            return "dna_helix"
        if any(k in niche_lower for k in ["ai", "tech", "coding", "software", "developer", "cyber", "machine learning"]):
            return "cyber_core"
        if any(k in niche_lower for k in ["mindset", "psychology", "motivation", "stoic", "discipline"]):
            return "prism_orb"

        # 2. Topic keywords for specific Vedic Astrological Bodies
        if contains_any(["saturn", "shani", "sade sati", "dhaiya", "neelam", "blue sapphire", "karma", "capricorn", "aquarius", "makar", "kumbh"]):
            return "saturn"
        if contains_any(["jupiter", "guru", "brihaspati", "pukhraj", "yellow sapphire", "sagittarius", "pisces", "dhanu", "meen"]):
            return "jupiter"
        if contains_any(["mars", "mangal", "manglik", "angarak", "coral", "moonga", "aries", "scorpio", "mesh", "vrishchik"]):
            return "mars"
        if contains_any(["sun", "surya", "aditya", "father", "authority", "ruby", "manik", "leo", "simha", "atmakaraka"]):
            return "sun"
        if contains_any(["moon", "chandra", "soma", "mind", "pearl", "moti", "mother", "cancer", "kark", "anxiety", "nakshatra"]):
            return "moon"
        if contains_any(["venus", "shukra", "luxury", "diamond", "heera", "taurus", "libra", "vrishabh", "tula", "romance", "marriage"]):
            return "venus"
        if contains_any(["mercury", "budh", "intellect", "emerald", "panna", "gemini", "virgo", "mithun", "kanya", "communication"]):
            return "mercury"
        if contains_any(["rahu", "north node", "eclipse", "illusion", "obsession", "maya", "gomed", "hessonite", "kal sarp"]):
            return "rahu"
        if contains_any(["ketu", "south node", "detachment", "moksha", "cat's eye", "cats eye", "lehsunia"]):
            return "ketu"

        # 3. Topic keywords for Modern Niches (when niche is generic or topic has clear cue)
        if contains_any(["crypto", "bitcoin", "btc", "eth", "ethereum", "web3", "defi", "trading", "stock", "investing", "finance", "money", "wealth", "rich", "passive income"]):
            return "crypto_coin"
        if contains_any(["science", "biology", "dna", "genetics", "health", "fitness", "body", "muscle", "workout", "nutrition", "medicine", "biohack", "longevity"]):
            return "dna_helix"
        if contains_any(["ai", "artificial intelligence", "tech", "coding", "software", "developer", "robot", "cyber", "machine learning", "cloud", "algorithm", "python"]):
            return "cyber_core"
        if contains_any(["mindset", "psychology", "motivation", "success", "discipline", "habits", "focus", "stoic", "stoicism"]):
            return "prism_orb"

        # 4. General Astrology / Zodiac
        if contains_any(["astrology", "vedic", "kundli", "horoscope", "zodiac", "rashi", "planet", "graha"]):
            return "earth"

        return "saturn"

    @staticmethod
    def create_space_backdrop(width: int, height: int, t: float = 0.0, style: str = "space") -> Image.Image:
        """Render a deep celestial space background with subtle multi-layer star parallax or theme style."""
        if style == "crypto":
            # Dark obsidian luxury background with floating gold bokeh
            base = Image.new("RGBA", (width, height), (10, 8, 12, 255))
            draw = ImageDraw.Draw(base)
            glow_center = (width // 2, int(height * 0.42))
            for r in range(400, 0, -20):
                alpha = int(35 * (1 - (r / 400) ** 1.8))
                draw.ellipse([glow_center[0] - r, glow_center[1] - r, glow_center[0] + r, glow_center[1] + r], fill=(160, 120, 20, alpha))
            rng = random.Random(42)
            for _ in range(70):
                sx = rng.randint(0, width)
                sy = (rng.randint(0, height) + int(t * 12)) % height
                s_sz = rng.randint(2, 5)
                draw.ellipse([sx, sy, sx + s_sz, sy + s_sz], fill=(255, 215, 80, rng.randint(80, 200)))
            return base

        elif style == "cyber":
            # Dark slate background with digital cyan glow and matrix grid
            base = Image.new("RGBA", (width, height), (6, 10, 18, 255))
            draw = ImageDraw.Draw(base)
            glow_center = (width // 2, int(height * 0.42))
            for r in range(420, 0, -20):
                alpha = int(40 * (1 - (r / 420) ** 1.8))
                draw.ellipse([glow_center[0] - r, glow_center[1] - r, glow_center[0] + r, glow_center[1] + r], fill=(0, 140, 200, alpha))
            rng = random.Random(77)
            for _ in range(60):
                sx = rng.randint(0, width)
                sy = (rng.randint(0, height) + int(t * 18)) % height
                draw.rectangle([sx, sy, sx + 2, sy + rng.randint(4, 10)], fill=(0, 255, 230, rng.randint(60, 180)))
            return base

        # Default: Deep celestial indigo-black canvas
        base = Image.new("RGBA", (width, height), (6, 4, 16, 255))
        draw = ImageDraw.Draw(base)

        # Cosmic focal nebula glow
        glow_center = (width // 2, int(height * 0.42))
        for r in range(450, 0, -15):
            alpha = int(45 * (1 - (r / 450) ** 1.8))
            draw.ellipse(
                [glow_center[0] - r, glow_center[1] - r, glow_center[0] + r, glow_center[1] + r],
                fill=(90, 35, 160, alpha),
            )

        # 3D Parallax Starfield (3 depth planes)
        rng = random.Random(1337)
        for layer in range(3):
            drift_speed = (layer + 1) * 4.0
            y_shift = int(t * drift_speed) % height
            star_count = 60 + layer * 40
            star_size = layer + 1
            opacity = 100 + layer * 60

            for _ in range(star_count):
                sx = rng.randint(0, width)
                sy = (rng.randint(0, height) + y_shift) % height
                draw.ellipse(
                    [sx, sy, sx + star_size, sy + star_size],
                    fill=(255, 255, 255, opacity),
                )

        return base

    @staticmethod
    def render_3d_sphere(
        radius: int = 240,
        t: float = 0.0,
        planet_type: str = "saturn",
        light_dir: Tuple[float, float, float] = (-0.6, -0.4, 0.7),
    ) -> Tuple[Image.Image, np.ndarray, np.ndarray, np.ndarray]:
        """
        Render a mathematically shaded 3D textured planet sphere or 3D thematic object.
        Returns:
        - Image (RGBA)
        - nx, ny, nz surface normal grids
        """
        d = radius * 2
        y, x = np.mgrid[-radius:radius, -radius:radius]
        dist_sq = x**2 + y**2
        mask = dist_sq <= radius**2

        nx = np.zeros_like(x, dtype=np.float32)
        ny = np.zeros_like(y, dtype=np.float32)
        nz = np.zeros_like(x, dtype=np.float32)

        nx[mask] = x[mask] / radius
        ny[mask] = y[mask] / radius
        nz[mask] = np.sqrt(np.maximum(0.0, 1.0 - (x[mask]**2 + y[mask]**2) / (radius**2)))

        # Directional Lighting (Diffuse + Specular)
        lx, ly, lz = light_dir
        norm_l = math.sqrt(lx**2 + ly**2 + lz**2)
        lx, ly, lz = lx / norm_l, ly / norm_l, lz / norm_l

        dot = np.maximum(0.0, nx * lx + ny * ly + nz * lz)
        ambient = 0.12
        light_intensity = ambient + (1.0 - ambient) * dot

        # Limb Darkening (Fresnel effect on edge of 3D sphere)
        fresnel = np.power(nz, 0.7)
        light_intensity = light_intensity * fresnel

        # Planet Latitude Bands (texture mapping onto 3D sphere)
        theta = np.arcsin(np.clip(ny, -1.0, 1.0))
        rotation_angle = t * 0.8
        phi = np.arctan2(nx, nz) + rotation_angle

        # -------------------------------------------------------------
        # PROCEDURAL 3D SHADER PALETTES
        # -------------------------------------------------------------
        if planet_type == "saturn":
            # Golden gas giant bands: ochre, honey, amber, pale ivory
            band_freq = 14.0
            wave = np.sin(theta * band_freq) * 0.5 + 0.5
            swirl = np.sin(phi * 4.0 + theta * 6.0) * 0.1
            base_r = 230.0 + 25.0 * wave - 20.0 * swirl
            base_g = 180.0 + 35.0 * wave - 15.0 * swirl
            base_b = 95.0 + 40.0 * wave

        elif planet_type == "jupiter":
            # Swirling cream, terracotta, and deep mocha storm bands + Great Red Spot
            band1 = np.sin(theta * 18.0 + np.sin(phi * 3.0) * 0.25) * 0.5 + 0.5
            band2 = np.sin(theta * 36.0 + phi * 2.0) * 0.5 + 0.5
            base_r = 215.0 + 30.0 * band1
            base_g = 145.0 + 35.0 * band1
            base_b = 95.0 + 30.0 * band2

        elif planet_type == "mars":
            # Rust-red iron crust + dark basalt Syrtis Major basins
            crater_noise = np.sin(phi * 7.0) * np.cos(theta * 8.0) * 0.5 + np.sin(phi * 15.0 + theta * 12.0) * 0.25
            mare = np.sin(phi * 3.0 + 1.0) * np.sin(theta * 4.0)
            is_dark = (mare > 0.2).astype(np.float32)
            base_r = 215.0 + 30.0 * crater_noise - 60.0 * is_dark
            base_g = 65.0 + 20.0 * crater_noise - 30.0 * is_dark
            base_b = 35.0 + 15.0 * crater_noise - 15.0 * is_dark

        elif planet_type == "sun":
            # Radiant solar plasma flares and pulsing convection granulation
            pulse = np.sin(t * 3.0) * 0.15
            plasma = np.sin(phi * 8.0 + t * 2.0) * np.sin(theta * 8.0) * 0.5 + 0.5
            base_r = 255.0
            base_g = 185.0 + 50.0 * plasma + 20.0 * pulse
            base_b = 40.0 + 40.0 * plasma

        elif planet_type == "moon":
            # Pearl silver/white highlands + dark basalt lunar maria plains
            crater_field = np.sin(phi * 6.0) * np.cos(theta * 5.0) + 0.5 * np.sin(phi * 18.0 + theta * 14.0)
            lunar_maria = (np.sin(phi * 2.5 + 0.8) * np.sin(theta * 3.0) > 0.15).astype(np.float32)
            highland_val = 215.0 + 30.0 * crater_field
            luma = highland_val * (1.0 - 0.42 * lunar_maria)
            base_r = luma
            base_g = luma * 0.98
            base_b = luma * 1.02

        elif planet_type == "venus":
            # Luminous mother-of-pearl cream & amber swirling sulfuric clouds
            cloud = np.sin(theta * 8.0 + phi * 2.5 + np.sin(phi * 5.0) * 0.3) * 0.5 + 0.5
            base_r = 245.0 + 10.0 * cloud
            base_g = 225.0 + 20.0 * cloud
            base_b = 165.0 + 30.0 * cloud

        elif planet_type == "mercury":
            # Emerald-crystalline metallic crust with high-contrast crater terrain
            craters = np.sin(phi * 12.0) * np.sin(theta * 12.0) * 0.5 + 0.5
            base_r = 70.0 + 40.0 * craters
            base_g = 175.0 + 50.0 * craters
            base_b = 135.0 + 40.0 * craters

        elif planet_type == "rahu":
            # Deep obsidian shadow eclipse orb with violet limb corona
            shadow_core = 20.0 + 15.0 * (nz ** 2)
            swirl = np.sin(phi * 8.0 - t * 2.5) * np.sin(theta * 6.0) * 0.5 + 0.5
            base_r = shadow_core + 50.0 * (1.0 - nz) + 20.0 * swirl
            base_g = shadow_core * 0.6
            base_b = shadow_core + 110.0 * (1.0 - nz) + 40.0 * swirl

        elif planet_type == "ketu":
            # Dark meteor crust with glowing crimson molten magma veins
            crust_noise = np.abs(np.sin(phi * 10.0 + theta * 8.0))
            is_magma = (crust_noise < 0.22).astype(np.float32)
            base_r = 60.0 * (1.0 - is_magma) + 255.0 * is_magma
            base_g = 35.0 * (1.0 - is_magma) + 110.0 * is_magma
            base_b = 30.0 * (1.0 - is_magma) + 20.0 * is_magma

        elif planet_type == "earth":
            # Azure oceans, emerald/ochre landmasses, and white atmospheric clouds
            continents = (np.sin(phi * 3.0 + np.sin(theta * 4.0) * 0.8) * np.cos(theta * 2.0) > 0.1).astype(np.float32)
            clouds = (np.sin(phi * 7.0 + theta * 5.0 + t * 0.5) > 0.45).astype(np.float32)
            surf_r = 20.0 * (1.0 - continents) + 45.0 * continents
            surf_g = 75.0 * (1.0 - continents) + 140.0 * continents
            surf_b = 185.0 * (1.0 - continents) + 70.0 * continents
            base_r = surf_r * (1.0 - clouds) + 245.0 * clouds
            base_g = surf_g * (1.0 - clouds) + 245.0 * clouds
            base_b = surf_b * (1.0 - clouds) + 255.0 * clouds

        elif planet_type == "crypto_coin":
            # 3D Rotating Metallic Gold Coin with raised rim and specular glint
            r_norm = np.sqrt(x**2 + y**2) / radius
            rim = ((r_norm > 0.78) & (r_norm < 0.96)).astype(np.float32)
            angle = np.arctan2(y, x) + rotation_angle
            specular_flash = np.maximum(0.0, np.cos(angle - 0.75)) ** 6
            base_r = 255.0 * (0.85 + 0.15 * rim) + 60.0 * specular_flash
            base_g = 195.0 * (0.85 + 0.15 * rim) + 50.0 * specular_flash
            base_b = 45.0 + 30.0 * rim + 30.0 * specular_flash

        elif planet_type == "cyber_core":
            # 3D Glowing Neon Cybernetic Core with digital wireframe grid
            lat_grid = np.abs(np.sin(theta * 14.0)) < 0.16
            lon_grid = np.abs(np.sin(phi * 14.0)) < 0.16
            grid = (lat_grid | lon_grid).astype(np.float32)
            base_r = 15.0 * (1.0 - grid) + 0.0 * grid
            base_g = 30.0 * (1.0 - grid) + 240.0 * grid
            base_b = 60.0 * (1.0 - grid) + 255.0 * grid

        elif planet_type == "dna_helix":
            # 3D Double Helix Bio-luminescent Energy Orb
            dna_wave = np.sin(phi * 6.0 + theta * 10.0) * 0.5 + 0.5
            base_r = 20.0 + 30.0 * dna_wave
            base_g = 180.0 + 60.0 * dna_wave
            base_b = 210.0 + 40.0 * (1.0 - dna_wave)

        elif planet_type == "prism_orb":
            # 3D Crystalline Gemstone refracting violet-rose hues
            facet = np.sin(phi * 5.0) * np.cos(theta * 5.0)
            base_r = 190.0 + 60.0 * facet
            base_g = 120.0 + 80.0 * np.sin(theta * 6.0)
            base_b = 240.0 + 15.0 * facet

        else:
            base_r, base_g, base_b = 220.0, 200.0, 160.0

        # Apply lighting intensity
        img_r = np.clip(base_r * light_intensity, 0, 255).astype(np.uint8)
        img_g = np.clip(base_g * light_intensity, 0, 255).astype(np.uint8)
        img_b = np.clip(base_b * light_intensity, 0, 255).astype(np.uint8)
        img_a = (mask * 255).astype(np.uint8)

        rgba = np.stack([img_r, img_g, img_b, img_a], axis=-1)
        planet_img = Image.fromarray(rgba, mode="RGBA")

        return planet_img, nx, ny, nz

    @staticmethod
    def render_saturn_rings(
        outer_width: int,
        outer_height: int,
        tilt_deg: float = 26.0,
        inner_r: int = 300,
        outer_r: int = 490,
        center: Tuple[int, int] = (540, 800),
        front_only: bool = False,
        back_only: bool = False,
    ) -> Image.Image:
        """
        Render 3D tilted concentric rings with perspective, Cassini gap, and transparency.
        Can render either back_only (behind planet disk) or front_only (in front of disk).
        """
        img = Image.new("RGBA", (outer_width, outer_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        tilt_rad = math.radians(tilt_deg)
        cx, cy = center
        y_scale = math.sin(tilt_rad)

        for r in range(outer_r, inner_r, -2):
            # Cassini Division gap (space between ring A and ring B)
            is_cassini = (395 <= r <= 412)
            if is_cassini:
                continue

            rx = r
            ry = int(r * y_scale)

            # Opacity variation across rings
            alpha = 180 if r > 412 else 220
            color = (225, 195, 130, alpha) if r > 412 else (245, 215, 150, alpha)

            bbox = [cx - rx, cy - ry, cx + rx, cy + ry]

            if front_only:
                # Lower half (y > cy) passes in front of the planet
                draw.arc(bbox, start=0, end=180, fill=color, width=3)
            elif back_only:
                # Upper half (y <= cy) passes behind the planet
                draw.arc(bbox, start=180, end=360, fill=color, width=3)
            else:
                draw.ellipse(bbox, outline=color, width=2)

        return img

    # Memory cache for smooth 3D rotation frames
    _rotation_cache: Dict[str, List[Image.Image]] = {}

    @classmethod
    def preload_3d_rotation_cache(cls, planet_type: str = "saturn", steps: int = 24, radius: int = 240):
        """Pre-compute 360-degree rotation sequence for blazing fast 30fps rendering."""
        cache_key = f"{planet_type}_{radius}_{steps}"
        if cache_key in cls._rotation_cache:
            return cls._rotation_cache[cache_key]

        frames = []
        for i in range(steps):
            t_rot = (i / steps) * (2.0 * math.pi / 0.8)
            img, _, _, _ = cls.render_3d_sphere(radius=radius, t=t_rot, planet_type=planet_type)
            frames.append(img)

        cls._rotation_cache[cache_key] = frames
        return frames

    @classmethod
    def render_composite_3d_planet_frame(
        cls,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        t: float = 0.0,
        planet_type: str = "saturn",
        center: Optional[Tuple[int, int]] = None,
        radius: int = 240,
        use_cache: bool = True,
    ) -> Image.Image:
        """
        Assemble the complete 3D scene frame:
        1. 3D Parallax Space Background (or themed backdrop)
        2. Back half of 3D inclined Rings (if Saturn)
        3. 3D Shaded Rotating Object Sphere
        4. Atmospheric / Speclar Limb Glow
        5. Front half of 3D inclined Rings (if Saturn)
        """
        center_pos = center or (width // 2, int(height * 0.42))
        cx, cy = center_pos

        # Choose backdrop style
        if planet_type == "crypto_coin":
            b_style = "crypto"
        elif planet_type in ("cyber_core", "dna_helix"):
            b_style = "cyber"
        else:
            b_style = "space"

        # 1. Background
        frame = cls.create_space_backdrop(width, height, t=t, style=b_style)

        if planet_type == "saturn":
            # 2. Back rings (depth behind planet)
            back_rings = cls.render_saturn_rings(
                outer_width=width,
                outer_height=height,
                tilt_deg=26.0,
                inner_r=int(radius * 1.25),
                outer_r=int(radius * 2.1),
                center=center_pos,
                back_only=True,
            )
            frame = Image.alpha_composite(frame, back_rings)

        # 3. 3D Shaded Object Sphere (with rotation cache)
        if use_cache:
            cache = cls.preload_3d_rotation_cache(planet_type=planet_type, steps=24, radius=radius)
            frame_idx = int(t * 8.0) % len(cache)
            planet_img = cache[frame_idx]
        else:
            planet_img, _, _, _ = cls.render_3d_sphere(
                radius=radius,
                t=t,
                planet_type=planet_type,
            )

        planet_x = cx - radius
        planet_y = cy - radius
        frame.paste(planet_img, (planet_x, planet_y), planet_img)

        # 4. Atmospheric / Specular Limb Glow
        glow_colors = {
            "saturn": (180, 140, 255, 90),
            "jupiter": (255, 180, 80, 110),
            "mars": (255, 60, 40, 120),
            "sun": (255, 200, 50, 180),
            "moon": (190, 215, 255, 120),
            "venus": (255, 225, 160, 110),
            "mercury": (50, 230, 170, 110),
            "rahu": (180, 50, 255, 140),
            "ketu": (255, 80, 20, 140),
            "earth": (70, 150, 255, 130),
            "crypto_coin": (255, 215, 0, 130),
            "cyber_core": (0, 240, 255, 140),
            "dna_helix": (40, 240, 180, 130),
            "prism_orb": (220, 100, 255, 130),
        }
        glow_color = glow_colors.get(planet_type, (180, 140, 255, 90))

        glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.ellipse(
            [planet_x - 14, planet_y - 14, planet_x + radius * 2 + 14, planet_y + radius * 2 + 14],
            outline=glow_color,
            width=10,
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(16))
        frame = Image.alpha_composite(frame, glow_layer)

        if planet_type == "saturn":
            # 5. Front rings (depth in front of planet)
            front_rings = cls.render_saturn_rings(
                outer_width=width,
                outer_height=height,
                tilt_deg=26.0,
                inner_r=int(radius * 1.25),
                outer_r=int(radius * 2.1),
                center=center_pos,
                front_only=True,
            )
            frame = Image.alpha_composite(frame, front_rings)

        return frame.convert("RGB")

    @classmethod
    def render_celestial_zodiac_orbits(
        cls,
        width: int,
        height: int,
        t: float = 0.0,
        center: Optional[Tuple[int, int]] = None,
    ) -> Image.Image:
        """
        Render 3D inclined planetary orbit tracks with moving planetary nodes (Vedic Grahas).
        """
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = center or (width // 2, int(height * 0.42))

        # 3 Orbit Planes inclined in 3D perspective
        orbits = [
            {"rx": 360, "ry": 160, "tilt": 18, "color": (255, 215, 0, 110), "speed": 0.4, "label": "Shani", "node_color": (255, 215, 0)},
            {"rx": 440, "ry": 195, "tilt": -12, "color": (147, 92, 255, 90), "speed": -0.6, "label": "Guru", "node_color": (230, 180, 255)},
            {"rx": 520, "ry": 230, "tilt": 32, "color": (239, 68, 68, 80), "speed": 0.3, "label": "Rahu", "node_color": (255, 100, 100)},
        ]

        for orb in orbits:
            rx, ry = orb["rx"], orb["ry"]
            bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
            draw.ellipse(bbox, outline=orb["color"], width=2)

            # Calculate moving 3D node position along orbit
            angle = t * orb["speed"]
            node_x = int(cx + rx * math.cos(angle))
            node_y = int(cy + ry * math.sin(angle))
            nr = 8

            # Glowing planetary node
            draw.ellipse([node_x - nr - 4, node_y - nr - 4, node_x + nr + 4, node_y + nr + 4], fill=orb["node_color"] + (80,))
            draw.ellipse([node_x - nr, node_y - nr, node_x + nr, node_y + nr], fill=orb["node_color"] + (255,))

            # Subtle connecting aspect line to center
            draw.line([(cx, cy), (node_x, node_y)], fill=orb["color"], width=1)

        return img

    # =====================================================================
    # MULTI-THEME 3D PROCEDURAL GENERATORS (GEMSTONES, KUNDLI, YANTRA, ETC.)
    # =====================================================================

    _gemstone_cache: Dict[str, List[Image.Image]] = {}
    _kundli_cache: Dict[str, List[Image.Image]] = {}
    _yantra_cache: Dict[str, List[Image.Image]] = {}
    _zodiac_cache: Dict[str, List[Image.Image]] = {}
    _vortex_cache: Dict[str, List[Image.Image]] = {}

    @classmethod
    def render_3d_gemstone(
        cls,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        t: float = 0.0,
        center: Optional[Tuple[int, int]] = None,
        radius: int = 240,
        gem_type: str = "blue_sapphire",
    ) -> Image.Image:
        """
        Renders an authentic 3D multi-faceted rotating crystal gemstone with
        specular reflections, internal facet depth, and radiating cosmic aura.
        """
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        cx, cy = center or (width // 2, int(height * 0.42))

        gem_palettes = {
            "blue_sapphire": {
                "base": (15, 45, 175),
                "mid": (35, 95, 235),
                "light": (120, 200, 255),
                "glint": (220, 245, 255),
                "glow": (30, 80, 255, 90),
                "aura_beams": (80, 140, 255, 120),
            },
            "yellow_sapphire": {
                "base": (180, 120, 10),
                "mid": (245, 185, 25),
                "light": (255, 230, 120),
                "glint": (255, 255, 220),
                "glow": (255, 190, 30, 90),
                "aura_beams": (255, 210, 60, 120),
            },
            "ruby": {
                "base": (160, 15, 45),
                "mid": (230, 35, 75),
                "light": (255, 110, 150),
                "glint": (255, 220, 235),
                "glow": (255, 30, 70, 90),
                "aura_beams": (255, 70, 100, 120),
            },
            "emerald": {
                "base": (10, 110, 60),
                "mid": (20, 190, 110),
                "light": (80, 245, 170),
                "glint": (210, 255, 235),
                "glow": (20, 230, 130, 90),
                "aura_beams": (40, 245, 150, 120),
            },
            "diamond": {
                "base": (130, 150, 190),
                "mid": (195, 215, 245),
                "light": (240, 250, 255),
                "glint": (255, 255, 255),
                "glow": (180, 220, 255, 90),
                "aura_beams": (200, 230, 255, 120),
            },
        }
        palette = gem_palettes.get(gem_type, gem_palettes["blue_sapphire"])

        n_facets = 8
        r_table = radius * 0.52
        r_girdle = radius * 0.95
        h_table = -radius * 0.50
        h_girdle = -radius * 0.05
        h_culet = radius * 0.90

        rot_y = t * 1.2
        rot_x = math.radians(24.0 + 4.0 * math.sin(t * 1.5))

        cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
        cos_x, sin_x = math.cos(rot_x), math.sin(rot_x)

        def transform_point(x, y, z):
            x1 = x * cos_y + z * sin_y
            z1 = -x * sin_y + z * cos_y
            y2 = y * cos_x - z1 * sin_x
            z2 = y * sin_x + z1 * cos_x
            fov = 1000.0
            scale = fov / (fov - z2)
            px = cx + x1 * scale
            py = cy + y2 * scale
            return (px, py, z2)

        table_pts = [(r_table * math.cos(2 * math.pi * i / n_facets), h_table, r_table * math.sin(2 * math.pi * i / n_facets)) for i in range(n_facets)]
        girdle_pts = [(r_girdle * math.cos(2 * math.pi * i / (n_facets * 2)), h_girdle, r_girdle * math.sin(2 * math.pi * i / (n_facets * 2))) for i in range(n_facets * 2)]
        culet_pt = (0.0, h_culet, 0.0)

        t_table = [transform_point(*p) for p in table_pts]
        t_girdle = [transform_point(*p) for p in girdle_pts]
        t_culet = transform_point(*culet_pt)

        facets = []
        facets.append({"pts": t_table, "type": "table"})
        for i in range(n_facets):
            i_next = (i + 1) % n_facets
            g_mid = i * 2 + 1
            g_left = i * 2
            g_right = (i * 2 + 2) % (n_facets * 2)
            facets.append({"pts": [t_table[i], t_table[i_next], t_girdle[g_mid]], "type": "crown_star"})
            facets.append({"pts": [t_table[i], t_girdle[g_mid], t_girdle[g_left]], "type": "crown_kite"})
            facets.append({"pts": [t_table[i_next], t_girdle[g_right], t_girdle[g_mid]], "type": "crown_kite"})

        for i in range(n_facets * 2):
            i_next = (i + 1) % (n_facets * 2)
            facets.append({"pts": [t_girdle[i], t_girdle[i_next], t_culet], "type": "pavilion"})

        facets.sort(key=lambda f: sum(p[2] for p in f["pts"]) / len(f["pts"]))

        # Radiant aura rays
        for beam_idx in range(12):
            beam_ang = (2 * math.pi * beam_idx / 12) + (t * 0.6)
            beam_len = radius * 2.2 + 20 * math.sin(t * 3.0 + beam_idx)
            bx = cx + beam_len * math.cos(beam_ang)
            by = cy + beam_len * math.sin(beam_ang)
            draw.line([(cx, cy), (bx, by)], fill=palette["aura_beams"], width=2)

        # Glow sphere
        glow_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        gr = int(radius * 1.35)
        glow_draw.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=palette["glow"])
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(36))
        canvas = Image.alpha_composite(canvas, glow_img)
        draw = ImageDraw.Draw(canvas)

        lx, ly, lz = -0.5, -0.6, 0.8
        l_mag = math.sqrt(lx**2 + ly**2 + lz**2)
        lx, ly, lz = lx / l_mag, ly / l_mag, lz / l_mag

        for f in facets:
            pts = f["pts"]
            if len(pts) < 3:
                continue
            v0, v1, v2 = pts[0], pts[1], pts[2]
            ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
            bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
            cross_z = ax * by - ay * bx
            is_front = cross_z < 0

            nx = ay * bz - az * by
            ny = az * bx - ax * bz
            nz = ax * by - ay * bx
            n_mag = math.sqrt(nx**2 + ny**2 + nz**2)
            if n_mag > 0.001:
                nx, ny, nz = nx / n_mag, ny / n_mag, nz / n_mag
            else:
                nx, ny, nz = 0.0, 0.0, 1.0

            diffuse = max(0.12, abs(nx * lx + ny * ly + nz * lz))
            dot_nl = nx * lx + ny * ly + nz * lz
            rz = 2 * dot_nl * nz - lz
            specular = max(0.0, rz) ** 14

            base_c, mid_c, glint_c = palette["base"], palette["mid"], palette["glint"]
            alpha = 240 if is_front else 110

            r_col = int(min(255, base_c[0] * (1 - diffuse) + mid_c[0] * diffuse + glint_c[0] * specular * 1.2))
            g_col = int(min(255, base_c[1] * (1 - diffuse) + mid_c[1] * diffuse + glint_c[1] * specular * 1.2))
            b_col = int(min(255, base_c[2] * (1 - diffuse) + mid_c[2] * diffuse + glint_c[2] * specular * 1.2))

            poly_2d = [(p[0], p[1]) for p in pts]
            draw.polygon(poly_2d, fill=(r_col, g_col, b_col, alpha))
            edge_alpha = 255 if is_front else 120
            draw.line(poly_2d + [poly_2d[0]], fill=(min(255, r_col + 50), min(255, g_col + 50), min(255, b_col + 50), edge_alpha), width=2)

        # Sparkle star
        glint_time = (t * 2.5) % (math.pi * 2)
        if math.sin(glint_time) > 0.8:
            gp = t_table[0]
            gx, gy = gp[0], gp[1]
            g_sz = int(18 + 12 * math.sin(glint_time * 4))
            draw.polygon([(gx, gy - g_sz), (gx + 3, gy), (gx, gy + g_sz), (gx - 3, gy)], fill=(255, 255, 255, 240))
            draw.polygon([(gx - g_sz, gy), (gx, gy + 3), (gx + g_sz, gy), (gx, gy - 3)], fill=(255, 255, 255, 240))
            draw.ellipse([gx - 4, gy - 4, gx + 4, gy + 4], fill=(255, 255, 255, 255))

        return canvas

    @classmethod
    def preload_gemstone_cache(cls, gem_type: str = "blue_sapphire", steps: int = 36, radius: int = 240) -> List[Image.Image]:
        cache_key = f"{gem_type}_{radius}_{steps}"
        if cache_key in cls._gemstone_cache:
            return cls._gemstone_cache[cache_key]
        frames = []
        for i in range(steps):
            t_rot = (i / steps) * (2.0 * math.pi / 1.2)
            frames.append(cls.render_3d_gemstone(t=t_rot, gem_type=gem_type, radius=radius))
        cls._gemstone_cache[cache_key] = frames
        return frames

    @classmethod
    def render_3d_kundli_chart(
        cls,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        t: float = 0.0,
        center: Optional[Tuple[int, int]] = None,
        size: int = 480,
        highlight_house: int = 8,
    ) -> Image.Image:
        """
        Renders an authentic traditional North Indian Vedic Kundali diamond chart
        with glowing gold sacred grid lines, Sanskrit symbols, and pulsing warning aura on House 8.
        """
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cx, cy = center or (width // 2, int(height * 0.42))

        bob_y = math.sin(t * 1.8) * 12
        tilt_rad = math.radians(16.0 + 3.0 * math.cos(t * 1.2))

        chart_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(chart_img)

        s, pad = size, 16
        half = s / 2.0

        draw.rectangle([pad, pad, s - pad, s - pad], fill=(12, 10, 24, 210), outline=(212, 175, 55, 220), width=3)

        p_tl, p_tr, p_br, p_bl = (pad, pad), (s - pad, pad), (s - pad, s - pad), (pad, s - pad)
        p_tm, p_rm, p_bm, p_lm = (half, pad), (s - pad, half), (half, s - pad), (pad, half)
        p_center = (half, half)

        draw.line([p_tl, p_br], fill=(212, 175, 55, 200), width=2)
        draw.line([p_tr, p_bl], fill=(212, 175, 55, 200), width=2)
        draw.line([p_tm, p_rm, p_bm, p_lm, p_tm], fill=(212, 175, 55, 240), width=3)

        pulse = 0.5 + 0.5 * math.sin(t * 4.5)
        warn_color = (int(235 + 20 * pulse), int(40 + 20 * pulse), 40, int(140 + 80 * pulse))

        # House 8 in North Indian Kundali (lower-right flank)
        h8_pts = [p_center, p_bm, p_rm]
        draw.polygon(h8_pts, fill=warn_color)
        draw.line(h8_pts + [p_center], fill=(255, 60, 60, 255), width=3)

        f_num = get_font(26, bold=True)
        f_badge = get_font(22, bold=True)
        draw.text((half - 10, half - 70), "1", font=f_num, fill=(255, 215, 0, 230))
        h8_cx = (half + s - pad) / 2 - 12
        h8_cy = (half + s - pad) / 2 + 10
        draw.text((h8_cx - 10, h8_cy - 20), str(highlight_house), font=f_num, fill=(255, 255, 255, 255))
        draw.text((h8_cx - 30, h8_cy + 10), "⚠️ KARMA", font=f_badge, fill=(255, 230, 0, 255))

        draw.text((pad + 12, pad + 10), "ॐ", font=get_font(28, bold=True), fill=(255, 215, 0, 200))
        draw.text((s - pad - 36, pad + 10), "卐", font=get_font(26, bold=True), fill=(255, 215, 0, 200))

        dx = int(math.sin(tilt_rad) * 60)
        dy = int(math.cos(tilt_rad) * size * 0.82)
        quad = [dx, 0, 0, dy, size, dy, size - dx, 0]
        tilted_chart = chart_img.transform((size, int(dy)), Image.Transform.QUAD, quad, resample=Image.Resampling.BICUBIC)

        paste_x = cx - size // 2
        paste_y = int(cy - dy // 2 + bob_y)

        glow_chart = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_chart)
        glow_draw.ellipse([cx - size // 2 - 40, cy - dy // 2 - 30, cx + size // 2 + 40, cy + dy // 2 + 30], fill=(180, 40, 255, 80))
        glow_chart = glow_chart.filter(ImageFilter.GaussianBlur(32))
        canvas = Image.alpha_composite(canvas, glow_chart)
        canvas.paste(tilted_chart, (paste_x, paste_y), tilted_chart)
        return canvas

    @classmethod
    def preload_kundli_cache(cls, highlight_house: int = 8, steps: int = 24, size: int = 480) -> List[Image.Image]:
        cache_key = f"kundli_{highlight_house}_{steps}_{size}"
        if cache_key in cls._kundli_cache:
            return cls._kundli_cache[cache_key]
        frames = []
        for i in range(steps):
            t_rot = (i / steps) * (2.0 * math.pi / 4.5)
            frames.append(cls.render_3d_kundli_chart(t=t_rot, size=size, highlight_house=highlight_house))
        cls._kundli_cache[cache_key] = frames
        return frames

    @classmethod
    def render_3d_sacred_yantra(
        cls,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        t: float = 0.0,
        center: Optional[Tuple[int, int]] = None,
        radius: int = 260,
    ) -> Image.Image:
        """
        Renders the sacred 3D Sri Yantra mandala with interlocking golden triangles,
        concentric lotus circles, and divine radiating spiritual particle rays.
        """
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cx, cy = center or (width // 2, int(height * 0.42))
        draw = ImageDraw.Draw(canvas)

        for i in range(16):
            ang = (2 * math.pi * i / 16) + (t * 0.3)
            b_len = radius * 1.8 + 15 * math.sin(t * 2.0 + i)
            bx = cx + b_len * math.cos(ang)
            by = cy + b_len * math.sin(ang)
            draw.line([(cx, cy), (bx, by)], fill=(255, 215, 0, 60), width=2)

        for r_mult in [1.0, 0.92, 0.84]:
            r = int(radius * r_mult)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 215, 0, 180), width=2)

        n_petals = 16
        rot_lotus = t * 0.2
        for i in range(n_petals):
            ang = (2 * math.pi * i / n_petals) + rot_lotus
            pr = radius * 0.92
            px = cx + pr * math.cos(ang)
            py = cy + pr * math.sin(ang)
            draw.ellipse([px - 14, py - 14, px + 14, py + 14], outline=(255, 223, 100, 140), width=2)

        up_triangles = [
            {"r": radius * 0.72, "w_mult": 1.15, "y_off": 15},
            {"r": radius * 0.58, "w_mult": 1.10, "y_off": 25},
            {"r": radius * 0.44, "w_mult": 1.05, "y_off": 30},
            {"r": radius * 0.30, "w_mult": 1.00, "y_off": 35},
        ]
        for tri in up_triangles:
            r, w_m, y_o = tri["r"], tri["w_mult"], tri["y_off"]
            draw.polygon([(cx, cy - r + y_o), (cx - r * w_m * 0.866, cy + r * 0.5 + y_o), (cx + r * w_m * 0.866, cy + r * 0.5 + y_o)], outline=(255, 215, 0, 220), width=2)

        down_triangles = [
            {"r": radius * 0.78, "w_mult": 1.18, "y_off": -15},
            {"r": radius * 0.65, "w_mult": 1.12, "y_off": -22},
            {"r": radius * 0.52, "w_mult": 1.08, "y_off": -28},
            {"r": radius * 0.38, "w_mult": 1.02, "y_off": -32},
            {"r": radius * 0.24, "w_mult": 0.98, "y_off": -36},
        ]
        for tri in down_triangles:
            r, w_m, y_o = tri["r"], tri["w_mult"], tri["y_off"]
            draw.polygon([(cx, cy + r + y_o), (cx - r * w_m * 0.866, cy - r * 0.5 + y_o), (cx + r * w_m * 0.866, cy - r * 0.5 + y_o)], outline=(255, 180, 50, 220), width=2)

        bindu_r = int(12 + 4 * math.sin(t * 5.0))
        draw.ellipse([cx - bindu_r, cy - bindu_r, cx + bindu_r, cy + bindu_r], fill=(255, 255, 220, 255))
        draw.ellipse([cx - bindu_r - 6, cy - bindu_r - 6, cx + bindu_r + 6, cy + bindu_r + 6], outline=(255, 215, 0, 160), width=2)
        return canvas

    @classmethod
    def preload_yantra_cache(cls, steps: int = 24, radius: int = 260) -> List[Image.Image]:
        cache_key = f"yantra_{radius}_{steps}"
        if cache_key in cls._yantra_cache:
            return cls._yantra_cache[cache_key]
        frames = []
        for i in range(steps):
            t_rot = (i / steps) * (2.0 * math.pi / 0.3)
            frames.append(cls.render_3d_sacred_yantra(t=t_rot, radius=radius))
        cls._yantra_cache[cache_key] = frames
        return frames

    @classmethod
    def render_3d_zodiac_wheel(
        cls,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        t: float = 0.0,
        center: Optional[Tuple[int, int]] = None,
        radius: int = 270,
    ) -> Image.Image:
        """
        Renders a 3D tilted rotating Kalpurusha Zodiac Wheel with 12 Rashi divisions.
        """
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cx, cy = center or (width // 2, int(height * 0.42))
        draw = ImageDraw.Draw(canvas)

        zodiac_signs = [
            ("ARIES", "♈"), ("TAURUS", "♉"), ("GEMINI", "♊"), ("CANCER", "♋"),
            ("LEO", "♌"), ("VIRGO", "♍"), ("LIBRA", "♎"), ("SCORPIO", "♏"),
            ("SAGITTARIUS", "♐"), ("CAPRICORN", "♑"), ("AQUARIUS", "♒"), ("PISCES", "♓"),
        ]

        tilt_rad = math.radians(35.0)
        rot_speed = t * 0.4
        r_outer, r_inner = radius, int(radius * 0.72)
        ry_outer, ry_inner = int(r_outer * math.cos(tilt_rad)), int(r_inner * math.cos(tilt_rad))

        draw.ellipse([cx - r_outer, cy - ry_outer, cx + r_outer, cy + ry_outer], outline=(255, 215, 0, 220), width=3)
        draw.ellipse([cx - r_inner, cy - ry_inner, cx + r_inner, cy + ry_inner], outline=(255, 215, 0, 180), width=2)

        font_glyph = get_font(30, bold=True)
        for i, (name, glyph) in enumerate(zodiac_signs):
            angle = (2 * math.pi * i / 12) + rot_speed
            px_out, py_out = cx + r_outer * math.cos(angle), cy + ry_outer * math.sin(angle)
            px_in, py_in = cx + r_inner * math.cos(angle), cy + ry_inner * math.sin(angle)
            draw.line([(px_in, py_in), (px_out, py_out)], fill=(255, 215, 0, 140), width=2)

            mid_ang = angle + (math.pi / 12)
            r_mid, ry_mid = (r_outer + r_inner) / 2.0, (ry_outer + ry_inner) / 2.0
            gx, gy = cx + r_mid * math.cos(mid_ang), cy + ry_mid * math.sin(mid_ang)
            is_front = math.sin(mid_ang) > 0.0
            g_col = (255, 230, 80, 255) if is_front else (180, 180, 190, 110)
            draw.text((gx - 12, gy - 16), glyph, font=font_glyph, fill=g_col)

        cr = 30
        draw.ellipse([cx - cr, cy - int(cr * math.cos(tilt_rad)), cx + cr, cy + int(cr * math.cos(tilt_rad))], fill=(255, 215, 50, 240))
        return canvas

    @classmethod
    def preload_zodiac_cache(cls, steps: int = 36, radius: int = 270) -> List[Image.Image]:
        cache_key = f"zodiac_{radius}_{steps}"
        if cache_key in cls._zodiac_cache:
            return cls._zodiac_cache[cache_key]
        frames = []
        for i in range(steps):
            t_rot = (i / steps) * (2.0 * math.pi / 0.4)
            frames.append(cls.render_3d_zodiac_wheel(t=t_rot, radius=radius))
        cls._zodiac_cache[cache_key] = frames
        return frames

    @classmethod
    def render_3d_karmic_vortex(
        cls,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        t: float = 0.0,
        center: Optional[Tuple[int, int]] = None,
        radius: int = 280,
    ) -> Image.Image:
        """
        Renders an intense, swirling 3D cosmic karmic black hole / shadow vortex.
        """
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cx, cy = center or (width // 2, int(height * 0.42))
        draw = ImageDraw.Draw(canvas)

        n_arms = 4
        for arm in range(n_arms):
            arm_base_ang = (2 * math.pi * arm / n_arms) - (t * 1.8)
            pts = []
            for step in range(25):
                frac = step / 25.0
                r = radius * frac
                ang = arm_base_ang + (frac * 3.5)
                pts.append((cx + r * math.cos(ang), cy + int(r * 0.65 * math.sin(ang))))

            for j in range(len(pts) - 1):
                alpha = int(220 * (j / len(pts)))
                col = (180, 30, 255, alpha) if arm % 2 == 0 else (255, 50, 80, alpha)
                draw.line([pts[j], pts[j + 1]], fill=col, width=int(2 + 4 * (j / len(pts))))

        for r_disk in range(int(radius * 0.6), int(radius * 0.15), -4):
            alpha = int(90 * (1.0 - (r_disk / (radius * 0.6))))
            draw.ellipse([cx - r_disk, cy - int(r_disk * 0.45), cx + r_disk, cy + int(r_disk * 0.45)], fill=(140, 20, 255, alpha))

        bh_r = int(radius * 0.22)
        draw.ellipse([cx - bh_r, cy - int(bh_r * 0.45), cx + bh_r, cy + int(bh_r * 0.45)], fill=(0, 0, 0, 255), outline=(255, 80, 200, 220), width=2)
        return canvas

    @classmethod
    def preload_vortex_cache(cls, steps: int = 24, radius: int = 280) -> List[Image.Image]:
        cache_key = f"vortex_{radius}_{steps}"
        if cache_key in cls._vortex_cache:
            return cls._vortex_cache[cache_key]
        frames = []
        for i in range(steps):
            t_rot = (i / steps) * (2.0 * math.pi / 1.8)
            frames.append(cls.render_3d_karmic_vortex(t=t_rot, radius=radius))
        cls._vortex_cache[cache_key] = frames
        return frames

    @classmethod
    def detect_scene_theme_3d(
        cls,
        scene_idx: int,
        total_scenes: int,
        scene_text: str = "",
        topic: str = "",
        niche: str = "",
    ) -> Dict[str, Any]:
        """
        Intelligently select a distinct 3D visual theme for this specific scene!
        Produces cinematic visual variation across beats:
        - Hook: 3D Faceted Gemstone (or Zodiac Wheel)
        - Stakes: 3D Vedic Kundali 12-House Birth Chart
        - Graha/Lord: 3D Planet Sphere (Saturn, Jupiter, Mars, etc.)
        - Karma/Conflict: 3D Cosmic Karmic Vortex
        - Resolution/CTA: 3D Sacred Sri Yantra / Devotional Mandala
        """
        combined = f" {topic} {scene_text} {niche} ".lower()

        gem_type = "blue_sapphire"
        has_gem = False
        if any(k in combined for k in ["neelam", "blue sapphire", "sapphire"]):
            gem_type = "blue_sapphire"
            has_gem = True
        elif any(k in combined for k in ["pukhraj", "yellow sapphire", "topaz"]):
            gem_type = "yellow_sapphire"
            has_gem = True
        elif any(k in combined for k in ["ruby", "manik"]):
            gem_type = "ruby"
            has_gem = True
        elif any(k in combined for k in ["emerald", "panna"]):
            gem_type = "emerald"
            has_gem = True
        elif any(k in combined for k in ["diamond", "heera"]):
            gem_type = "diamond"
            has_gem = True
        elif any(k in combined for k in ["gemstone", "ratna", "crystal"]):
            gem_type = "blue_sapphire"
            has_gem = True

        house_num = 8
        m_house = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+house\b", combined)
        if m_house:
            try:
                house_num = int(m_house.group(1))
            except Exception:
                house_num = 8

        primary_planet = cls.detect_3d_object_type(topic=topic, niche=niche)

        # 5-beat progressive narrative mapping:
        if scene_idx == 0:
            if has_gem:
                accent = (35, 95, 235) if gem_type == "blue_sapphire" else (255, 215, 0)
                return {"type": "gemstone_3d", "gem_type": gem_type, "accent": accent, "badge": "GEMSTONE ENERGY"}
            elif any(k in combined for k in ["kundli", "chart", "house", "awakening", "placement", "signs", "3 am", "wealth", "drain", "money", "ruin"]):
                return {"type": "kundli_chart_3d", "highlight_house": house_num, "accent": (239, 68, 68), "badge": "KUNDLI SECRET"}
            elif any(k in combined for k in ["saturn", "shani", "jupiter", "guru", "mars", "mangal", "venus", "shukra", "sun", "surya", "moon", "rahu", "ketu"]):
                return {"type": "planet_3d", "planet_type": primary_planet, "accent": (255, 215, 0), "badge": "PLANETARY IMPACT"}
            else:
                return {"type": "kundli_chart_3d", "highlight_house": 8, "accent": (255, 215, 0), "badge": "VEDIC ASTROLOGY"}

        elif scene_idx == 1:
            return {"type": "kundli_chart_3d", "highlight_house": house_num, "accent": (239, 68, 68), "badge": f"HOUSE {house_num} SECRET"}

        elif scene_idx == 2:
            return {"type": "planet_3d", "planet_type": primary_planet, "accent": (255, 215, 0), "badge": "GRAHA CONFRONTATION"}

        elif scene_idx == 3:
            return {"type": "karmic_vortex_3d", "accent": (168, 85, 247), "badge": "KARMIC CONSEQUENCE"}

        else:
            return {"type": "sacred_yantra_3d", "accent": (255, 215, 0), "badge": "SACRED REMEDY"}

    @classmethod
    def render_full_3d_scene_frame(
        cls,
        t: float,
        on_screen_text: str,
        scene_number: int,
        total_scenes: int,
        planet_type: str = "saturn",
        topic: str = "",
        niche: str = "",
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        show_orbits: bool = True,
    ) -> Image.Image:
        """
        Render a fully composited 3D frame ready for video assembly:
        - 3D rotating planet + rings + atmosphere
        - 3D inclined planetary orbits with moving nodes
        - Safe-zone viral card & category badge
        """
        center = (width // 2, int(height * 0.42))

        # Auto-detect object if not explicitly specified
        if not planet_type or planet_type == "auto":
            resolved_type = cls.detect_3d_object_type(topic=topic, niche=niche)
        else:
            resolved_type = planet_type

        # 1. 3D Planet + space background
        frame = cls.render_composite_3d_planet_frame(
            width=width,
            height=height,
            t=t,
            planet_type=resolved_type,
            center=center,
        )

        # 2. 3D Celestial orbits (show for space/planetary themes)
        if show_orbits and resolved_type in ("saturn", "jupiter", "mars", "sun", "moon", "venus", "mercury", "rahu", "ketu", "earth"):
            orbit_layer = cls.render_celestial_zodiac_orbits(width, height, t=t, center=center)
            frame = Image.alpha_composite(frame.convert("RGBA"), orbit_layer).convert("RGB")

        # 3. High-conversion viral on-screen card & category badge
        from app.video.video_composer import render_scene_overlay
        accent_map = {
            "saturn": (255, 215, 0),
            "jupiter": (234, 179, 8),
            "mars": (239, 68, 68),
            "sun": (245, 158, 11),
            "moon": (192, 192, 230),
            "venus": (251, 191, 36),
            "mercury": (16, 185, 129),
            "rahu": (168, 85, 247),
            "ketu": (239, 68, 68),
            "earth": (59, 130, 246),
            "crypto_coin": (255, 215, 0),
            "cyber_core": (6, 182, 212),
            "dna_helix": (16, 185, 129),
            "prism_orb": (168, 85, 247),
        }
        chosen_accent = accent_map.get(resolved_type, (255, 215, 0))

        final_frame = render_scene_overlay(
            bg_image=frame,
            on_screen_text=on_screen_text,
            scene_number=scene_number,
            total_scenes=total_scenes,
            accent_color=chosen_accent,
            topic_badge=niche.upper() if niche else None,
        )

        return final_frame


if __name__ == "__main__":
    print("Testing Extended 3D Procedural Engine...")
    t_start = time.time()
    test_frame = Engine3D.render_full_3d_scene_frame(
        t=1.5,
        on_screen_text="STOP WEARING PUKHRAJ!",
        scene_number=1,
        total_scenes=5,
        planet_type="jupiter",
        niche="Vedic Astrology",
    )
    test_path = PROJECT_ROOT / "output" / "test_3d_jupiter_scene.jpg"
    test_frame.save(test_path, quality=95)
    print(f"Rendered 3D Scene in {time.time() - t_start:.2f}s -> {test_path}")
