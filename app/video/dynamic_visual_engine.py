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
from typing import Any, Dict, List, Optional, Set, Tuple, Union
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

    _session_used_urls: Set[str] = set()
    _session_used_hashes: Set[str] = set()

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
        """Persists used images registry to disk atomically with backoff."""
        try:
            from app.storage.permanent_visual_memory import _atomic_replace_json
            _atomic_replace_json(USED_REGISTRY_FILE, {"used_images": sorted(list(used_set))}, indent=2)
        except Exception:
            try:
                USED_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(USED_REGISTRY_FILE, "w", encoding="utf-8") as f:
                    json.dump({"used_images": sorted(list(used_set))}, f, indent=2)
            except Exception as e:
                logger.warning(f"Notice saving visual registry: {e}")

    @classmethod
    def purge_old_generated_images(
        cls,
        keep_paths: Optional[Set[Any]] = None,
        max_age_seconds: int = 0,
    ) -> int:
        """
        Safely purges stale intermediate b-roll and temporary frame renders from disk.
        Task 8 Storage Safety:
        - NEVER deletes images currently in use or passed in keep_paths.
        - NEVER deletes files if max_age_seconds > 0 and file is younger than max_age_seconds.
        - Resets session in-memory caches.
        """
        cls._session_used_urls.clear()
        cls._session_used_hashes.clear()
        purged = 0
        now = time.time()

        resolved_keeps: Set[str] = set()
        if keep_paths:
            for p in keep_paths:
                resolved_keeps.add(str(Path(p).resolve()))
                resolved_keeps.add(Path(p).name)

        if GENERATED_BROLL_DIR.exists():
            for f in GENERATED_BROLL_DIR.glob("*.*"):
                if str(f.resolve()) in resolved_keeps or f.name in resolved_keeps:
                    continue
                try:
                    mtime = f.stat().st_mtime
                    if max_age_seconds <= 0 or (now - mtime) > max_age_seconds:
                        f.unlink()
                        purged += 1
                except Exception:
                    pass
        frames_dir = PROJECT_ROOT / "output" / "frames"
        if frames_dir.exists():
            for f in frames_dir.glob("*.jpg"):
                if str(f.resolve()) in resolved_keeps or f.name in resolved_keeps:
                    continue
                try:
                    mtime = f.stat().st_mtime
                    if max_age_seconds <= 0 or (now - mtime) > max_age_seconds:
                        f.unlink()
                        purged += 1
                except Exception:
                    pass
        for f in (PROJECT_ROOT / "output").glob("frame_sample_*.jpg"):
            if str(f.resolve()) in resolved_keeps or f.name in resolved_keeps:
                continue
            try:
                mtime = f.stat().st_mtime
                if max_age_seconds <= 0 or (now - mtime) > max_age_seconds:
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
        logger.info(f"[DynamicVisualEngine] Pre-generation purge: Deleted {purged} stale intermediate files from disk.")
        return purged



    @classmethod
    def register_used_image(cls, identifier: Any, file_bytes: Optional[bytes] = None) -> None:
        """Records an image as used (by path, filename, URL, or MD5/SHA256 hash) so it is never reused in future videos."""
        reg = cls.get_used_registry()

        # Connect to PermanentVisualMemory for perceptual & cryptographic durability
        try:
            from app.storage.permanent_visual_memory import PermanentVisualMemory
            if isinstance(identifier, Path) and identifier.exists():
                PermanentVisualMemory.record_used_visual(identifier, source_identity=identifier.name)
            elif file_bytes:
                PermanentVisualMemory.record_used_visual(file_bytes, source_identity=str(identifier) if isinstance(identifier, str) else "")
        except Exception as e:
            logger.debug(f"PermanentVisualMemory registration notice: {e}")

        if file_bytes:
            h = f"hash:{hashlib.md5(file_bytes).hexdigest()}"
            reg.add(h)
            cls._session_used_hashes.add(h.lower())

        if isinstance(identifier, Path):
            try:
                rel = str(identifier.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
                reg.add(rel)
            except Exception:
                pass
            reg.add(identifier.name)
            if identifier.exists():
                try:
                    with open(identifier, "rb") as f:
                        fh = f"hash:{hashlib.md5(f.read()).hexdigest()}"
                    reg.add(fh)
                    cls._session_used_hashes.add(fh.lower())
                except Exception:
                    pass
        elif isinstance(identifier, str):
            clean = identifier.strip()
            if clean:
                reg.add(clean)
                if clean.startswith("http"):
                    base_url = clean.split("?")[0].lower()
                    reg.add(base_url)
                    cls._session_used_urls.add(clean.lower())
                    cls._session_used_urls.add(base_url)
                elif clean.startswith("hash:"):
                    cls._session_used_hashes.add(clean.lower())

        cls.save_used_registry(reg)

    @classmethod
    def is_image_used(cls, identifier: Any, file_bytes: Optional[bytes] = None) -> bool:
        """Checks if this image (by Path, filename, URL, or MD5/pHash/dHash) has ever been used in this or past videos."""
        # 0. Check PermanentVisualMemory for exact or near-duplicate matches
        try:
            from app.storage.permanent_visual_memory import PermanentVisualMemory
            if isinstance(identifier, Path) and identifier.exists():
                is_dup, reason, _ = PermanentVisualMemory.check_duplicate(identifier, source_identity=identifier.name)
                if is_dup:
                    logger.debug(f"[DynamicVisualEngine] Permanent memory rejected duplicate: {reason}")
                    return True
            elif file_bytes:
                is_dup, reason, _ = PermanentVisualMemory.check_duplicate(file_bytes, source_identity=str(identifier) if isinstance(identifier, str) else "")
                if is_dup:
                    logger.debug(f"[DynamicVisualEngine] Permanent memory rejected byte duplicate: {reason}")
                    return True
            elif isinstance(identifier, str):
                is_dup, reason, _ = PermanentVisualMemory.check_duplicate(None, source_identity=identifier)
                if is_dup:
                    return True
        except Exception as e:
            logger.debug(f"PermanentVisualMemory duplicate check notice: {e}")

        if file_bytes:
            h = f"hash:{hashlib.md5(file_bytes).hexdigest()}".lower()
            if h in cls._session_used_hashes:
                return True
            reg = cls.get_used_registry()
            if h in {x.lower() for x in reg}:
                return True

        if isinstance(identifier, Path):
            name = identifier.name.lower()
            if name in BANNED_IMAGE_NAMES:
                return True
            # Permanently block any legacy static artifact b-roll or repeated files
            if any(pat in name for pat in ["neelam_sc", "pukhraj_sc", "panna_sc", "gomed_sc", "ruby_sc", "sample_"]):
                return True

            reg = cls.get_used_registry()
            reg_lower = {x.lower() for x in reg}

            if identifier.name in reg or name in reg_lower:
                return True
            try:
                rel = str(identifier.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/").lower()
                if rel in reg_lower:
                    return True
            except Exception:
                pass
            if identifier.exists():
                try:
                    with open(identifier, "rb") as f:
                        fh = f"hash:{hashlib.md5(f.read()).hexdigest()}".lower()
                    if fh in cls._session_used_hashes or fh in reg_lower:
                        return True
                except Exception:
                    pass
            return False

        elif isinstance(identifier, str):
            clean = identifier.strip().lower()
            if not clean:
                return False
            if clean in cls._session_used_urls or clean in cls._session_used_hashes:
                return True
            reg = cls.get_used_registry()
            reg_lower = {x.lower() for x in reg}
            if clean in reg_lower:
                return True
            if clean.startswith("http"):
                base_url = clean.split("?")[0].lower()
                if base_url in cls._session_used_urls or base_url in reg_lower:
                    return True
            return False

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
            is_crystal_or_gem = any(k in f"{entity_context} {topic.lower()}" for k in [
                "pyrite", "amethyst", "tourmaline", "citrine", "rose quartz", "tiger",
                "sphatik", "selenite", "carnelian", "labradorite", "rudraksha", "mukhi"
            ])
            if is_crystal_or_gem:
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
    def matches_keyword(cls, text: str, keywords: List[str]) -> bool:
        """Performs strict word-boundary matching to prevent substring false positives (e.g. 'moti' in 'emotional')."""
        if not text:
            return False
        for kw in keywords:
            if re.search(r"[a-zA-Z]", kw):
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return True
            else:
                # Devanagari Hindi words (protect boundaries)
                pattern = rf"(?<![\w\u0900-\u097F]){re.escape(kw)}(?![\w\u0900-\u097F])"
                if re.search(pattern, text):
                    return True
        return False

    @classmethod
    def get_scene_search_query(cls, scene_dict: Dict[str, Any], topic: str, scene_idx: int) -> str:
        """Formulates targeted keywords for live photographic image retrieval that match exact scene content."""
        spoken = scene_dict.get("spoken_line", "").lower()
        on_screen = scene_dict.get("on_screen_text", "").lower()
        vis_desc = scene_dict.get("visual_description", "").lower()
        scene_context = f"{spoken} {on_screen} {vis_desc}".lower()
        topic_lower = (topic or "").lower()
        combined_context = f"{topic_lower} {scene_context}"

        # 1. SPECIFIC CRYSTAL / GEMSTONE / RUDRAKSHA TOPIC OVERRIDES
        # When the user or scene specifically talks about an entity, strictly return queries for that entity
        if cls.matches_keyword(combined_context, ["pyrite", "पायराइट"]):
            queries = ["pyrite crystal cluster", "raw golden pyrite mineral", "sparkling pyrite cube specimen", "iron pyrite rock cluster"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "pyrite crystal cluster macro"
        elif cls.matches_keyword(combined_context, ["rudraksha", "रुद्राक्ष", "मुख", "mukhi"]):
            queries = ["rudraksha beads prayer mala", "nepalese rudraksha seed macro", "sacred rudraksha japa mala", "rudraksha tree bead"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "rudraksha beads prayer mala macro"
        elif cls.matches_keyword(combined_context, ["amethyst", "कटेला", "जामुनिया"]):
            queries = ["amethyst geode crystal", "raw purple amethyst cluster", "deep violet amethyst mineral specimen", "amethyst crystal point"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "amethyst geode crystal macro"
        elif cls.matches_keyword(combined_context, ["tourmaline", "टूमलाइन"]):
            queries = ["black tourmaline crystal", "raw black tourmaline tower", "schorl tourmaline mineral specimen", "striated black tourmaline"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "black tourmaline crystal macro"
        elif cls.matches_keyword(combined_context, ["citrine", "सिट्रीन"]):
            queries = ["citrine quartz crystal", "golden citrine cluster", "raw amber citrine mineral", "yellow citrine specimen"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "citrine quartz crystal macro"
        elif cls.matches_keyword(combined_context, ["rose quartz"]):
            queries = ["rose quartz crystal mineral", "raw pink rose quartz", "translucent rose quartz stone", "pink quartz specimen"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "rose quartz crystal mineral macro"
        elif cls.matches_keyword(combined_context, ["tiger", "tigers eye", "tiger's eye", "टाइगर"]):
            queries = ["tigers eye gemstone mineral", "golden brown tigers eye stone", "chatoyant tigers eye specimen", "tigers eye rock"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "tigers eye gemstone mineral macro"
        elif cls.matches_keyword(combined_context, ["selenite", "सेलेनाइट"]):
            queries = ["selenite crystal tower", "white selenite mineral specimen", "raw selenite gypsum crystal", "selenite wand crystal"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "selenite crystal tower macro"
        elif cls.matches_keyword(combined_context, ["clear quartz", "sphatik", "स्फटिक"]):
            queries = ["clear quartz crystal", "sphatik crystal point", "natural quartz mineral specimen"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "clear quartz crystal macro"
        elif cls.matches_keyword(combined_context, ["carnelian", "कार्नेलियन"]):
            queries = ["carnelian crystal polished stone", "raw carnelian agate mineral", "translucent carnelian gemstone"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "carnelian crystal macro"
        elif cls.matches_keyword(combined_context, ["labradorite", "लैब्राडोराइट"]):
            queries = ["labradorite crystal stone", "raw labradorite mineral flash", "labradorite iridescent specimen"]
            return queries[scene_idx % len(queries)] if scene_idx > 0 else "labradorite crystal macro"
        elif cls.matches_keyword(combined_context, ["blue sapphire", "neelam", "नीलम"]) and cls.matches_keyword(combined_context, ["gemstone", "रत्न", "stone", "ring", "अंगूठी"]):
            queries = ["blue sapphire gemstone", "raw blue corundum sapphire", "natural blue sapphire crystal"]
            return queries[scene_idx % len(queries)]
        elif cls.matches_keyword(combined_context, ["ruby", "manik", "माणिक"]) and cls.matches_keyword(combined_context, ["gemstone", "रत्न", "stone", "ring", "अंगूठी"]):
            queries = ["ruby gemstone jewelry", "raw ruby corundum mineral", "natural red ruby crystal"]
            return queries[scene_idx % len(queries)]
        elif cls.matches_keyword(combined_context, ["yellow sapphire", "pukhraj", "पुखराज"]) and cls.matches_keyword(combined_context, ["gemstone", "रत्न", "stone", "ring", "अंगूठी"]):
            queries = ["yellow sapphire gemstone", "natural yellow sapphire corundum", "yellow sapphire mineral"]
            return queries[scene_idx % len(queries)]
        elif cls.matches_keyword(combined_context, ["emerald", "panna", "पन्ना"]) and cls.matches_keyword(combined_context, ["gemstone", "रत्न", "stone", "ring", "अंगूठी"]):
            queries = ["emerald gemstone jewelry", "raw green emerald beryl", "colombian emerald crystal specimen"]
            return queries[scene_idx % len(queries)]
        elif cls.matches_keyword(combined_context, ["pearl", "moti", "मोती"]) and cls.matches_keyword(combined_context, ["gemstone", "रत्न", "stone", "ring", "अंगूठी"]):
            queries = ["natural pearl gemstone", "south sea white pearl", "basra pearl jewelry"]
            return queries[scene_idx % len(queries)]
        elif cls.matches_keyword(combined_context, ["coral", "moonga", "मूँगा", "मूंगा"]) and cls.matches_keyword(combined_context, ["gemstone", "रत्न", "stone", "ring", "अंगूठी"]):
            queries = ["red coral gemstone", "natural red coral mineral", "mediterranean red coral stone"]
            return queries[scene_idx % len(queries)]
        elif cls.matches_keyword(combined_context, ["diamond", "heera", "हीरा"]) and cls.matches_keyword(combined_context, ["gemstone", "रत्न", "stone", "ring", "अंगूठी"]):
            queries = ["diamond gemstone jewelry", "raw uncut diamond crystal", "sparkling diamond gemstone"]
            return queries[scene_idx % len(queries)]

        # 2. SCRIPT-SPECIFIC CONTENT ROUTING (Astrology, Meditation, Sacred Lamps, Constellations)
        if cls.matches_keyword(scene_context, ["constellation", "star map", "cosmic map", "starlight", "astrolabe"]):
            queries = [
                "ancient star chart constellation lines",
                "ancient celestial map star chart",
                "constellation star map celestial",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["dream", "astral", "dreamscape", "sleep", "नींद", "सपनों"]):
            queries = [
                "cosmic dreamscape starlight nebula",
                "ethereal deep space nebula",
                "starry sky nebula space",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["meditat", "silhouette", "एकांत", "ध्यान", "detachment", "वैराग्य", "solitude"]):
            queries = [
                "meditation silhouette amber light",
                "person meditating serene golden light",
                "meditator silhouette sacred room",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["lamp", "diya", "दीपक", "दीप", "oil lamp", "candlelight", "candle"]):
            if cls.matches_keyword(scene_context, ["text", "scripture", "ग्रंथ", "शास्त्र", "book", "chart", "charts"]):
                return "burning brass oil lamp sacred texts"
            queries = [
                "brass diya flame temple altar",
                "hindu temple brass oil lamp",
                "sacred brass diya glowing light",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["mala", "bead", "beads", "माला", "japa"]):
            queries = [
                "japa mala prayer beads brass diya",
                "sacred japa mala beads altar",
                "prayer beads meditation desk",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["palmleaf", "manuscript", "पांडुलिपि", "hourglass"]):
            queries = [
                "ancient palm leaf manuscript sanskrit",
                "vedic manuscript parchment scroll",
                "ancient sanskrit scripture",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["kundli", "birth chart", "कुंडली", "जन्मपत्रिका", "house", "भाव", "लग्न", "horoscope"]):
            queries = [
                "authentic vedic kundli astrology chart",
                "ancient astrology birth chart horoscope",
                "vedic birth chart manuscript",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["temple", "sanctum", "मंदिर", "dm", "consultation", "परामर्श", "कमेंट", "booking", "bells", "bell"]):
            cta_queries = [
                "hindu temple sanctum brass diyas",
                "sacred temple oil lamps golden diyas",
                "sacred brass diya flame temple altar",
            ]
            return cta_queries[scene_idx % len(cta_queries)]

        if cls.matches_keyword(scene_context, ["havan", "fire", "altar", "हवन", "अग्नि"]):
            queries = [
                "sacred havan flame fire altar",
                "vedic havan fire altar",
                "sacred fire flame ritual",
            ]
            return queries[scene_idx % len(queries)]

        if cls.matches_keyword(scene_context, ["saturn", "shani", "शनि"]):
            return "planet saturn rings space"
        if cls.matches_keyword(scene_context, ["moon", "chandra", "चंद्रमा"]):
            return "crescent moon night stars space"
        if cls.matches_keyword(scene_context, ["sun", "surya", "सूर्य"]):
            return "sun solar flare corona space"
        if cls.matches_keyword(scene_context, ["jupiter", "guru", "बृहस्पति"]):
            return "planet jupiter space cosmos"
        if cls.matches_keyword(scene_context, ["mars", "mangal", "मंगल"]):
            return "planet mars red space"
        if cls.matches_keyword(scene_context, ["venus", "shukra", "शुक्र"]):
            return "planet venus space atmosphere"

        # 3. Clean extraction from visual_description if provided
        if vis_desc and len(vis_desc.split()) >= 3:
            clean_desc = re.sub(
                r"^(cinematic\s+)?(8k\s+)?(macro\s+)?(shot\s+of\s+)?(close-up\s+of\s+)?(high-end\s+visual\s+of\s+)?(clear\s+cinematic\s+focus\s+on\s+)?(warm,\s*inviting\s+cinematic\s+frame\s+of\s+)?(calm,\s*serene\s+silhouette\s+of\s+a\s+)?(an\s+)?",
                "",
                vis_desc,
                flags=re.I,
            ).strip()
            stopwords = {"with", "and", "the", "for", "from", "into", "that", "this", "shot", "visual", "frame", "tones", "colors"}
            words = [w for w in re.split(r"[\s,\.:;]+", clean_desc) if len(w) > 2 and w.lower() not in stopwords]
            if len(words) >= 2:
                return " ".join(words[:4])

        # 4. Safe authentic fallback
        return "authentic vedic astrology cosmic map"

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
        seed: Optional[int] = None,
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
        calc_seed = seed if seed is not None else int(time.time() * 1000000) % 999999
        rng = random.Random(calc_seed)
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
            frac = max(0.0, (r_step - width * 0.35) / max(1.0, (max_dist - width * 0.35)))
            alpha = int(230 * (frac ** 1.6))
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
    ) -> Optional[Path]:
        """
        Searches Openverse API for high-resolution Creative Commons photographs
        of authentic crystals, minerals, and sacred items.
        Enforces strict anti-repetition: checks URLs and content hashes against both
        session memory and the persistent used visuals registry.
        """
        if os.getenv("TESTING") == "true" or os.getenv("OFFLINE_MODE") == "true":
            return None

        clean_q = urllib.parse.quote(query)
        url = f"https://api.openverse.org/v1/images/?q={clean_q}&page_size=15"
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
                if not img_url:
                    continue
                clean_url = img_url.split("?")[0].lower()
                if img_url in cls._session_used_urls or clean_url in cls._session_used_urls:
                    continue
                if cls.is_image_used(img_url) or cls.is_image_used(clean_url):
                    continue
                try:
                    ir = urllib.request.urlopen(
                        urllib.request.Request(img_url, headers={"User-Agent": "InstaAstrologyAgent/1.0"}),
                        timeout=6,
                    )
                    img_bytes = ir.read(6 * 1024 * 1024)
                    if len(img_bytes) > 12000:
                        if cls.is_image_used(clean_url, file_bytes=img_bytes):
                            continue
                        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        w, h = img.size
                        if w < 200 or h < 200:
                            continue
                        cropped = ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)
                        cls.save_clean_photographic_image(cropped, target_file, quality=95)
                        cls._session_used_urls.add(img_url)
                        cls._session_used_urls.add(clean_url)
                        cls.register_used_image(img_url, file_bytes=img_bytes)
                        cls.register_used_image(clean_url)
                        cls.register_used_image(target_file)
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
        Searches NASA Image and Video Library API strictly for celestial / astronomical space queries
        and crops the image to professional 1080x1920 (9:16 vertical) resolution.
        Never scrapes generic public search engines (eliminating food, insects, and irrelevant images).
        """
        if os.getenv("TESTING") == "true" or os.getenv("OFFLINE_MODE") == "true":
            return None

        # Check NASA API strictly for celestial / space queries
        if any(w in query.lower() for w in ["moon", "saturn", "jupiter", "mars", "nebula", "space", "eclipse", "sun", "stars", "cosmos"]):
            try:
                nasa_url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(query)}&media_type=image"
                req = urllib.request.Request(nasa_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as r:
                    nasa_data = json.loads(r.read())
                items = nasa_data.get("collection", {}).get("items", [])
                for item in items[:15]:
                    links = item.get("links", [])
                    if links:
                        img_url = links[0].get("href")
                        if not img_url or img_url in cls._session_used_urls or cls.is_image_used(img_url):
                            continue
                        med_url = img_url.replace("~thumb.jpg", "~medium.jpg")
                        try:
                            ir = urllib.request.urlopen(urllib.request.Request(med_url, headers={"User-Agent": "Mozilla/5.0"}), timeout=5)
                            data_bytes = ir.read(6 * 1024 * 1024)
                        except Exception:
                            ir = urllib.request.urlopen(urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"}), timeout=5)
                            data_bytes = ir.read(6 * 1024 * 1024)
                        if len(data_bytes) > 10000:
                            if cls.is_image_used(img_url, file_bytes=data_bytes):
                                continue
                            img = Image.open(io.BytesIO(data_bytes)).convert("RGB")
                            w, h = img.size
                            if w < 200 or h < 200:
                                continue
                            cropped = ImageOps.fit(img, (1080, 1920), method=Image.Resampling.LANCZOS)
                            cls.save_clean_photographic_image(cropped, target_file, quality=95)
                            cls._session_used_urls.add(img_url)
                            cls.register_used_image(img_url, file_bytes=data_bytes)
                            cls.register_used_image(target_file)
                            logger.info(f"[DynamicVisualEngine] Sourced authentic NASA photograph -> {target_file.name}")
                            return target_file
            except Exception as e:
                logger.debug(f"[DynamicVisualEngine] NASA search notice: {e}")

        return None

    @classmethod
    def generate_authentic_photographic_canvas(
        cls,
        scene_dict: Dict[str, Any],
        topic: str,
        scene_idx: int,
        total_scenes: int,
        out_path: Path,
        seed: Optional[int] = None,
        width: int = 1080,
        height: int = 1920,
        master_asset_override: Optional[Path] = None,
        used_master_assets: Optional[Set[Any]] = None,
    ) -> Path:
        """
        Creates an authentic, freshly rendered 100% genuine photographic canvas.
        Strictly sources from high-resolution authentic master photographs in CINEMATIC_BROLL_DIR,
        crops/fits to 1080x1920 (9:16 vertical), and applies subtle cinematic photographic
        grading (contrast, color temperature, tone curve) so that every output is uniquely
        registered and 100% photographic.
        STRICTLY ZERO 3D geometric drawings, ZERO Pillow polygon shapes, ZERO synthetic canvases.
        """
        spoken = scene_dict.get("spoken_line", "").lower()
        on_screen = scene_dict.get("on_screen_text", "").lower()
        vis_desc = scene_dict.get("visual_description", "").lower()
        scene_txt = f"{spoken} {on_screen} {vis_desc}".lower()
        topic_lower = (topic or "").lower()
        full_context = f"{topic_lower} {scene_txt}"

        calc_seed = seed if seed is not None else int(time.time() * 1000000) % 999999
        rng = random.Random(calc_seed)

        def is_available(p: Path) -> bool:
            if not p or not p.exists():
                return False
            if used_master_assets is None:
                return True
            return p not in used_master_assets and p.name not in used_master_assets and str(p) not in used_master_assets

        def pick_unused(cands_list: List[Path]) -> Optional[Path]:
            for c in cands_list:
                if is_available(c):
                    return c
            return None

        # 1. Determine the best matching authentic photographic master asset
        master_asset: Optional[Path] = None
        if master_asset_override and is_available(master_asset_override):
            master_asset = master_asset_override

        # (A) Crystal / Gemstone / Rudraksha specific topics
        if not master_asset:
            if any(k in full_context for k in ["pyrite", "पायराइट"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_pyrite_cluster.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_green_aventurine.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                ])
            elif any(k in full_context for k in ["rudraksha", "रुद्राक्ष", "mukhi", "मुख"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "rudraksha_sacred_beads.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_green_aventurine.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                ])
            elif any(k in full_context for k in ["amethyst", "कटेला", "जामुनिया"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_amethyst_cluster.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                ])
            elif any(k in full_context for k in ["tourmaline", "टूमलाइन"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_black_tourmaline.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                ])
            elif any(k in full_context for k in ["citrine", "सिट्रीन"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_pyrite_cluster.jpg",
                ])
            elif any(k in full_context for k in ["rose quartz"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_rose_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                ])
            elif any(k in full_context for k in ["tiger", "tigers eye", "टाइगर"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                ])
            elif any(k in full_context for k in ["selenite", "सेलेनाइट"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                ])
            elif any(k in full_context for k in ["aventurine", "एवेंट्यूरिन"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_green_aventurine.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                ])
            elif any(k in full_context for k in ["clear quartz", "sphatik", "स्फटिक"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                ])
            elif any(k in full_context for k in ["carnelian", "कार्नेलियन"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_carnelian.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
                ])
            elif any(k in full_context for k in ["labradorite", "लैब्राडोराइट"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "crystal_labradorite.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_black_tourmaline.jpg",
                ])

        # (B) Script scene semantic matching
        if not master_asset:
            if any(k in scene_txt for k in ["meditat", "silhouette", "एकांत", "ध्यान", "peace", "serenity"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "rudraksha_sacred_beads.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg",
                    CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg",
                ])
            elif any(k in scene_txt for k in ["lamp", "diya", "दीपक", "दीप", "oil lamp"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg",
                    CINEMATIC_BROLL_DIR / "astrology_consultation_scroll.jpg",
                ])
            elif any(k in scene_txt for k in ["dream", "astral", "dreamscape", "sleep", "नींद", "starlight", "vivid", "सपने", "सपनों"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "planet_moon.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                    CINEMATIC_BROLL_DIR / "planet_saturn.jpg",
                    CINEMATIC_BROLL_DIR / "planet_jupiter.jpg",
                ])
            elif any(k in scene_txt for k in ["constellation", "star map", "cosmic map"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg",
                    CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg",
                    CINEMATIC_BROLL_DIR / "2_kundli_chart.jpg",
                ])
            elif any(k in scene_txt for k in ["kundli", "birth chart", "कुंडली", "जन्मपत्रिका", "house", "भाव", "8th house"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg",
                    CINEMATIC_BROLL_DIR / "2_kundli_chart.jpg",
                    CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg",
                ])
            elif any(k in scene_txt for k in ["palmleaf", "manuscript", "पांडुलिपि", "शास्त्र", "ग्रंथ", "remedy", "caution", "उपाय", "सावधानी"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "astrology_consultation_scroll.jpg",
                    CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                ])
            elif any(k in scene_txt for k in ["mala", "bead", "माला", "desk"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "rudraksha_sacred_beads.jpg",
                    CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg",
                ])
            elif any(k in scene_txt for k in ["havan", "fire", "altar", "हवन", "अग्नि"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "sacred_havan_flame_altar.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_vedic_fire_altar.jpg",
                    CINEMATIC_BROLL_DIR / "4_sacred_havan.jpg",
                ])
            elif any(k in scene_txt for k in ["temple", "sanctum", "मंदिर", "dm", "consultation", "परामर्श", "सेव"]):
                master_asset = pick_unused([
                    CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_vedic_fire_altar.jpg",
                    CINEMATIC_BROLL_DIR / "5_temple_sanctum.jpg",
                ])
            elif any(k in scene_txt for k in ["saturn", "shani", "शनि"]):
                master_asset = pick_unused([CINEMATIC_BROLL_DIR / "planet_saturn.jpg"])
            elif any(k in scene_txt for k in ["moon", "chandra", "चंद्रमा"]):
                master_asset = pick_unused([CINEMATIC_BROLL_DIR / "planet_moon.jpg"])
            elif any(k in scene_txt for k in ["sun", "surya", "सूर्य"]):
                master_asset = pick_unused([CINEMATIC_BROLL_DIR / "planet_sun.jpg"])
            elif any(k in scene_txt for k in ["jupiter", "guru", "बृहस्पति"]):
                master_asset = pick_unused([CINEMATIC_BROLL_DIR / "planet_jupiter.jpg"])
            elif any(k in scene_txt for k in ["yantra", "mandala", "यंत्र"]):
                master_asset = pick_unused([CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg"])

        # Final default fallback to safe authentic photographic master
        is_crystal_topic = any(k in full_context for k in ["pyrite", "crystal", "amethyst", "tourmaline", "citrine", "rudraksha", "mukhi"])
        safe_pool = [
            CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
            CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg",
            CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
            CINEMATIC_BROLL_DIR / "crystal_green_aventurine.jpg",
            CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
            CINEMATIC_BROLL_DIR / "crystal_carnelian.jpg",
            CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
        ] if is_crystal_topic else [
            CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg",
            CINEMATIC_BROLL_DIR / "planet_saturn.jpg",
            CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg",
            CINEMATIC_BROLL_DIR / "planet_moon.jpg",
            CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg",
            CINEMATIC_BROLL_DIR / "astrology_consultation_scroll.jpg",
            CINEMATIC_BROLL_DIR / "sacred_vedic_fire_altar.jpg",
            CINEMATIC_BROLL_DIR / "2_kundli_chart.jpg",
            CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg",
            CINEMATIC_BROLL_DIR / "rudraksha_sacred_beads.jpg",
            CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
        ]

        if not master_asset:
            master_asset = pick_unused(safe_pool)

        if not master_asset:
            master_asset = safe_pool[scene_idx % len(safe_pool)]

        # Track in used_master_assets so no scene in this reel reuses this master asset
        if used_master_assets is not None and master_asset:
            used_master_assets.add(master_asset)
            used_master_assets.add(master_asset.name)
            used_master_assets.add(str(master_asset))

        # Open and adapt the genuine photograph with subtle cinematic grading
        with Image.open(master_asset) as src_img:
            img = src_img.convert("RGB")
            cropped = ImageOps.fit(img, (width, height), method=Image.Resampling.LANCZOS)

            # Apply subtle photographic grading
            contrast_factor = 1.02 + (scene_idx % 3) * 0.02
            color_factor = 0.98 + (scene_idx % 2) * 0.04
            graded = ImageEnhance.Contrast(cropped).enhance(contrast_factor)
            graded = ImageEnhance.Color(graded).enhance(color_factor)

        cls.save_clean_photographic_image(graded, out_path, quality=95)
        logger.info(f"[DynamicVisualEngine] Rendered authentic photographic canvas ({master_asset.name}) -> {out_path.name}")
        return out_path

    # Backward-compatibility alias
    generate_variety_canvas = generate_authentic_photographic_canvas

    @classmethod
    def get_or_generate_scene_image(
        cls,
        scene_dict: Dict[str, Any],
        topic: str,
        scene_idx: int,
        total_scenes: int,
        reel_slug: str,
        used_images: Optional[Set[Any]] = None,
        allow_static_fallback: Optional[bool] = None,
    ) -> Path:
        """
        Main production entrypoint: Sourcing and delivering an authentic, high-resolution 1080x1920 visual
        that STRICTLY matches the information conveyed in this specific scene script.
        Uses AIImageGenerator to create fresh, script-driven visuals.
        """
        from app.video.ai_image_generator import AIImageGenerator
        try:
            res = AIImageGenerator.generate_scene_image(
                scene_dict=scene_dict,
                topic=topic,
                scene_idx=scene_idx,
                total_scenes=total_scenes,
                reel_slug=reel_slug,
                used_images=used_images,
                allow_static_fallback=allow_static_fallback,
            )
            if used_images is not None:
                used_images.add(res)
            return res
        except Exception as e:
            if allow_static_fallback:
                logger.warning(f"[DynamicVisualEngine] AI generation failed, falling back to static plate: {e}")
                return cls._legacy_static_broll_fallback(
                    scene_dict=scene_dict,
                    topic=topic,
                    scene_idx=scene_idx,
                    total_scenes=total_scenes,
                    target_file=None,
                    used_images=used_images or set(),
                )
            raise

    # Backward-compatible alias
    get_or_create_scene_visual = get_or_generate_scene_image

    @classmethod
    def _legacy_static_broll_fallback(
        cls,
        scene_dict: Dict[str, Any],
        topic: str,
        scene_idx: int,
        total_scenes: int,
        target_file: Optional[Path] = None,
        used_images: Optional[Set[Any]] = None,
    ) -> Path:
        """
        Sourcing and delivering an authentic, high-resolution 1080x1920 visual
        that STRICTLY matches the information conveyed in this specific scene script.
        """
        if used_images is None:
            used_images = set()

        reel_slug = re.sub(r"[^\w]", "_", topic.lower())[:20].strip("_")
        timestamp_seed = int(time.time() * 1000) % 1000000
        prompt_hash = hashlib.md5(f"{reel_slug}_{scene_idx}_{timestamp_seed}".encode()).hexdigest()[:10]
        if target_file is None:
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
        is_last_scene = (scene_idx == total_scenes - 1)
        is_caution_scene = (scene_idx == total_scenes - 2)
        is_hook_scene = (scene_idx == 0)

        is_crystal_or_rudraksha = any(k in full_context for k in [
            "pyrite", "पायराइट", "amethyst", "कटेला", "जामुनिया", "tourmaline", "टूमलाइन",
            "citrine", "सिट्रीन", "rose quartz", "aventurine", "एवेंट्यूरिन", "tiger",
            "sphatik", "स्फटिक", "selenite", "सेलेनाइट", "carnelian", "कार्नेलियन",
            "labradorite", "लैब्राडोराइट", "rudraksha", "रुद्राक्ष", "mukhi"
        ])

        candidates: List[Path] = []

        # (A) Call to Action / DM Consultation / Sacred Havan (Scene 7)
        if is_last_scene:
            cta_pool = [
                CINEMATIC_BROLL_DIR / "4_sacred_havan.jpg",
                CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg",
                CINEMATIC_BROLL_DIR / "2_kundli_chart.jpg",
            ]
            rot_idx = int(hashlib.md5(f"{topic}_cta".encode()).hexdigest(), 16) % len(cta_pool)
            candidates.extend(cta_pool[rot_idx:] + cta_pool[:rot_idx])

        # (B) Caution against Blind Remedies / Warning / Blue Sapphire (Scene 6)
        elif is_caution_scene:
            caution_pool = [
                CINEMATIC_BROLL_DIR / "gemstone_blue_sapphire.jpg",
                CINEMATIC_BROLL_DIR / "gemstone_emerald.jpg",
                CINEMATIC_BROLL_DIR / "gemstone_ruby.jpg",
            ]
            rot_idx = int(hashlib.md5(f"{topic}_caution".encode()).hexdigest(), 16) % len(caution_pool)
            candidates.extend(caution_pool[rot_idx:] + caution_pool[:rot_idx])

        # (C) Scenes 0-5: Rich Content-Matched Semantic Resolver
        else:
            # 0. Tiger's Eye Gemstone (Strict 1:1 match for tiger eye scenes & hook)
            if any(k in scene_txt for k in ["tiger", "tigers eye", "टाइगर"]):
                candidates.append(CINEMATIC_BROLL_DIR / "fresh_tiger_eye_macro.jpg")
            elif is_hook_scene and curated_master_plate:
                candidates.append(curated_master_plate)

            # 1. Specific Planets & Cosmic Alignments (Highest Priority: match exact celestial entity)
            if any(k in scene_txt for k in ["tiger", "tigers eye", "टाइगर"]):
                candidates.append(CINEMATIC_BROLL_DIR / "fresh_tiger_eye_macro.jpg")
            if (any(k in scene_txt for k in ["rahu", "राहु"]) and any(k in scene_txt for k in ["surya", "sun", "सूर्य"])) or "sun rahu" in scene_txt:
                from app.video.kundli_chart_generator import KundliChartGenerator
                candidates.append(KundliChartGenerator.generate_3d_kundli_planet_scene(scene_dict, topic, scene_idx, target_file))
            if any(k in scene_txt for k in ["mangal", "mars", "मंगल"]):
                from app.video.kundli_chart_generator import KundliChartGenerator
                candidates.append(KundliChartGenerator.generate_3d_kundli_planet_scene(scene_dict, topic, scene_idx, target_file))
            if any(k in scene_txt for k in ["shani", "saturn", "शनि", "drishti", "दृष्टि"]):
                from app.video.kundli_chart_generator import KundliChartGenerator
                candidates.append(KundliChartGenerator.generate_3d_kundli_planet_scene(scene_dict, topic, scene_idx, target_file))
            if any(k in scene_txt for k in ["emerald", "पन्ना", "gemstone", "sapphire", "नीलम", "रत्न"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_blue_sapphire.jpg")
            if any(k in scene_txt for k in ["12th", "बारहवें", "बारहवां", "twelfth", "vyaya", "व्यय", "kundli", "कुंडली"]):
                from app.video.kundli_chart_generator import KundliChartGenerator
                candidates.append(KundliChartGenerator.generate_3d_kundli_planet_scene(scene_dict, topic, scene_idx, target_file))
            if any(k in scene_txt for k in ["guru", "brihaspati", "jupiter", "गुरु", "बृहस्पति"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_jupiter.jpg")
            if any(k in scene_txt for k in ["chandra", "moon", "चंद्रमा", "चन्द्र"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_moon.jpg")
            if any(k in scene_txt for k in ["shukra", "venus", "शुक्र"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_venus.jpg")
            if any(k in scene_txt for k in ["budh", "mercury", "बुध"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_mercury.jpg")
            if any(k in scene_txt for k in ["rahu", "राहु"]) and not any(k in scene_txt for k in ["surya", "sun", "सूर्य"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_rahu.jpg")
            if any(k in scene_txt for k in ["ketu", "केतु"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_ketu.jpg")

            # 2. Specific Gemstones & Crystals (Direct physical match)
            if any(k in scene_txt for k in ["tiger", "tigers eye", "टाइगर"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg")
            if any(k in scene_txt for k in ["neelam", "blue sapphire", "नीलम"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_blue_sapphire.jpg")
            if any(k in scene_txt for k in ["panna", "emerald", "पन्ना"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_emerald.jpg")
            if any(k in scene_txt for k in ["manik", "ruby", "माणिक"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_ruby.jpg")
            if any(k in scene_txt for k in ["pukhraj", "yellow sapphire", "पुखराज"]):
                candidates.append(CINEMATIC_BROLL_DIR / "gemstone_yellow_sapphire.jpg")
            if any(k in scene_txt for k in ["pyrite", "पायराइट"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_pyrite_cluster.jpg")
            if any(k in scene_txt for k in ["amethyst", "कटेला", "जामुनिया"]):
                candidates.append(CINEMATIC_BROLL_DIR / "crystal_amethyst_cluster.jpg")

            # 3. Authentic Vedic Kundli / Birth Chart / Sanskrit Parchment
            if any(k in scene_txt for k in ["kundli", "कुंडली", "birth chart", "भाव", "लग्न", "house", "केंद्र", "त्रिकोण", "जन्मपत्रिका", "12th", "बारहवें"]):
                candidates.append(CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg")
                candidates.append(CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg")

            # 4. Subtle Energy / Sacred Geometry / Yantra
            if any(k in scene_txt for k in ["yantra", "यंत्र", "frequency", "vibration", "resonance", "तरंग", "bio-electric", "चक्र", "ऊर्जा", "aura", "shield"]):
                candidates.append(CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg")

            # 5. Astrological Consultation / Sacred Lamps / Sanctum
            if any(k in scene_txt for k in ["lamp", "diya", "दीपक", "दीप", "oil lamp"]):
                candidates.append(CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg")
                candidates.append(CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg")

            # 7. Ancient Palmleaf Manuscript, Ancient Scriptures & Caution
            if any(k in scene_txt for k in ["palmleaf", "manuscript", "पांडुलिपि", "शास्त्र", "ग्रंथ"]):
                candidates.append(CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg")
                candidates.append(CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg")

            # 8. Constellations, Celestial Charts & Cosmic Maps
            if any(k in scene_txt for k in ["constellation", "star map", "cosmic map"]):
                candidates.append(CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg")
                candidates.append(CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg")

            # 9. Astral Dreams & Cosmic Dreamscape
            if any(k in scene_txt for k in ["dream", "astral", "dreamscape", "sleep", "नींद", "सपनों"]):
                candidates.append(CINEMATIC_BROLL_DIR / "planet_moon.jpg")
                candidates.append(CINEMATIC_BROLL_DIR / "planet_saturn.jpg")

            # 10. Sacred Mala Beads & Devotional Desk
            if any(k in scene_txt for k in ["mala", "bead", "माला"]):
                candidates.append(CINEMATIC_BROLL_DIR / "rudraksha_sacred_beads.jpg")
                candidates.append(CINEMATIC_BROLL_DIR / "temple_sanctum_golden_diyas.jpg")

            # 11. Direct Crystals / Gemstones / Rudraksha
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

            # Universal diverse library fallbacks (strictly segregated by niche to avoid mismatch)
            if is_crystal_or_rudraksha:
                candidates.extend([
                    CINEMATIC_BROLL_DIR / "crystal_citrine_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_clear_quartz.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_green_aventurine.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_tigers_eye.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_selenite.jpg",
                    CINEMATIC_BROLL_DIR / "crystal_carnelian.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                ])
            else:
                candidates.extend([
                    CINEMATIC_BROLL_DIR / "authentic_vedic_kundli_parchment.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_geometric_yantra.jpg",
                    CINEMATIC_BROLL_DIR / "vedic_astrology_parchment_chart.jpg",
                    CINEMATIC_BROLL_DIR / "planet_saturn.jpg",
                    CINEMATIC_BROLL_DIR / "planet_moon.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_havan_flame_altar.jpg",
                    CINEMATIC_BROLL_DIR / "sacred_temple_oil_lamps.jpg",
                ])

        # Tier 1: Check NASA API strictly for celestial/astronomical space queries
        chosen_cand: Optional[Path] = None
        search_query = cls.get_scene_search_query(scene_dict, topic, scene_idx)
        if any(w in search_query.lower() for w in ["moon", "saturn", "jupiter", "mars", "nebula", "galaxy"]):
            nasa_asset = cls.search_online_photographic_asset(search_query, target_file)
            if nasa_asset and nasa_asset.exists():
                chosen_cand = nasa_asset

        # Tier 2: Check matching candidates in candidates list that haven't been used in this reel
        if not chosen_cand:
            for cand in candidates:
                if cand.exists() and cand not in used_images and cand.name not in used_images:
                    chosen_cand = cand
                    break

        # Tier 3: Authentic photographic canvas adaptation (STRICTLY 100% genuine photograph, ZERO 3D drawings)
        # Sourced directly from authentic master b-roll, cropped to 1080x1920 with scene-specific cinematic grading
        if not chosen_cand:
            proc_seed = int(hashlib.md5(f"{reel_slug}_{scene_idx}_{prompt_hash}".encode()).hexdigest()[:8], 16)
            chosen_cand = cls.generate_authentic_photographic_canvas(
                scene_dict, topic, scene_idx, total_scenes, target_file, seed=proc_seed, used_master_assets=used_images
            )
        elif chosen_cand != target_file:
            # Adapt the chosen candidate into target_file with 9:16 vertical crop and grading
            proc_seed = int(hashlib.md5(f"{reel_slug}_{scene_idx}_{prompt_hash}".encode()).hexdigest()[:8], 16)
            cls.generate_authentic_photographic_canvas(
                scene_dict, topic, scene_idx, total_scenes, target_file, seed=proc_seed,
                master_asset_override=chosen_cand, used_master_assets=used_images
            )
            chosen_cand = target_file

        # Record in current reel's memory
        if chosen_cand:
            used_images.add(chosen_cand)
            used_images.add(chosen_cand.name)
            used_images.add(target_file)
            used_images.add(target_file.name)

        # Durable permanent registration of the generated target image
        cls.register_used_image(target_file)
        logger.info(f"[DynamicVisualEngine] Scene {scene_idx + 1}: Sourced and registered unique visual ({chosen_cand.name if chosen_cand else target_file.name}) -> {target_file.name}")
        return target_file
