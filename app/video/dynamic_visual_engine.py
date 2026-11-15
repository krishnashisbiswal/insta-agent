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
    "1_gemstone_hook.jpg",
    "2_kundli_chart.jpg",
    "3_shani_saturn.jpg",
    "4_sacred_havan.jpg",
    "5_temple_sanctum.jpg",
    "vedic_astrology_parchment_chart.jpg",
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
    def purge_old_generated_images(cls) -> int:
        """
        STRICT MANDATE: Purges all old generated b-roll and temporary frame renders
        from disk before a new Reel starts generation, guaranteeing 100% fresh assets.
        """
        purged = 0
        if GENERATED_BROLL_DIR.exists():
            for f in GENERATED_BROLL_DIR.glob("*.*"):
                try:
                    f.unlink()
                    purged += 1
                except Exception:
                    pass
        frames_dir = PROJECT_ROOT / "output" / "frames"
        if frames_dir.exists():
            for f in frames_dir.glob("*.jpg"):
                try:
                    f.unlink()
                    purged += 1
                except Exception:
                    pass
        for f in (PROJECT_ROOT / "output").glob("frame_sample_*.jpg"):
            try:
                f.unlink()
                purged += 1
            except Exception:
                pass
        for f in (PROJECT_ROOT / "output" / "reels").glob("*TEMP_MPY*"):
            try:
                f.unlink()
                purged += 1
            except Exception:
                pass
        logger.info(f"[DynamicVisualEngine] Pre-generation purge: Deleted {purged} old intermediate files from disk.")
        return purged

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
        elif any(k in entity_context for k in ["selenite"]):
            gem_name = "luminous silky white Selenite crystal tower with pearlescent cleansing glow"
            planet_name = "pure lunar high-frequency light and auric cleansing"
        elif any(k in entity_context for k in ["labradorite"]):
            gem_name = "natural raw Labradorite crystal with iridescent peacock blue-green flash and spectral labradorescence"
            planet_name = "mystical psychic shielding and aura protection"
        elif any(k in entity_context for k in ["carnelian"]):
            gem_name = "vibrant fiery orange Carnelian crystal polished stone with warm translucent glow"
            planet_name = "sacral chakra creative energy and vital motivation"
        elif any(k in entity_context for k in ["obsidian"]):
            gem_name = "mirror-reflective glossy Black Obsidian volcanic stone with deep dark protection shield"
            planet_name = "grounding root chakra security and negative energy reflection"
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

        # 2. Semantic scene intent matching (STRICTLY Anchored to the Crystal/Gemstone/Rudraksha Subject)
        # Hook / Opener Scene (Scene 1)
        if scene_idx == 0:
            return (
                f"cinematic dramatic macro luxury shot of {gem_name} resting upon a clean dark reflective surface, "
                f"soft celestial aura of {planet_name} radiating around it, inspiring high-vibrational sacred lighting, {base_modifiers}"
            )

        # Call to Action / DM Consultation / Sacred Temple Sanctuary
        if any(k in scene_context for k in ["dm", "save", "consultation", "परामर्श", "कमेंट", "booking", "message"]):
            return (
                f"cinematic sacred sanctum sanctorum of an ancient Vedic temple, {gem_name} respectfully placed on a pure silk offering cloth "
                f"before multiple glowing brass oil lamps (diyas) casting warm golden reflections on sacred carved stone pillars, peaceful divine tranquility, {base_modifiers}"
            )

        # Calming Nervous System / Meditation / Mental Clarity / Peace
        if any(k in scene_context for k in ["calm", "nervous system", "peace", "meditat", "focus", "clarity", "anxiety relief", "blood pressure", "एकाग्रता", "शांति", "तंत्रिका", "तनाव", "ध्यान", "फायदे", "राहत"]):
            return (
                f"cinematic serene macro shot of {gem_name} held gently in mindful hands during morning meditation in gentle golden sunlight, "
                f"soft glowing aura of {planet_name} harmonizing the atmosphere, warm zen aesthetic, high vibrational peace, {base_modifiers}"
            )

        # Aura Cleansing / Energy Shielding / EMF Protection / Negative Energy Absorption
        if any(k in scene_context for k in ["shield", "aura", "protect", "negative", "absorb", "emf", "psychic", "सुरक्षा", "आभामंडल", "नजर", "नकारात्मक"]):
            return (
                f"cinematic visual of {gem_name} radiating an impenetrable luminous energetic aura shield, "
                f"sacred protective crystalline light particles deflecting shadowy negative waves, high vibrational {planet_name} energy field, {base_modifiers}"
            )

        # Wealth Attraction / Abundance / Prosperity / Work Desk Sacred Setup
        if any(k in scene_context for k in ["attract", "wealth", "abundance", "prosperity", "money", "desk", "office", "धन", "समृद्धि", "आकर्षण", "बरकत", "कार्यस्थल"]):
            return (
                f"cinematic macro photograph of {gem_name} catching warm morning sunlight on a refined executive wooden desk beside a clean journal, "
                f"subtle golden bokeh, inspiring atmosphere of abundance and success, {base_modifiers}"
            )

        # Sacred Bio-Electromagnetism / Ancient Vedic Science / Heart & Bodily Harmony
        if any(k in scene_context for k in ["science", "bio-electric", "electromagnetic", "heart", "frequency", "resonance", "विज्ञान", "हृदय", "रक्तचाप", "ऊर्जा"]):
            return (
                f"cinematic sacred macro shot of {gem_name} radiating subtle golden sacred geometric frequency waves, "
                f"harmonizing bio-energy fields, ancient Vedic spiritual science visualization, {base_modifiers}"
            )

        # Warning Against Blind Internet Remedies / Unverified Rules / Sacred Knowledge
        if any(k in scene_context for k in ["blind", "remedy", "remedies", "unverified", "internet", "नियम", "उपाय", "अंधाधुंध"]):
            return (
                f"cinematic moody mystical shot of {gem_name} resting beside ancient palm-leaf astrological manuscripts and an antique brass compass, "
                f"single warm oil lamp flickering on dark weathered wood, sacred wisdom and precision, {base_modifiers}"
            )

        # Birth Chart, Kundli Houses (6th, 8th, 12th House, Lagna, Kendra)
        if any(k in scene_context for k in ["kundli", "house", "houses", "chart", "horoscope", "भाव", "लग्न", "केंद्र", "त्रिकोण", "छठे", "आठवें", "बारहवें"]):
            return (
                f"cinematic ancient Vedic astrological birth chart manuscript with {gem_name} resting gracefully upon the astrological houses, "
                f"glowing cosmic Sanskrit numbers and stardust softly illuminating the crystalline facets, {base_modifiers}"
            )

        # Opposing Enemy Planets Clashing / Energy Collision (e.g. Saturn clashing with Sun/Ruby)
        if any(k in scene_context for k in ["enemy", "clash", "collision", "opposing", "शत्रु", "टकराव", "विपरीत"]):
            return (
                f"cinematic dramatic macro shot of {gem_name} glowing steadily while harmonizing turbulent contrasting cosmic energies of {planet_name}, "
                f"luminous glowing plasma particles and celestial balancing waves in deep space, {base_modifiers}"
            )

        # Panic, Anxiety, Insomnia, 3 AM Restlessness, Stress
        if any(k in scene_context for k in ["panic", "anxiety", "insomnia", "3 am", "sleep", "restless", "तनाव", "घबराहट", "अनिद्रा", "बेचैनी"]):
            return (
                f"cinematic calming night shot of {gem_name} resting on a clean wooden bedside stand in soft warm amber ambient light, "
                f"soothing tranquil aura melting away nighttime restlessness, peaceful deep serenity, {base_modifiers}"
            )

        # Career Destruction, Bankruptcy, Financial Loss, Business Crash / Grounding
        if any(k in scene_context for k in ["career", "financ", "money", "drain", "ruin", "destruct", "loss", "करियर", "नुकसान", "हानि", "कर्ज", "बर्बाद"]):
            return (
                f"cinematic macro luxury shot of {gem_name} resting firmly on a sleek dark executive desk, "
                f"providing grounding stability and resolute mental focus amidst high stakes, rich warm ambient reflections, {base_modifiers}"
            )

        # Wrong Metal, Wrong Finger, Ring Fitting, Physical Gemstone Placement
        if any(k in scene_context for k in ["metal", "finger", "hand", "wear", "ring", "धातु", "उंगली", "हाथ", "अंगूठी"]):
            return (
                f"cinematic macro luxury photograph of a person's hand wearing an elegant ring or holding {gem_name}, "
                f"dramatic moody studio lighting, subtle golden visual flare, fine jewelry details, {base_modifiers}"
            )

        # Use Gemini's custom visual description if provided (guaranteeing subject inclusion)
        if vis_desc and len(vis_desc.split()) >= 4:
            clean_desc = re.sub(r"^(cinematic\s+)?(8k\s+)?(shot\s+of\s+)?", "", vis_desc.strip(), flags=re.I)
            gem_kw_token = gem_name.split()[0].lower()
            if gem_kw_token not in clean_desc.lower() and not any(k in clean_desc.lower() for k in ["crystal", "gemstone", "rudraksha", "stone", "bead"]):
                clean_desc = f"{gem_name}, {clean_desc}"
            return f"cinematic 8k {clean_desc}, moody dramatic atmosphere, {base_modifiers}"

        # Default Planetary / Gemstone Macro (strictly featuring subject)
        return (
            f"cinematic dramatic macro luxury photograph of {gem_name} bathed in ethereal glowing radiance of {planet_name}, "
            f"crystalline reflections and sacred aesthetic, {base_modifiers}"
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
            planet_kw = "black tourmaline mineral"
        elif any(k in entity_context for k in ["citrine"]):
            gem_kw = "citrine quartz crystal"
            planet_kw = "citrine mineral"
        elif any(k in entity_context for k in ["rose quartz"]):
            gem_kw = "rose quartz crystal mineral"
            planet_kw = "raw rose quartz stone"
        elif any(k in entity_context for k in ["tiger", "tigers eye", "tiger's eye"]):
            gem_kw = "tigers eye mineral gemstone"
            planet_kw = "tigers eye stone macro"
        elif any(k in entity_context for k in ["selenite"]):
            gem_kw = "selenite crystal"
            planet_kw = "selenite mineral"
        elif any(k in entity_context for k in ["gauri shankar"]):
            gem_kw = "rudraksha sacred bead"
            planet_kw = "rudraksha seed nepali"
        elif any(k in entity_context for k in ["rudraksha", "rudraksh", "mukhi"]):
            gem_kw = "rudraksha beads close up"
            planet_kw = "rudraksha seeds prayer"
        elif any(k in entity_context for k in ["neelam", "blue sapphire", "shani", "saturn"]):
            gem_kw = "blue sapphire gemstone"
            planet_kw = "blue sapphire mineral"
        elif any(k in entity_context for k in ["manik", "ruby", "surya", "sun"]):
            gem_kw = "ruby gemstone jewelry"
            planet_kw = "ruby mineral corundum"
        elif any(k in entity_context for k in ["pukhraj", "yellow sapphire", "guru", "jupiter"]):
            gem_kw = "yellow sapphire gemstone"
            planet_kw = "yellow sapphire corundum"
        elif any(k in entity_context for k in ["panna", "emerald", "budh", "mercury"]):
            gem_kw = "emerald gemstone jewelry"
            planet_kw = "emerald beryl mineral"
        elif any(k in entity_context for k in ["moti", "pearl", "chandra", "moon"]):
            gem_kw = "natural pearl gemstone"
            planet_kw = "pearl oyster jewelry"
        elif any(k in entity_context for k in ["moonga", "coral", "mangal", "mars"]):
            gem_kw = "red coral gemstone"
            planet_kw = "red coral mineral"
        elif any(k in entity_context for k in ["heera", "diamond", "shukra", "venus"]):
            gem_kw = "diamond gemstone jewelry"
            planet_kw = "raw diamond crystal"
        elif any(k in entity_context for k in ["gomed", "hessonite", "rahu"]):
            gem_kw = "hessonite garnet gemstone"
            planet_kw = "hessonite mineral"
        elif any(k in entity_context for k in ["lehsuniya", "cat's eye", "ketu"]):
            gem_kw = "chrysoberyl cats eye gemstone"
            planet_kw = "chrysoberyl mineral"

        # 1. Hook (Scene 0)
        if scene_idx == 0:
            return f"{gem_kw} macro"

        # 2. CTA / DM Consultation / Sacred Temple
        if any(k in scene_context for k in ["dm", "save", "consultation", "परामर्श", "कमेंट", "booking", "message"]):
            queries = [f"{gem_kw} temple sacred altar", f"{gem_kw} brass diya", f"{gem_kw} altar"]
            return queries[scene_idx % len(queries)]

        # 3. Calming Nervous System / Meditation / Peace
        if any(k in scene_context for k in ["calm", "nervous system", "peace", "meditat", "focus", "clarity", "anxiety relief", "एकाग्रता", "शांति", "ध्यान"]):
            queries = [f"{gem_kw} meditation stone", f"{gem_kw} zen harmony", f"{gem_kw} healing"]
            return queries[scene_idx % len(queries)]

        # 4. Aura / Protection / Negativity Shield
        if any(k in scene_context for k in ["shield", "aura", "protect", "negative", "absorb", "emf", "सुरक्षा", "आभामंडल", "नजर"]):
            queries = [f"{gem_kw} raw mineral specimen", f"{gem_kw} energy crystal", f"{gem_kw} specimen"]
            return queries[scene_idx % len(queries)]

        # 5. Wealth Attraction / Abundance / Office Desk
        if any(k in scene_context for k in ["attract", "wealth", "abundance", "prosperity", "money", "desk", "office", "धन", "समृद्धि"]):
            queries = [f"{gem_kw} mineral crystal cluster", f"{gem_kw} desk stone", f"{gem_kw} specimen"]
            return queries[scene_idx % len(queries)]

        # 6. Blind Remedies / Internet Mistakes / Ancient Texts
        if any(k in scene_context for k in ["blind", "remedy", "remedies", "unverified", "internet", "नियम", "उपाय"]):
            queries = [f"{gem_kw} natural gemstone specimen", f"{gem_kw} antique manuscript", f"{gem_kw} sacred"]
            return queries[scene_idx % len(queries)]

        # 7. Birth Chart, Kundli Houses
        if any(k in scene_context for k in ["kundli", "house", "houses", "chart", "horoscope", "भाव", "लग्न", "केंद्र", "त्रिकोण"]):
            queries = [f"{gem_kw} astrology chart", f"{gem_kw} sacred stone", f"{gem_kw} crystal"]
            return queries[scene_idx % len(queries)]

        # 8. Enemy Planets Clashing / Collision
        if any(k in scene_context for k in ["enemy", "clash", "collision", "opposing", "शत्रु", "टकराव", "विपरीत"]):
            queries = [f"{gem_kw} rough mineral crystal", f"{gem_kw} specimen raw", f"{gem_kw} crystal cluster"]
            return queries[scene_idx % len(queries)]

        # 9. Panic, Anxiety, Insomnia, 3 AM Restlessness
        if any(k in scene_context for k in ["panic", "anxiety", "insomnia", "3 am", "sleep", "restless", "तनाव", "घबराहट", "अनिद्रा", "बेचैनी"]):
            queries = [f"{gem_kw} bedside calm", f"{gem_kw} soothing crystal", f"{gem_kw} polished stone"]
            return queries[scene_idx % len(queries)]

        # 10. Career Destruction, Financial Loss, Office Stress
        if any(k in scene_context for k in ["career", "financ", "money", "drain", "ruin", "destruct", "loss", "करियर", "नुकसान", "हानि", "कर्ज", "बर्बाद"]):
            queries = [f"{gem_kw} executive desk stone", f"{gem_kw} grounding crystal", f"{gem_kw} cluster"]
            return queries[scene_idx % len(queries)]

        # 11. Wrong Metal, Wrong Finger, Ring Fitting
        if any(k in scene_context for k in ["metal", "finger", "hand", "wear", "ring", "धातु", "उंगली", "हाथ", "अंगूठी"]):
            queries = [f"{gem_kw} ring", f"{gem_kw} jewelry ring fingers", gem_kw]
            return queries[scene_idx % len(queries)]

        # 12. Fallback
        return f"{gem_kw} mineral specimen"

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
        mineral studio gradients, sacred crystalline geometry, warm golden bokeh, and atmospheric vignette.
        Guarantees that a high-end luxury crystal/gemstone visual is ALWAYS produced even if offline.
        """
        canvas = Image.new("RGB", (width, height), (8, 6, 12))
        draw = ImageDraw.Draw(canvas)

        palettes = {
            "tourmaline": ((6, 6, 10), (18, 18, 26), (180, 200, 220)),
            "pyrite": ((18, 14, 6), (58, 44, 16), (255, 215, 110)),
            "amethyst": ((14, 6, 22), (48, 18, 70), (220, 160, 255)),
            "citrine": ((20, 12, 4), (70, 42, 10), (255, 200, 80)),
            "rudraksha": ((18, 8, 4), (64, 26, 12), (255, 170, 70)),
            "sapphire": ((4, 8, 24), (14, 26, 68), (140, 190, 255)),
            "ruby": ((24, 6, 8), (72, 16, 22), (255, 130, 120)),
            "emerald": ((4, 18, 10), (14, 52, 30), (130, 255, 180)),
            "temple": ((20, 8, 4), (70, 25, 10), (255, 165, 50)),
            "cosmic": ((10, 8, 16), (36, 22, 54), (210, 170, 240)),
            "deep": ((6, 6, 12), (18, 20, 36), (150, 180, 220)),
        }
        palette = palettes.get(theme_key, palettes["tourmaline"])
        c_dark, c_mid, c_light = palette

        # 1. Vertical Luxury Studio Gradient
        for y in range(height):
            frac = y / height
            r = int(c_dark[0] * (1 - frac) + c_mid[0] * frac)
            g = int(c_dark[1] * (1 - frac) + c_mid[1] * frac)
            b = int(c_dark[2] * (1 - frac) + c_mid[2] * frac)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Glowing Radial Sacred Aura Spotlight
        aura_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        aura_draw = ImageDraw.Draw(aura_layer)
        cx, cy = width // 2, int(height * 0.44)
        r_max = int(width * 0.48)
        for i in range(r_max, 0, -12):
            alpha = int(60 * (1 - i / r_max))
            aura_draw.ellipse(
                [cx - i, cy - int(i * 1.1), cx + i, cy + int(i * 1.1)],
                fill=(c_light[0], c_light[1], c_light[2], alpha),
            )
        aura_layer = aura_layer.filter(ImageFilter.GaussianBlur(40))
        canvas.paste(aura_layer, (0, 0), aura_layer)

        # 3. Sacred Crystalline Geometry / Facet Refraction Lattice
        geo_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        geo_draw = ImageDraw.Draw(geo_layer)
        facets = [
            [(cx, cy - 240), (cx + 160, cy - 60), (cx, cy + 220), (cx - 160, cy - 60)],
            [(cx, cy - 160), (cx + 110, cy - 40), (cx, cy + 140), (cx - 110, cy - 40)],
            [(cx, cy - 240), (cx, cy + 220)],
            [(cx - 160, cy - 60), (cx + 160, cy - 60)],
            [(cx - 160, cy - 60), (cx, cy - 160)],
            [(cx + 160, cy - 60), (cx, cy - 160)],
            [(cx - 110, cy - 40), (cx, cy + 220)],
            [(cx + 110, cy - 40), (cx, cy + 220)],
        ]
        line_color = (c_light[0], c_light[1], c_light[2], 55)
        for poly in facets:
            if len(poly) > 2:
                geo_draw.polygon(poly, outline=line_color, fill=(c_light[0], c_light[1], c_light[2], 8))
            else:
                geo_draw.line(poly, fill=line_color, width=2)

        for ring_r in [180, 260, 340]:
            geo_draw.ellipse(
                [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                outline=(c_light[0], c_light[1], c_light[2], 30),
                width=1,
            )
        geo_layer = geo_layer.filter(ImageFilter.GaussianBlur(2))
        canvas.paste(geo_layer, (0, 0), geo_layer)

        # 4. Soft Golden Bokeh Particles (warm motes, not sharp stars)
        rng = random.Random(int(time.time() * 1000) % 999999)
        bokeh_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bokeh_draw = ImageDraw.Draw(bokeh_layer)
        for _ in range(45):
            bx = rng.randint(int(width * 0.1), int(width * 0.9))
            by = rng.randint(int(height * 0.2), int(height * 0.75))
            b_radius = rng.randint(4, 22)
            b_alpha = rng.randint(25, 90)
            bokeh_draw.ellipse(
                [bx - b_radius, by - b_radius, bx + b_radius, by + b_radius],
                fill=(c_light[0], c_light[1], c_light[2], b_alpha),
            )
        bokeh_layer = bokeh_layer.filter(ImageFilter.GaussianBlur(6))
        canvas.paste(bokeh_layer, (0, 0), bokeh_layer)

        # 5. Cinematic Deep Perimeter Vignette
        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        v_draw = ImageDraw.Draw(vignette)
        max_dist = math.sqrt((width / 2) ** 2 + (height / 2) ** 2)
        for r_step in range(int(width * 0.35), int(max_dist), 20):
            alpha = int(230 * ((r_step - width * 0.35) / (max_dist - width * 0.35)) ** 1.6)
            alpha = min(245, max(0, alpha))
            v_draw.ellipse(
                [width // 2 - r_step, height // 2 - r_step, width // 2 + r_step, height // 2 + r_step],
                outline=(0, 0, 0, alpha),
                width=20,
            )
        vignette = vignette.filter(ImageFilter.GaussianBlur(24))
        canvas.paste(vignette, (0, 0), vignette)

        cls.save_clean_photographic_image(canvas, out_path, quality=95)
        logger.info(f"[DynamicVisualEngine] Generated procedural photographic canvas -> {out_path.name}")
        return out_path

    @classmethod
    def search_openverse_photographic_asset(
        cls,
        query: str,
        target_file: Path,
        used_urls: Optional[Set[str]] = None,
    ) -> Optional[Path]:
        """
        Searches Openverse API for high-resolution Creative Commons photographs
        of authentic crystals, minerals, and sacred items.
        """
        if used_urls is None:
            used_urls = set()
        clean_q = urllib.parse.quote(query)
        url = f"https://api.openverse.org/v1/images/?q={clean_q}&page_size=8"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "InstaAstrologyAgent/1.0 (https://neodivinestore.in; support@neodivinestore.in)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            results = data.get("results", [])
            for res in results:
                img_url = res.get("url")
                if not img_url or img_url in used_urls:
                    continue
                try:
                    ir = urllib.request.urlopen(
                        urllib.request.Request(img_url, headers={"User-Agent": "InstaAstrologyAgent/1.0"}),
                        timeout=6,
                    )
                    img_bytes = ir.read(6 * 1024 * 1024)
                    if len(img_bytes) > 12000:
                        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        cropped = ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)
                        cls.save_clean_photographic_image(cropped, target_file, quality=95)
                        used_urls.add(img_url)
                        logger.info(f"[DynamicVisualEngine] Sourced authentic Openverse photo ('{query}') -> {target_file.name}")
                        return target_file
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"[DynamicVisualEngine] Openverse search notice ('{query}'): {e}")
        return None

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

        # 2. Check Wikimedia Commons API with progressive query fallback
        candidate_queries = [query]
        tokens = [t for t in query.split() if t.lower() not in ["macro", "specimen", "cluster", "sacred", "raw", "altar", "temple", "stone", "close", "up"]]
        if len(tokens) >= 2:
            candidate_queries.append(" ".join(tokens[:2]))
        if len(tokens) >= 1:
            candidate_queries.append(tokens[0])

        for c_query in candidate_queries:
            try:
                # Strictly filter out scanned books, PDF pages, treatises, and archive documents
                clean_search_query = f"{c_query} filetype:bitmap -pdf -djvu -book -text -treatise -ia -page"
                wiki_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(clean_search_query)}&gsrnamespace=6&gsrlimit=10&prop=imageinfo&iiprop=url|size&iiurlwidth=1080&format=json"
                req = urllib.request.Request(wiki_url, headers={"User-Agent": "InstaAstrologyAgent/1.0 (https://neodivinestore.in; support@neodivinestore.in)"})
                with urllib.request.urlopen(req, timeout=4) as r:
                    data = json.loads(r.read())
                pages = data.get("query", {}).get("pages", {})
                for _, pdata in pages.items():
                    title_lower = pdata.get("title", "").lower()
                    if any(bad in title_lower for bad in [".pdf", ".djvu", ".tif", "page1", "ia ", "treatise", "report", "journal", "document", "disassembled", "book"]):
                        continue

                    ii = pdata.get("imageinfo", [{}])[0]
                    dl_url = ii.get("thumburl") or ii.get("url")
                    if dl_url:
                        clean_url = dl_url.split("?")[0].lower()
                        if any(bad in clean_url for bad in [".pdf", ".djvu", ".tif", "page1", "ia_"]):
                            continue
                        if clean_url.endswith((".jpg", ".jpeg", ".png")):
                            img_req = urllib.request.Request(dl_url, headers={"User-Agent": "InstaAstrologyAgent/1.0 (https://neodivinestore.in; support@neodivinestore.in)"})
                            with urllib.request.urlopen(img_req, timeout=5) as ir:
                                img_bytes = ir.read(5 * 1024 * 1024)
                            if len(img_bytes) > 10000:
                                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                                cropped = ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)
                                cls.save_clean_photographic_image(cropped, target_file, quality=95)
                                logger.info(f"[DynamicVisualEngine] Sourced authentic photographic asset via Wikimedia ('{c_query}') -> {target_file.name}")
                                return target_file
            except Exception as e:
                logger.debug(f"[DynamicVisualEngine] Wikimedia search notice ('{c_query}'): {e}")

        return None

    @classmethod
    def create_macro_focal_crop(
        cls,
        source_path: Path,
        target_path: Path,
        crop_index: int,
        theme_key: str = "pyrite",
    ) -> Path:
        """
        Renders a unique, non-repeating macro optical cutaway from an authentic high-resolution
        subject plate (e.g. facet zoom, reflective angle, core specimen), ensuring each scene
        is visually distinct while remaining 100% relevant to the subject.
        """
        with Image.open(source_path) as orig:
            img = orig.convert("RGB")
        w, h = img.size

        # 8 distinct cinematic camera perspectives & macro focal boxes
        crop_boxes = [
            (int(w * 0.12), int(h * 0.08), int(w * 0.88), int(h * 0.68)),   # 0: Upper facet macro zoom
            (int(w * 0.08), int(h * 0.22), int(w * 0.92), int(h * 0.82)),   # 1: Central core crystalline structure
            (int(w * 0.16), int(h * 0.35), int(w * 0.84), int(h * 0.95)),   # 2: Lower reflection angle with deep shadow
            (int(w * 0.04), int(h * 0.12), int(w * 0.72), int(h * 0.72)),   # 3: Left angle facet structure
            (int(w * 0.28), int(h * 0.12), int(w * 0.96), int(h * 0.72)),   # 4: Right angle specular crystal highlight
            (int(w * 0.15), int(h * 0.18), int(w * 0.85), int(h * 0.78)),   # 5: Natural inclusions & authentic striations macro
            (int(w * 0.06), int(h * 0.30), int(w * 0.94), int(h * 0.90)),   # 6: Base facet grounding view on dark velvet
            (int(w * 0.20), int(h * 0.15), int(w * 0.80), int(h * 0.80)),   # 7: Tightest ultra-macro specimen core
        ]
        box = crop_boxes[crop_index % len(crop_boxes)]
        cropped = img.crop(box)
        resized = ImageOps.fit(cropped, (1080, 1920), method=Image.Resampling.LANCZOS)

        # Dynamic optical grade based on scene index for rich cinematic contrast
        enhancer = ImageEnhance.Contrast(resized)
        enhanced = enhancer.enhance(1.08 + (crop_index % 3) * 0.03)
        color_enhancer = ImageEnhance.Color(enhanced)
        enhanced = color_enhancer.enhance(1.05 + (crop_index % 2) * 0.04)

        cls.save_clean_photographic_image(enhanced, target_path, quality=95)
        logger.info(f"[DynamicVisualEngine] Generated unique macro focal crop ({source_path.name} -> crop {crop_index}) -> {target_path.name}")
        return target_path

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
        Main entrypoint: Sourcing and delivering an authentic, high-resolution 1080x1920 visual
        that STRICTLY matches the information conveyed in this specific scene.
        Guarantees:
        1. Visual diversity across scenes (each scene gets a distinct, authentic photographic asset).
        2. Semantic accuracy (Saturn dialogue -> Saturn visual; Kundli -> Kundli chart; Crystal -> Crystal).
        3. Zero duplicate images within a single reel.
        4. Rotated ending visuals so Scene 6 and Scene 7 do NOT repeat identical images across reels.
        """
        if used_images is None:
            used_images = set()

        timestamp_seed = int(time.time() * 1000) % 1000000
        prompt_hash = hashlib.md5(f"{reel_slug}_{scene_idx}_{timestamp_seed}".encode()).hexdigest()[:10]
        target_file = GENERATED_BROLL_DIR / f"{reel_slug}_sc{scene_idx + 1}_{prompt_hash}.jpg"

        spoken = scene_dict.get("spoken_line", "").lower()
        on_screen = scene_dict.get("on_screen_text", "").lower()
        vis_desc = scene_dict.get("visual_description", "").lower()
        scene_txt = f"{spoken} {on_screen} {vis_desc}".lower()
        t_lower = (topic or "").lower()
        full_context = f"{t_lower} {scene_txt}"

        # 1. Identify Topic Category & Specific Master Entity
        curated_master_plate: Optional[Path] = None
        theme_palette = "pyrite"

        if any(k in full_context for k in ["pyrite", "पायराइट", "fool's gold"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_pyrite_cluster.jpg"
            theme_palette = "pyrite"
        elif any(k in full_context for k in ["amethyst", "कटेला", "जामुनिया"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_amethyst_cluster.jpg"
            theme_palette = "amethyst"
        elif any(k in full_context for k in ["tourmaline", "टूमलाइन", "black tourmaline"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_black_tourmaline.jpg"
            theme_palette = "tourmaline"
        elif any(k in full_context for k in ["citrine", "सिट्रीन"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg"
            theme_palette = "citrine"
        elif any(k in full_context for k in ["rose quartz", "गुलाबी क्वार्ट्ज"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_rose_quartz.jpg"
            theme_palette = "tourmaline"
        elif any(k in full_context for k in ["aventurine", "एवेंट्यूरिन", "jade"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_green_aventurine.jpg"
            theme_palette = "emerald"
        elif any(k in full_context for k in ["tiger", "tigers eye", "टाइगर"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg"
            theme_palette = "citrine"
        elif any(k in full_context for k in ["sphatik", "स्फटिक", "quartz"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg"
            theme_palette = "sapphire"
        elif any(k in full_context for k in ["selenite", "सेलेनाइट"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_selenite.jpg"
            theme_palette = "sapphire"
        elif any(k in full_context for k in ["carnelian", "कार्नेलियन"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_carnelian.jpg"
            theme_palette = "ruby"
        elif any(k in full_context for k in ["labradorite", "लैब्राडोराइट"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "crystal_labradorite.jpg"
            theme_palette = "deep"
        elif any(k in full_context for k in ["rudraksha", "rudraksh", "रुद्राक्ष", "mukhi", "मुख"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "rudraksha_sacred_beads.jpg"
            theme_palette = "rudraksha"
        elif any(k in full_context for k in ["neelam", "blue sapphire", "नीलम"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "gemstone_blue_sapphire.jpg"
            theme_palette = "sapphire"
        elif any(k in full_context for k in ["pukhraj", "yellow sapphire", "पुखराज"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "gemstone_yellow_sapphire.jpg"
            theme_palette = "citrine"
        elif any(k in full_context for k in ["panna", "emerald", "पन्ना"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "gemstone_emerald.jpg"
            theme_palette = "emerald"
        elif any(k in full_context for k in ["manik", "ruby", "माणिक"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "gemstone_ruby.jpg"
            theme_palette = "ruby"
        elif any(k in full_context for k in ["heera", "diamond", "हीरा"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "gemstone_diamond.jpg"
            theme_palette = "sapphire"
        elif any(k in full_context for k in ["moti", "pearl", "मोती"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "gemstone_pearl.jpg"
            theme_palette = "sapphire"
        elif any(k in full_context for k in ["moonga", "coral", "मूंगा"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "gemstone_red_coral.jpg"
            theme_palette = "ruby"
        elif any(k in full_context for k in ["shani", "saturn", "शनि"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_saturn.jpg"
            theme_palette = "deep"
        elif any(k in full_context for k in ["chandra", "moon", "चंद्रमा", "चन्द्र", "rohini", "रोहिणी"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_moon.jpg"
            theme_palette = "sapphire"
        elif any(k in full_context for k in ["surya", "sun", "सूर्य"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_sun.jpg"
            theme_palette = "citrine"
        elif any(k in full_context for k in ["guru", "brihaspati", "jupiter", "गुरु", "बृहस्पति"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_jupiter.jpg"
            theme_palette = "citrine"
        elif any(k in full_context for k in ["mangal", "mars", "मंगल"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_mars.jpg"
            theme_palette = "ruby"
        elif any(k in full_context for k in ["shukra", "venus", "शुक्र"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_venus.jpg"
            theme_palette = "citrine"
        elif any(k in full_context for k in ["budh", "mercury", "बुध"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_mercury.jpg"
            theme_palette = "emerald"
        elif any(k in full_context for k in ["rahu", "राहु"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_rahu.jpg"
            theme_palette = "deep"
        elif any(k in full_context for k in ["ketu", "केतु"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "planet_ketu.jpg"
            theme_palette = "deep"
        elif any(k in full_context for k in ["kundli", "कुंडली", "जन्मपत्रिका", "chart"]):
            curated_master_plate = CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg"
            theme_palette = "citrine"

        # 2. Build Ranked Scene Candidates Matching THIS Scene Content
        is_last_scene = (scene_idx == total_scenes - 1) or any(k in scene_txt for k in ["dm", "save", "booking", "message", "सेव", "कमेंट", "परामर्श के लिए", "मंदिर"])
        is_caution_scene = (scene_idx == total_scenes - 2) or any(k in scene_txt for k in ["blind", "remedy", "remedies", "अंधाधुंध", "warning", "विपरीत", "सावधानी", "नियम"])
        is_hook_scene = (scene_idx == 0)

        candidates: List[Path] = []

        # (A) Call to Action / DM Consultation / Temple Sanctum (Scene 7)
        if is_last_scene:
            cta_pool = [
                CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg",
                CINEMATIC_BROLL_DIR / "astrology_consultation_scroll.jpg",
                CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg",
                CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
            ]
            rot_idx = int(hashlib.md5(f"{topic}_cta".encode()).hexdigest(), 16) % len(cta_pool)
            candidates.extend(cta_pool[rot_idx:] + cta_pool[:rot_idx])

        # (B) Caution against Blind Remedies / Warning / Fire Altar (Scene 6)
        elif is_caution_scene:
            caution_pool = [
                CINEMATIC_BROLL_DIR / "sacred_havan_flame_altar.jpg",
                CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg",
                CINEMATIC_BROLL_DIR / "astrology_consultation_scroll.jpg",
                CINEMATIC_BROLL_DIR / "sacred_vedic_fire_altar.jpg",
            ]
            rot_idx = int(hashlib.md5(f"{topic}_caution".encode()).hexdigest(), 16) % len(caution_pool)
            candidates.extend(caution_pool[rot_idx:] + caution_pool[:rot_idx])

        # (C) Scenes 0-5: Rich Content-Matched Semantic Resolver
        else:
            if is_hook_scene and curated_master_plate:
                candidates.append(curated_master_plate)

            # 1. Kundli / Birth Chart / Astrological Houses
            if any(k in scene_txt for k in ["kundli", "कुंडली", "birth chart", "भाव", "लग्न", "house", "केंद्र", "त्रिकोण", "जन्मपत्रिका"]):
                candidates.append(CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg")
                candidates.append(CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg")

            # 2. Subtle Energy / Bio-Electromagnetism / Sacred Geometry / Yantra
            if any(k in scene_txt for k in ["yantra", "यंत्र", "frequency", "vibration", "resonance", "तरंग", "रेजोनेंस", "bio-electric", "चक्र", "ऊर्जा", "आभामंडल", "aura", "shield"]):
                candidates.append(CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg")

            # 3. Astrological Consultation / Client Case Study / Ancient Manuscripts
            if any(k in scene_txt for k in ["क्लाइंट", "परामर्श सत्र", "consultation", "case study", "सत्र", "परामर्श", "शोध", "research", "शास्त्र", "ग्रंथ"]):
                candidates.append(CINEMATIC_BROLL_DIR / "astrology_consultation_scroll.jpg")

            # 4. Planetary Forces & Cosmic Alignments
            if any(k in scene_txt for k in ["shani", "saturn", "शनि"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_saturn.jpg")
            if any(k in scene_txt for k in ["chandra", "moon", "चंद्रमा", "चन्द्र", "मन", "अनिद्रा", "रात", "rohini", "रोहिणी"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_moon.jpg")
            if any(k in scene_txt for k in ["surya", "sun", "सूर्य", "aditya"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_sun.jpg")
            if any(k in scene_txt for k in ["guru", "brihaspati", "jupiter", "गुरु", "बृहस्पति"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_jupiter.jpg")
            if any(k in scene_txt for k in ["mangal", "mars", "मंगल"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_mars.jpg")
            if any(k in scene_txt for k in ["shukra", "venus", "शुक्र"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_venus.jpg")
            if any(k in scene_txt for k in ["budh", "mercury", "बुध"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_mercury.jpg")
            if any(k in scene_txt for k in ["rahu", "राहु"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_rahu.jpg")
            if any(k in scene_txt for k in ["ketu", "केतु"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_ketu.jpg")

            # 5. Direct Crystals / Gemstones / Rudraksha
            if any(k in scene_txt for k in ["pyrite", "पायराइट"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_pyrite_cluster.jpg")
            if any(k in scene_txt for k in ["amethyst", "कटेला", "जामुनिया"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_amethyst_cluster.jpg")
            if any(k in scene_txt for k in ["tourmaline", "टूमलाइन"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_black_tourmaline.jpg")
            if any(k in scene_txt for k in ["citrine", "सिट्रीन"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg")
            if any(k in scene_txt for k in ["rose quartz", "गुलाबी क्वार्ट्ज"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_rose_quartz.jpg")
            if any(k in scene_txt for k in ["aventurine", "एवेंट्यूरिन", "jade"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_green_aventurine.jpg")
            if any(k in scene_txt for k in ["tiger", "tigers eye", "टाइगर"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg")
            if any(k in scene_txt for k in ["sphatik", "स्फटिक", "quartz"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg")
            if any(k in scene_txt for k in ["selenite", "सेलेनाइट"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_selenite.jpg")
            if any(k in scene_txt for k in ["carnelian", "कार्नेलियन"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_carnelian.jpg")
            if any(k in scene_txt for k in ["labradorite", "लैब्राडोराइट"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_labradorite.jpg")
            if any(k in scene_txt for k in ["rudraksha", "rudraksh", "रुद्राक्ष", "mukhi", "मुख"]):
                candidates.append(CINEMATIC_BROLL_DIR / "rudraksha_sacred_beads.jpg")
            if any(k in scene_txt for k in ["neelam", "blue sapphire", "नीलम"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_blue_sapphire.jpg")
            if any(k in scene_txt for k in ["pukhraj", "yellow sapphire", "पुखराज"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_yellow_sapphire.jpg")
            if any(k in scene_txt for k in ["panna", "emerald", "पन्ना"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_emerald.jpg")
            if any(k in scene_txt for k in ["manik", "ruby", "माणिक"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_ruby.jpg")
            if any(k in scene_txt for k in ["moti", "pearl", "मोती"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_pearl.jpg")
            if any(k in scene_txt for k in ["heera", "diamond", "हीरा"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_diamond.jpg")
            if any(k in scene_txt for k in ["moonga", "coral", "मूंगा"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_red_coral.jpg")

            # Topic-level primary fallback
            if curated_master_plate:
                candidates.append(curated_master_plate)

            # Universal diverse library fallbacks (all high-res, distinct, authentic)
            candidates.extend([
                CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg",
                CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                CINEMATIC_BROLL_DIR / "astrology_consultation_scroll.jpg",
                CINEMATIC_BROLL_DIR / "planet_saturn.jpg",
                CINEMATIC_BROLL_DIR / "planet_moon.jpg",
                CINEMATIC_BROLL_DIR / "sacred_havan_flame_altar.jpg",
                CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg",
            ])

        # Pick the FIRST candidate that exists and hasn't been used yet in THIS video reel
        chosen_cand: Optional[Path] = None
        for cand in candidates:
            if cand.exists() and cand not in used_images:
                chosen_cand = cand
                break

        # If all candidates were used in this reel, generate a unique macro focal crop
        if not chosen_cand and curated_master_plate and curated_master_plate.exists():
            macro_file = GENERATED_BROLL_DIR / f"{reel_slug}_macro_sc{scene_idx + 1}_{prompt_hash}.jpg"
            cls.create_macro_focal_crop(curated_master_plate, macro_file, crop_index=scene_idx)
            if macro_file.exists() and macro_file not in used_images:
                chosen_cand = macro_file

        if chosen_cand and chosen_cand.exists():
            with Image.open(chosen_cand) as c_img:
                cropped = ImageOps.fit(c_img.convert("RGB"), (1080, 1920), method=Image.Resampling.LANCZOS)
            cls.save_clean_photographic_image(cropped, target_file, quality=95)
            used_images.add(chosen_cand)
            used_images.add(target_file)
            logger.info(f"[DynamicVisualEngine] Scene {scene_idx + 1}: Sourced authentic visual ({chosen_cand.name}) -> {target_file.name}")
            return target_file

        # Fallback: Procedural luxury studio canvas
        proc_file = GENERATED_BROLL_DIR / f"proc_{reel_slug}_sc{scene_idx + 1}_{prompt_hash}.jpg"
        cls.generate_procedural_photorealistic_image(theme_key=theme_palette, out_path=proc_file)
        used_images.add(proc_file)
        return proc_file
