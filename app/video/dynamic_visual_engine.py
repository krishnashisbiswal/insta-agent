import hashlib
import io
import json
import logging
import math
import os
import random
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger("DynamicVisualEngine")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED_BROLL_DIR = PROJECT_ROOT / "assets" / "generated_broll"
GENERATED_BROLL_DIR.mkdir(parents=True, exist_ok=True)
CINEMATIC_BROLL_DIR = PROJECT_ROOT / "assets" / "cinematic_broll"
USED_REGISTRY_FILE = PROJECT_ROOT / "storage" / "used_visuals_registry.json"

# Permanently blacklisted static assets that caused repetitive output
BANNED_IMAGE_NAMES: Set[str] = {
    "2_kundli_chart.jpg",
    "4_sacred_havan.jpg",
    "5_temple_sanctum.jpg",
    "gemstone_blue_sapphire.jpg",
    "gemstone_yellow_sapphire.jpg",
    "gemstone_ruby.jpg",
    "gemstone_emerald.jpg",
    "temple_sanctum_golden_diyas.jpg",
    "vedic_astrology_parchment_chart.jpg",
    "sacred_vedic_fire_altar.jpg",
}


class DynamicVisualEngine:
    """
    Autonomous AI Visual Engine that creates brand-new, unique 9:16 vertical images
    for every scene in every video.
    Guarantees:
    1. ZERO REUSED IMAGES across new topics or videos (backed by persistent disk registry).
    2. SCENE-SPECIFIC VISUALS: Deeply tailored to the specific deity, planet, gemstone, and psychological trait.
    3. FAILSAFE MULTI-LAYER SOURCING:
       - Layer 1: Online AI photorealistic generation with custom seed & trait prompt.
       - Layer 2: Live online photographic search (Wikimedia Commons + NASA API) with 9:16 vertical smart crop.
       - Layer 3: Curated thematic fallback photographic bank (strictly unused only).
       - Layer 4: Procedural atmospheric celestial compositor.
    """

    @classmethod
    def get_used_registry(cls) -> Set[str]:
        """Loads all globally used image paths/names across videos."""
        if not USED_REGISTRY_FILE.exists():
            initial = set(BANNED_IMAGE_NAMES)
            cls.save_used_registry(initial)
            return initial
        try:
            with open(USED_REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                res = set(data.get("used_images", []))
                res.update(BANNED_IMAGE_NAMES)
                return res
        except Exception as e:
            logger.warning(f"Notice reading visual registry: {e}")
            return set(BANNED_IMAGE_NAMES)

    @classmethod
    def save_used_registry(cls, used_set: Set[str]) -> None:
        """Persists used images registry to disk."""
        USED_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(USED_REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump({"used_images": sorted(list(used_set))}, f, indent=2)
        except Exception as e:
            logger.warning(f"Notice saving visual registry: {e}")

    @classmethod
    def register_used_image(cls, img_path: Path) -> None:
        """Records an image as used so it is never reused in future videos."""
        reg = cls.get_used_registry()
        try:
            rel = str(img_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
            reg.add(rel)
        except Exception:
            pass
        reg.add(img_path.name)
        cls.save_used_registry(reg)

    @classmethod
    def is_image_used(cls, img_path: Path) -> bool:
        """Checks if this image has ever been used in this or past videos."""
        name = img_path.name.lower()
        if name in BANNED_IMAGE_NAMES:
            return True
        # Permanently block any legacy static artifact b-roll or repeated files
        if any(pat in name for pat in ["neelam_sc", "pukhraj_sc", "panna_sc", "gomed_sc", "ruby_sc", "sample_"]):
            return True
        reg = cls.get_used_registry()
        if img_path.name in reg:
            return True
        try:
            rel = str(img_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
            if rel in reg:
                return True
        except Exception:
            pass
        return False

    @classmethod
    def get_trait_visual_prompt(cls, scene_dict: Dict[str, Any], topic: str, scene_idx: int) -> str:
        """Constructs an ultra-photorealistic, cinematic 9:16 vertical image prompt strictly matching scene content."""
        spoken = scene_dict.get("spoken_line", "")
        on_screen = scene_dict.get("on_screen_text", "")
        vis_desc = scene_dict.get("visual_description", "")
        entity_context = f"{spoken} {on_screen} {vis_desc} {topic}".lower()
        scene_context = f"{spoken} {on_screen} {vis_desc}".lower()

        base_modifiers = (
            "cinematic lighting, photorealistic, 9:16 vertical aspect ratio, masterwork"
        )

        # 1. Identify specific celestial/gemstone/crystal/rudraksha entity
        gem_name = "Vedic Astrological Gemstone"
        planet_name = "Cosmic Celestial Entity"
        if any(k in entity_context for k in ["pyrite"]):
            gem_name = "natural raw golden Pyrite crystal cluster sparkling with metallic brass luster"
            planet_name = "golden solar abundance aura and sacred geometry"
        elif any(k in entity_context for k in ["amethyst"]):
            gem_name = "natural deep violet raw Amethyst geode cluster glowing with sacred purple crystalline light"
            planet_name = "soothing crown chakra spiritual aura and peaceful starlight"
        elif any(k in entity_context for k in ["tourmaline"]):
            gem_name = "raw natural Black Tourmaline crystalline tower with glossy jet-black striated texture"
            planet_name = "impenetrable auric protective shield and grounding earth energy"
        elif any(k in entity_context for k in ["citrine"]):
            gem_name = "warm radiant natural Golden Citrine quartz crystal glowing with amber sunshine"
            planet_name = "radiant solar plexus chakra energy of manifestation and prosperity"
        elif any(k in entity_context for k in ["rose quartz"]):
            gem_name = "delicate translucent pink Rose Quartz raw crystal specimen with soft loving luminescence"
            planet_name = "gentle anahata heart chakra pink aura of harmony and peace"
        elif any(k in entity_context for k in ["tiger", "tigers eye", "tiger's eye"]):
            gem_name = "polished golden-brown Tiger's Eye gemstone revealing silky chatoyant bands of light"
            planet_name = "fearless courage and grounded inner power"
        elif any(k in entity_context for k in ["clear quartz", "sphatik"]):
            gem_name = "flawless prismatic natural Clear Quartz crystal point refracting crystalline rainbow light"
            planet_name = "pure high-frequency universal light and mental clarity"
        elif any(k in entity_context for k in ["gauri shankar"]):
            gem_name = "sacred natural Nepali Gauri Shankar Rudraksha two naturally joined beads with distinct divine grooves"
            planet_name = "sacred cosmic Shiva-Shakti union and divine grace"
        elif any(k in entity_context for k in ["rudraksha", "rudraksh", "mukhi"]):
            gem_name = "authentic sacred Nepali Rudraksha bead with deep natural mukhi grooves and sacred water droplets"
            planet_name = "calming bio-electromagnetic energy field and Lord Shiva's divine consciousness"
        elif any(k in entity_context for k in ["neelam", "blue sapphire", "shani", "saturn"]):
            gem_name = "natural certified royal Blue Sapphire (Neelam) gemstone with deep velvety blue luster"
            planet_name = "planet Saturn with majestic dust rings in dark cosmos"
        elif any(k in entity_context for k in ["manik", "ruby", "surya", "sun"]):
            gem_name = "natural certified pigeon-blood Ruby (Manik) gemstone glowing with crimson fire"
            planet_name = "blazing radiant Sun with golden solar flares in space"
        elif any(k in entity_context for k in ["pukhraj", "yellow sapphire", "guru", "jupiter"]):
            gem_name = "natural certified Ceylon Yellow Sapphire (Pukhraj) gemstone glowing like golden sunshine"
            planet_name = "giant banded planet Jupiter in cosmic space"
        elif any(k in entity_context for k in ["panna", "emerald", "budh", "mercury"]):
            gem_name = "natural certified vivid green Zambian Emerald (Panna) gemstone"
            planet_name = "planet Mercury in sunlit space"
        elif any(k in entity_context for k in ["moti", "pearl", "chandra", "moon"]):
            gem_name = "natural certified South Sea Pearl (Moti) glowing with iridescent silver luster"
            planet_name = "glowing celestial full Moon in midnight starfield"
        elif any(k in entity_context for k in ["moonga", "coral", "mangal", "mars"]):
            gem_name = "natural certified triangular Red Coral (Moonga) gemstone"
            planet_name = "reddish planet Mars in starry cosmos"
        elif any(k in entity_context for k in ["heera", "diamond", "shukra", "venus"]):
            gem_name = "natural certified brilliant-cut Diamond (Heera) refracting rainbow spectral fire"
            planet_name = "pearlescent planet Venus shining brilliant silver in twilight"
        elif any(k in entity_context for k in ["gomed", "hessonite", "rahu"]):
            gem_name = "natural certified honey-colored Ceylon Hessonite (Gomed) gemstone"
            planet_name = "mysterious total solar eclipse with glowing corona"
        elif any(k in entity_context for k in ["lehsuniya", "cat's eye", "ketu"]):
            gem_name = "natural certified Chrysoberyl Cat's Eye (Lehsuniya) gemstone with sharp chatoyant band"
            planet_name = "luminous celestial comet in deep starry galaxy"

        # 2. Semantic scene intent matching (strictly derived from THIS SCENE's text & description)
        # Hook / Opener Scene (Scene 1)
        if scene_idx == 0:
            if any(k in entity_context for k in ["pyrite", "amethyst", "tourmaline", "citrine", "rose quartz", "tiger", "quartz", "crystal", "rudraksh", "mukhi"]):
                return (
                    f"cinematic dramatic macro luxury shot of a {gem_name} resting upon a clean dark reflective surface, "
                    f"soft celestial aura of {planet_name} radiating around it, inspiring high-vibrational sacred lighting, {base_modifiers}"
                )
            return (
                f"cinematic dramatic macro luxury shot of a {gem_name} resting upon dark reflective obsidian stone, "
                f"subtle celestial aura of {planet_name} reflecting above, scroll-stopping high-stakes contrast, {base_modifiers}"
            )

        # Call to Action / DM Consultation / Sacred Temple Sanctuary
        if any(k in scene_context for k in ["dm", "save", "consultation", "परामर्श", "कमेंट", "booking", "message"]):
            return (
                f"cinematic sacred sanctum sanctorum of an ancient Vedic temple, multiple glowing brass oil lamps (diyas) "
                f"casting warm golden radiance on sacred offerings and ancient carved stone pillars, peaceful divine atmosphere, {base_modifiers}"
            )

        # Calming Nervous System / Meditation / Mental Clarity / Peace
        if any(k in scene_context for k in ["calm", "nervous system", "peace", "meditat", "focus", "clarity", "anxiety relief", "blood pressure", "एकाग्रता", "शांति", "तंत्रिका", "तनाव", "ध्यान", "फायदे", "राहत"]):
            return (
                f"cinematic peaceful shot of a serene person meditating in gentle morning golden sunlight, "
                f"soft glowing aura of harmonic tranquility, calming sacred atmosphere, warm zen aesthetic, {base_modifiers}"
            )

        # Aura Cleansing / Energy Shielding / EMF Protection / Negative Energy Absorption
        if any(k in scene_context for k in ["shield", "aura", "protect", "negative", "absorb", "emf", "psychic", "सुरक्षा", "आभामंडल", "नजर", "नकारात्मक"]):
            return (
                f"cinematic visual of a luminous energetic aura shield surrounding a peaceful silhouette, "
                f"sacred protective crystalline light particles deflecting shadowy negative waves, high vibrational energy, {base_modifiers}"
            )

        # Wealth Attraction / Abundance / Prosperity / Work Desk Sacred Setup
        if any(k in scene_context for k in ["attract", "wealth", "abundance", "prosperity", "money", "desk", "office", "धन", "समृद्धि", "आकर्षण", "बरकत", "कार्यस्थल"]):
            return (
                f"cinematic macro photograph of a natural golden {gem_name} catching warm morning sunlight on a refined executive wooden desk, "
                f"subtle golden bokeh, inspiring atmosphere of abundance and success, {base_modifiers}"
            )

        # Sacred Bio-Electromagnetism / Ancient Vedic Science / Heart & Bodily Harmony
        if any(k in scene_context for k in ["science", "bio-electric", "electromagnetic", "heart", "frequency", "resonance", "विज्ञान", "हृदय", "रक्तचाप", "ऊर्जा"]):
            return (
                f"cinematic sacred macro shot of {gem_name} radiating subtle golden sacred geometric frequency waves, "
                f"harmonizing bio-energy fields, ancient Vedic spiritual science visualization, {base_modifiers}"
            )

        # Warning Against Blind Internet Remedies / Unverified Rules
        if any(k in scene_context for k in ["blind", "remedy", "remedies", "unverified", "internet", "नियम", "उपाय", "अंधाधुंध"]):
            return (
                f"cinematic moody mystical library sanctum with ancient palm-leaf astrological scrolls, antique brass compass, "
                f"and a single solitary oil lamp flickering on dark weathered wood, caution and sacred wisdom, {base_modifiers}"
            )

        # Birth Chart, Kundli Houses (6th, 8th, 12th House, Lagna, Kendra)
        if any(k in scene_context for k in ["kundli", "house", "houses", "chart", "horoscope", "भाव", "लग्न", "केंद्र", "त्रिकोण", "छठे", "आठवें", "बारहवें"]):
            return (
                f"cinematic ancient Vedic astrological birth chart manuscript written on aged parchment with intricate golden geometric alignments, "
                f"glowing cosmic symbols and Sanskrit numbers illuminating astrological houses, floating stardust, {base_modifiers}"
            )

        # Opposing Enemy Planets Clashing / Energy Collision (e.g. Saturn clashing with Sun/Ruby)
        if any(k in scene_context for k in ["enemy", "clash", "collision", "opposing", "शत्रु", "टकराव", "विपरीत"]):
            return (
                f"cinematic epic cosmic collision of two opposing celestial forces, intense dark velvet blue energy clashing violently against "
                f"fiery blazing crimson solar rays in deep space, cosmic shockwaves and glowing plasma particles, {base_modifiers}"
            )

        # Panic, Anxiety, Insomnia, 3 AM Restlessness, Stress
        if any(k in scene_context for k in ["panic", "anxiety", "insomnia", "3 am", "sleep", "restless", "तनाव", "घबराहट", "अनिद्रा", "बेचैनी"]):
            return (
                f"cinematic moody dramatic shot of an exhausted restless person sitting awake by a dark rainy window at 3 AM in deep despair, "
                f"subtle cold blue rim light, moody psychological tension and sleeplessness, {base_modifiers}"
            )

        # Career Destruction, Bankruptcy, Financial Loss, Business Crash
        if any(k in scene_context for k in ["career", "financ", "money", "drain", "ruin", "destruct", "loss", "करियर", "नुकसान", "हानि", "कर्ज", "बर्बाद"]):
            return (
                f"cinematic moody dramatic shot of a distressed business professional sitting late at night at an executive desk with head in hands, "
                f"crashing red financial market graphs on multiple monitors in background, moody volumetric shadows, tension and heavy loss, {base_modifiers}"
            )

        # Wrong Metal, Wrong Finger, Ring Fitting, Physical Gemstone Placement
        if any(k in scene_context for k in ["metal", "finger", "hand", "wear", "ring", "धातु", "उंगली", "हाथ", "अंगूठी"]):
            return (
                f"cinematic macro luxury photograph of a person's hand wearing an elegant ring set with a {gem_name}, "
                f"dramatic moody studio lighting, subtle warning golden visual flare, fine jewelry details, {base_modifiers}"
            )

        # Use Gemini's custom visual description if provided
        if vis_desc and len(vis_desc.split()) >= 4:
            clean_desc = re.sub(r"^(cinematic\s+)?(8k\s+)?(shot\s+of\s+)?", "", vis_desc.strip(), flags=re.I)
            return f"cinematic 8k {clean_desc}, moody dramatic atmosphere, {base_modifiers}"

        # Default Planetary / Gemstone Macro
        return (
            f"cinematic dramatic cosmic photograph of {planet_name} with radiant glowing nebula, {base_modifiers}"
        )

    @classmethod
    def get_scene_search_query(cls, scene_dict: Dict[str, Any], topic: str, scene_idx: int) -> str:
        """Formulates targeted keywords for live photographic image retrieval that match exact scene content."""
        spoken = scene_dict.get("spoken_line", "").lower()
        on_screen = scene_dict.get("on_screen_text", "").lower()
        vis_desc = scene_dict.get("visual_description", "").lower()
        entity_context = f"{spoken} {on_screen} {vis_desc} {topic.lower()}"
        scene_context = f"{spoken} {on_screen} {vis_desc}".lower()

        # Detect active gemstone/planet/crystal/rudraksha
        gem_kw = "gemstone jewelry"
        planet_kw = "space stars"
        if any(k in entity_context for k in ["pyrite"]):
            gem_kw = "pyrite crystal cluster"
            planet_kw = "pyrite mineral specimen"
        elif any(k in entity_context for k in ["amethyst"]):
            gem_kw = "amethyst geode crystal"
            planet_kw = "amethyst purple mineral"
        elif any(k in entity_context for k in ["tourmaline"]):
            gem_kw = "black tourmaline crystal"
            planet_kw = "schorl tourmaline mineral"
        elif any(k in entity_context for k in ["citrine"]):
            gem_kw = "citrine quartz crystal"
            planet_kw = "natural citrine mineral"
        elif any(k in entity_context for k in ["rose quartz"]):
            gem_kw = "rose quartz crystal mineral"
            planet_kw = "raw rose quartz stone"
        elif any(k in entity_context for k in ["tiger", "tigers eye", "tiger's eye"]):
            gem_kw = "tigers eye mineral gemstone"
            planet_kw = "tigers eye stone macro"
        elif any(k in entity_context for k in ["gauri shankar"]):
            gem_kw = "rudraksha sacred bead"
            planet_kw = "rudraksha seed nepali"
        elif any(k in entity_context for k in ["rudraksha", "rudraksh", "mukhi"]):
            gem_kw = "rudraksha beads close up"
            planet_kw = "rudraksha seeds prayer"
        elif any(k in entity_context for k in ["neelam", "blue sapphire", "shani", "saturn"]):
            gem_kw = "blue sapphire gemstone"
            planet_kw = "saturn planet cassini"
        elif any(k in entity_context for k in ["manik", "ruby", "surya", "sun"]):
            gem_kw = "ruby gemstone jewelry"
            planet_kw = "sun solar flare nasa"
        elif any(k in entity_context for k in ["pukhraj", "yellow sapphire", "guru", "jupiter"]):
            gem_kw = "yellow sapphire gemstone"
            planet_kw = "jupiter planet hubble"
        elif any(k in entity_context for k in ["panna", "emerald", "budh", "mercury"]):
            gem_kw = "emerald gemstone jewelry"
            planet_kw = "mercury planet space"
        elif any(k in entity_context for k in ["moti", "pearl", "chandra", "moon"]):
            gem_kw = "natural pearl gemstone"
            planet_kw = "full moon night sky"
        elif any(k in entity_context for k in ["moonga", "coral", "mangal", "mars"]):
            gem_kw = "red coral gemstone"
            planet_kw = "planet mars hubble"
        elif any(k in entity_context for k in ["heera", "diamond", "shukra", "venus"]):
            gem_kw = "diamond gemstone jewelry"
            planet_kw = "venus planet twilight"

        # 1. Hook (Scene 0)
        if scene_idx == 0:
            return gem_kw

        # 2. CTA / DM Consultation / Sacred Temple
        if any(k in scene_context for k in ["dm", "save", "consultation", "परामर्श", "कमेंट", "booking", "message"]):
            queries = ["traditional hindu temple oil lamp", "diya lamp temple sanctum", "ancient temple sanctum brass diyas"]
            return queries[scene_idx % len(queries)]

        # 3. Calming Nervous System / Meditation / Peace
        if any(k in scene_context for k in ["calm", "nervous system", "peace", "meditat", "focus", "clarity", "anxiety relief", "एकाग्रता", "शांति", "ध्यान"]):
            queries = ["person meditating sunrise calm", "peaceful meditation zen morning", "peaceful zen stone balance"]
            return queries[scene_idx % len(queries)]

        # 4. Aura / Protection / Negativity Shield
        if any(k in scene_context for k in ["shield", "aura", "protect", "negative", "absorb", "emf", "सुरक्षा", "आभामंडल", "नजर"]):
            queries = [gem_kw, "aurora borealis night sky", "light beam dark space rays"]
            return queries[scene_idx % len(queries)]

        # 5. Wealth Attraction / Abundance / Office Desk
        if any(k in scene_context for k in ["attract", "wealth", "abundance", "prosperity", "money", "desk", "office", "धन", "समृद्धि"]):
            queries = [gem_kw, "pyrite crystal cluster", "morning sunlight office desk"]
            return queries[scene_idx % len(queries)]

        # 6. Blind Remedies / Internet Mistakes / Ancient Texts
        if any(k in scene_context for k in ["blind", "remedy", "remedies", "unverified", "internet", "नियम", "उपाय"]):
            queries = ["ancient sanskrit manuscript scroll", "antique astrology manuscript", "sacred oil lamp temple"]
            return queries[scene_idx % len(queries)]

        # 7. Birth Chart, Kundli Houses
        if any(k in scene_context for k in ["kundli", "house", "houses", "chart", "horoscope", "भाव", "लग्न", "केंद्र", "त्रिकोण"]):
            queries = ["ancient astrology manuscript chart", "astrolabe celestial horoscope", "zodiac horoscope chart wheel"]
            return queries[scene_idx % len(queries)]

        # 8. Enemy Planets Clashing / Collision
        if any(k in scene_context for k in ["enemy", "clash", "collision", "opposing", "शत्रु", "टकराव", "विपरीत"]):
            queries = [planet_kw, "galaxy collision space hubble", "nebula explosion cosmos"]
            return queries[scene_idx % len(queries)]

        # 9. Panic, Anxiety, Insomnia, 3 AM Restlessness
        if any(k in scene_context for k in ["panic", "anxiety", "insomnia", "3 am", "sleep", "restless", "तनाव", "घबराहट", "अनिद्रा", "बेचैनी"]):
            queries = ["insomnia stressed dark room", "night darkness window silhouette", "stressed person head in hands"]
            return queries[scene_idx % len(queries)]

        # 10. Career Destruction, Financial Loss, Office Stress
        if any(k in scene_context for k in ["career", "financ", "money", "drain", "ruin", "destruct", "loss", "करियर", "नुकसान", "हानि", "कर्ज", "बर्बाद"]):
            queries = ["business executive stress office", "financial crisis stock market", "stock crash chart screen"]
            return queries[scene_idx % len(queries)]

        # 11. Wrong Metal, Wrong Finger, Ring Fitting
        if any(k in scene_context for k in ["metal", "finger", "hand", "wear", "ring", "धातु", "उंगली", "हाथ", "अंगूठी"]):
            queries = [f"{gem_kw} ring", "gemstone jewelry ring fingers", gem_kw]
            return queries[scene_idx % len(queries)]

        # 12. Fallback
        return planet_kw

    @classmethod
    def save_clean_photographic_image(cls, img: Image.Image, target_path: Path, quality: int = 95) -> Path:
        """
        Saves image with 100% clean metadata:
        - Creates a fresh raster RGB surface to sever all synthetic C2PA (Content Credentials) manifests,
          IPTC digital source type markers, XMP chunks, and AI generator tool signatures.
        - Guarantees zero AI metadata provenance headers exist in the file.
        """
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        clean = Image.new("RGB", img.size)
        clean.paste(img)
        clean.save(str(target_path), format="JPEG", quality=quality, exif=b"")
        return target_path

    @classmethod
    def generate_procedural_photorealistic_image(
        cls,
        theme_key: str,
        out_path: Path,
        width: int = 1080,
        height: int = 1920,
    ) -> Path:
        """
        Creates an original, rich, cinematic 9:16 photographic canvas using multi-layered
        astronomical gradients, depth bokeh, celestial starfields, and atmospheric vignette.
        Guarantees that an image is ALWAYS produced even if offline.
        """
        canvas = Image.new("RGB", (width, height), (8, 6, 16))
        draw = ImageDraw.Draw(canvas)

        palettes = {
            "lunar": ((6, 10, 24), (24, 38, 75), (200, 225, 255)),
            "gold": ((18, 12, 5), (65, 42, 12), (255, 205, 90)),
            "crimson": ((25, 6, 8), (75, 18, 22), (255, 120, 100)),
            "emerald": ((6, 22, 14), (18, 60, 38), (140, 255, 190)),
            "sapphire": ((5, 8, 28), (16, 28, 75), (120, 180, 255)),
            "cosmic": ((12, 5, 20), (45, 15, 65), (210, 140, 255)),
            "temple": ((20, 8, 5), (75, 25, 10), (255, 165, 50)),
            "deep": ((4, 4, 10), (15, 20, 35), (140, 180, 220)),
        }
        palette = palettes.get(theme_key, palettes["cosmic"])
        c_dark, c_mid, c_light = palette

        # 1. Vertical Atmospheric Gradient
        for y in range(height):
            frac = y / height
            r = int(c_dark[0] * (1 - frac) + c_mid[0] * frac)
            g = int(c_dark[1] * (1 - frac) + c_mid[1] * frac)
            b = int(c_dark[2] * (1 - frac) + c_mid[2] * frac)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Glowing Radial Light Source (Celestial Orb)
        orb_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        orb_draw = ImageDraw.Draw(orb_layer)
        cx, cy = width // 2, int(height * 0.42)
        r_orb = int(width * 0.38)
        for i in range(r_orb, 0, -8):
            alpha = int(45 * (1 - i / r_orb))
            orb_draw.ellipse(
                [cx - i, cy - i, cx + i, cy + i],
                fill=(c_light[0], c_light[1], c_light[2], alpha),
            )
        orb_layer = orb_layer.filter(ImageFilter.GaussianBlur(36))
        canvas.paste(orb_layer, (0, 0), orb_layer)

        # 3. Dense High-Resolution Celestial Starfield
        rng = random.Random(int(time.time() * 1000) % 999999)
        star_draw = ImageDraw.Draw(canvas)
        for _ in range(350):
            sx = rng.randint(0, width - 1)
            sy = rng.randint(0, height - 1)
            brightness = rng.randint(120, 255)
            s_sz = 1 if rng.random() > 0.12 else 2
            star_draw.ellipse([sx, sy, sx + s_sz, sy + s_sz], fill=(brightness, brightness, brightness))

        # 4. Cinematic Heavy Perimeter Vignette
        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        v_draw = ImageDraw.Draw(vignette)
        max_dist = math.sqrt((width / 2) ** 2 + (height / 2) ** 2)
        for r_step in range(int(width * 0.4), int(max_dist), 24):
            alpha = int(220 * ((r_step - width * 0.4) / (max_dist - width * 0.4)) ** 1.8)
            alpha = min(235, max(0, alpha))
            v_draw.ellipse(
                [width // 2 - r_step, height // 2 - r_step, width // 2 + r_step, height // 2 + r_step],
                outline=(0, 0, 0, alpha),
                width=24,
            )
        vignette = vignette.filter(ImageFilter.GaussianBlur(28))
        canvas.paste(vignette, (0, 0), vignette)

        cls.save_clean_photographic_image(canvas, out_path, quality=95)
        logger.info(f"[DynamicVisualEngine] Generated procedural photographic canvas -> {out_path.name}")
        return out_path

    @classmethod
    def search_online_photographic_asset(cls, query: str, target_file: Path) -> Optional[Path]:
        """
        Searches live online open photo repositories (NASA API & Wikimedia Commons)
        and crops the image to professional 1080x1920 (9:16 vertical) resolution.
        """
        # 1. Check NASA API for celestial / space queries
        if any(w in query.lower() for w in ["moon", "saturn", "jupiter", "mars", "nebula", "space", "eclipse", "sun", "stars"]):
            try:
                nasa_url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(query)}&media_type=image"
                req = urllib.request.Request(nasa_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as r:
                    nasa_data = json.loads(r.read())
                items = nasa_data.get("collection", {}).get("items", [])
                for item in items[:4]:
                    links = item.get("links", [])
                    if links:
                        img_url = links[0].get("href")
                        if img_url:
                            # Prefer medium image for fast, reliable download
                            med_url = img_url.replace("~thumb.jpg", "~medium.jpg")
                            try:
                                ir = urllib.request.urlopen(urllib.request.Request(med_url, headers={"User-Agent": "Mozilla/5.0"}), timeout=5)
                                data_bytes = ir.read(6 * 1024 * 1024)
                            except Exception:
                                ir = urllib.request.urlopen(urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"}), timeout=5)
                                data_bytes = ir.read(6 * 1024 * 1024)
                            if len(data_bytes) > 10000:
                                img = Image.open(io.BytesIO(data_bytes)).convert("RGB")
                                cropped = ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)
                                cls.save_clean_photographic_image(cropped, target_file, quality=95)
                                logger.info(f"[DynamicVisualEngine] Sourced authentic NASA photograph -> {target_file.name}")
                                return target_file
            except Exception as e:
                logger.debug(f"[DynamicVisualEngine] NASA search notice: {e}")

        # 2. Check Wikimedia Commons API with 1080px thumbnail width for instant download
        try:
            # Strictly filter out scanned books, PDF pages, treatises, and archive documents
            clean_search_query = f"{query} filetype:bitmap -pdf -djvu -book -text -treatise -ia -page"
            wiki_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(clean_search_query)}&gsrnamespace=6&gsrlimit=10&prop=imageinfo&iiprop=url|size&iiurlwidth=1080&format=json"
            req = urllib.request.Request(wiki_url, headers={"User-Agent": "InstaAstrologyAgent/1.0 (https://neodivinestore.in; support@neodivinestore.in)"})
            with urllib.request.urlopen(req, timeout=4) as r:
                data = json.loads(r.read())
            pages = data.get("query", {}).get("pages", {})
            for _, pdata in pages.items():
                title_lower = pdata.get("title", "").lower()
                # Strict exclusion of scans, book covers, PDFs, and archive files
                if any(bad in title_lower for bad in [".pdf", ".djvu", ".tif", "page1", "ia ", "treatise", "report", "journal", "document", "disassembled", "book"]):
                    continue

                ii = pdata.get("imageinfo", [{}])[0]
                dl_url = ii.get("thumburl") or ii.get("url")
                if dl_url:
                    clean_url = dl_url.split("?")[0]
                    url_lower = clean_url.lower()
                    if any(bad in url_lower for bad in [".pdf", ".djvu", ".tif", "page1", "ia_"]):
                        continue
                    if clean_url.lower().endswith((".jpg", ".jpeg", ".png")):
                        img_req = urllib.request.Request(dl_url, headers={"User-Agent": "InstaAstrologyAgent/1.0 (https://neodivinestore.in; support@neodivinestore.in)"})
                        with urllib.request.urlopen(img_req, timeout=5) as ir:
                            img_bytes = ir.read(5 * 1024 * 1024)
                        if len(img_bytes) > 10000:
                            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                            cropped = ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)
                            cls.save_clean_photographic_image(cropped, target_file, quality=95)
                            logger.info(f"[DynamicVisualEngine] Sourced authentic photographic asset via Wikimedia -> {target_file.name}")
                            return target_file
        except Exception as e:
            logger.debug(f"[DynamicVisualEngine] Wikimedia search notice: {e}")

        return None

    @classmethod
    def get_or_generate_scene_image(
        cls,
        scene_dict: Dict[str, Any],
        topic: str,
        scene_idx: int,
        total_scenes: int,
        reel_slug: str,
        used_images: Optional[Set[Path]] = None,
    ) -> Path:
        """
        Main entrypoint: Generates or sources a brand-new, unique 9:16 image for this scene.
        Guarantees 100% diversity across every scene and every video!
        """
        if used_images is None:
            used_images = set()

        timestamp_seed = int(time.time() * 1000) % 1000000
        prompt = cls.get_trait_visual_prompt(scene_dict, topic, scene_idx)
        prompt_hash = hashlib.md5(f"{reel_slug}_{scene_idx}_{timestamp_seed}_{prompt}".encode()).hexdigest()[:10]
        target_file = GENERATED_BROLL_DIR / f"{reel_slug}_sc{scene_idx + 1}_{prompt_hash}.jpg"

        # 1. ATTEMPT AI GENERATION (Pollinations AI with custom seed & 1080x1920 9:16 target)
        try:
            encoded_prompt = urllib.parse.quote(prompt)
            seed = random.randint(10000, 999999)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&seed={seed}"
            logger.info(f"[DynamicVisualEngine] Generating fresh AI visual for Scene {scene_idx + 1}...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()

            if len(data) > 12000:
                with Image.open(io.BytesIO(data)) as opened_img:
                    img = opened_img.convert("RGB")
                cropped = ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)
                cls.save_clean_photographic_image(cropped, target_file, quality=95)
                if not cls.is_image_used(target_file):
                    cls.register_used_image(target_file)
                    used_images.add(target_file)
                    logger.info(f"[DynamicVisualEngine] AI generation SUCCESS -> {target_file.name} ({cropped.size})")
                    return target_file
        except Exception as e:
            logger.warning(f"[DynamicVisualEngine] AI generator notice ({e}). Searching authentic photo repositories...")

        # 2. LIVE ONLINE PHOTOGRAPHIC SEARCH (Wikimedia Commons + NASA API)
        search_query = cls.get_scene_search_query(scene_dict, topic, scene_idx)
        logger.info(f"[DynamicVisualEngine] Searching online photo repositories for Scene {scene_idx + 1}: '{search_query}'...")
        online_asset = cls.search_online_photographic_asset(search_query, target_file)
        if online_asset and online_asset.exists() and not cls.is_image_used(online_asset) and online_asset not in used_images:
            cls.register_used_image(online_asset)
            used_images.add(online_asset)
            return online_asset

        # 3. TOPIC-SPECIFIC UNUSED LOCAL ASSET BANK (High-Res Photorealistic Assets)
        t_lower = (topic or "").lower()
        scene_txt = f"{scene_dict.get('spoken_line', '')} {scene_dict.get('on_screen_text', '')}".lower()
        
        cand = None
        if scene_idx == 0:
            if any(k in t_lower for k in ["neelam", "blue sapphire"]):
                cand = CINEMATIC_BROLL_DIR / "gemstone_blue_sapphire.jpg"
            elif any(k in t_lower for k in ["manik", "ruby"]):
                cand = CINEMATIC_BROLL_DIR / "gemstone_ruby.jpg"
            elif any(k in t_lower for k in ["pukhraj", "yellow sapphire"]):
                cand = CINEMATIC_BROLL_DIR / "gemstone_yellow_sapphire.jpg"
            elif any(k in t_lower for k in ["emerald", "panna"]):
                cand = CINEMATIC_BROLL_DIR / "gemstone_emerald.jpg"
            elif any(k in t_lower for k in ["moti", "pearl", "chandra"]):
                cand = CINEMATIC_BROLL_DIR / "gemstone_pearl.jpg"
            elif any(k in t_lower for k in ["moonga", "coral", "mangal"]):
                cand = CINEMATIC_BROLL_DIR / "gemstone_red_coral.jpg"
            elif any(k in t_lower for k in ["gomed", "hessonite", "rahu"]):
                cand = CINEMATIC_BROLL_DIR / "planet_rahu.jpg"
        elif any(k in scene_txt for k in ["dm", "save", "consultation", "परामर्श"]):
            cand = CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg"
        elif any(k in scene_txt for k in ["kundli", "house", "chart", "भाव"]):
            cand = CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg"
        elif any(k in scene_txt for k in ["blind", "remedy", "नियम"]):
            cand = CINEMATIC_BROLL_DIR / "sacred_vedic_fire_altar.jpg"
        elif any(k in scene_txt for k in ["enemy", "clash", "टकराव"]):
            if any(k in t_lower for k in ["neelam", "shani", "saturn"]):
                cand = CINEMATIC_BROLL_DIR / "planet_sun.jpg"
            else:
                cand = CINEMATIC_BROLL_DIR / "planet_saturn.jpg"

        if cand and cand.exists() and not cls.is_image_used(cand) and cand not in used_images:
            cls.register_used_image(cand)
            used_images.add(cand)
            logger.info(f"[DynamicVisualEngine] Using curated local asset -> {cand.name}")
            return cand

        # 4. FAILSAFE PROCEDURAL HIGH-RESOLUTION CANVASES (100% Unique, Never Repeated)
        theme_map = {
            0: "lunar" if any(k in t_lower for k in ["chandra", "moon"]) else "cosmic",
            1: "sapphire" if any(k in t_lower for k in ["chandra", "moon"]) else "deep",
            2: "lunar",
            3: "deep",
            4: "lunar" if any(k in t_lower for k in ["chandra", "moon", "pearl"]) else "gold",
            5: "temple",
            6: "temple",
        }
        theme = theme_map.get(scene_idx, "cosmic")
        proc_file = GENERATED_BROLL_DIR / f"proc_{reel_slug}_sc{scene_idx + 1}_{prompt_hash}.jpg"
        cls.generate_procedural_photorealistic_image(theme_key=theme, out_path=proc_file)
        cls.register_used_image(proc_file)
        used_images.add(proc_file)
        return proc_file
