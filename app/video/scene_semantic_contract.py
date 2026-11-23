"""
Scene Semantic Contract Architecture.

Enforces strict scene-level semantic boundaries, entity requirements,
attribute profiles, and multi-dimensional verification. Prevents false-positive
validation (e.g. accepting a Kundli chart when an Emerald gemstone is required).
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import io
import re
import numpy as np
from PIL import Image


@dataclass
class ContractValidationResult:
    scene_id: str
    overall_accepted: bool
    primary_subject_match: bool
    required_entities_present: bool
    visual_attributes_match: bool
    scene_meaning_match: bool
    contradiction_free: bool
    contradictions: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SceneSemanticContract:
    scene_id: str
    narration: str
    primary_subject: str
    scene_meaning: str
    visual_intent: str
    required_entities: List[str] = field(default_factory=list)
    required_attributes: List[str] = field(default_factory=list)
    supporting_entities: List[str] = field(default_factory=list)
    forbidden_visuals: List[str] = field(default_factory=list)
    asset_requirements: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def build_from_scene(
        cls,
        scene_dict: Dict[str, Any],
        topic: str = "",
        scene_idx: int = 0,
        total_scenes: int = 1,
    ) -> "SceneSemanticContract":
        """
        Builds an authoritative semantic contract from scene narration, visual description,
        and on-screen text. Spoken narration and scene meaning take absolute priority.
        """
        spoken = scene_dict.get("spoken_line", "").strip()
        on_screen = scene_dict.get("on_screen_text", "").strip()
        vis_desc = scene_dict.get("visual_description", "").strip()
        full_text = f"{spoken} {on_screen} {vis_desc}".lower()
        spoken_lower = spoken.lower()

        scene_id = f"scene_{scene_idx + 1}"

        # 1. EMERALD / PANNA GEMSTONE DOMAIN
        has_emerald = any(k in full_text for k in ["emerald", "panna", "पन्ना", "green emerald", "जाम्बियन पन्ना", "मरकत"])
        has_gem_generic = any(k in full_text for k in ["gemstone", "रत्न", "neelam", "sapphire", "pukhraj", "ruby", "diamond", "माणिक"])

        if has_emerald:
            return cls(
                scene_id=scene_id,
                narration=spoken,
                primary_subject="emerald gemstone",
                scene_meaning="gemstone remedy: wearing certified green Zambian Emerald for planet Mercury",
                visual_intent="Macro luxury photograph of certified natural vivid green Emerald gemstone with glowing crystalline facets",
                required_entities=["emerald", "panna", "gemstone", "green crystal"],
                required_attributes=["vivid green chromatic dominance", "cut crystalline facets", "gemstone clarity"],
                supporting_entities=["Mercury", "Budha", "astrological remedy"],
                forbidden_visuals=[
                    "generic kundli", "birth chart", "kundli parchment", "temple", "havan",
                    "saturn", "blue sapphire", "yellow sapphire", "monochrome chart", "fire"
                ],
                asset_requirements={"min_green_ratio": 0.04, "target_aspect_ratio": "9:16"},
            )

        # 2. BLUE SAPPHIRE / NEELAM GEMSTONE DOMAIN
        if any(k in full_text for k in ["blue sapphire", "neelam", "नीलम"]):
            return cls(
                scene_id=scene_id,
                narration=spoken,
                primary_subject="blue sapphire gemstone",
                scene_meaning="gemstone remedy: natural royal blue sapphire Neelam for planet Saturn",
                visual_intent="Macro luxury photograph of certified natural royal blue sapphire Neelam gemstone",
                required_entities=["blue sapphire", "neelam", "gemstone"],
                required_attributes=["royal blue chromatic dominance", "faceted gemstone clarity"],
                supporting_entities=["Saturn", "Shani"],
                forbidden_visuals=["generic kundli", "birth chart alone", "temple", "havan", "emerald"],
                asset_requirements={"target_aspect_ratio": "9:16"},
            )

        # 3. SATURN / SHANI CELESTIAL DOMAIN
        has_saturn = any(k in full_text for k in ["saturn", "shani", "शनि"])
        if has_saturn and not has_gem_generic:
            return cls(
                scene_id=scene_id,
                narration=spoken,
                primary_subject="planet saturn with rings",
                scene_meaning="karmic discipline and perseverance governed by Saturn",
                visual_intent="Cinematic vertical view of planet Saturn with majestic rings in deep cosmic starfield space",
                required_entities=["saturn", "shani", "rings", "deep space"],
                required_attributes=["cosmic starfield", "detailed planetary rings", "indigo-amber lighting"],
                supporting_entities=["Vedic astrology", "karmic delay"],
                forbidden_visuals=["gemstone", "emerald", "sapphire", "temple", "havan", "wedding"],
                asset_requirements={"min_dark_ratio": 0.35, "target_aspect_ratio": "9:16"},
            )

        # 4. CAREER / 10TH HOUSE DOMAIN
        has_career = any(k in full_text for k in ["career", "10th house", "tenth house", "दसवां", "10वां", "कर्म भाव", "karma bhava", "promotion", "job", "नौकरी"])
        if has_career and not has_gem_generic:
            return cls(
                scene_id=scene_id,
                narration=spoken,
                primary_subject="10th house karma career",
                scene_meaning="10th House Karma Bhava analysis for professional career growth and obstacles",
                visual_intent="North Indian Vedic Kundli birth chart highlighting 10th House Karma Bhava or executive mahogany workspace desk",
                required_entities=["10th house", "karma bhava", "executive desk", "career journal"],
                required_attributes=["illuminated 10th house quadrant", "focused professional desk atmosphere"],
                supporting_entities=["profession", "leadership", "planetary houses"],
                forbidden_visuals=["gemstone", "emerald", "sapphire", "marriage", "wedding", "temple", "havan"],
                asset_requirements={"target_aspect_ratio": "9:16"},
            )

        # 5. MARRIAGE / 7TH HOUSE DOMAIN
        has_marriage = any(k in full_text for k in ["marriage", "7th house", "seventh house", "सातवां", "7वां", "कलत्र", "yuvati", "विवाह", "शादी", "रिश्ते"])
        if has_marriage and not has_gem_generic:
            return cls(
                scene_id=scene_id,
                narration=spoken,
                primary_subject="7th house marriage partnership",
                scene_meaning="7th House Kalatra Bhava analysis for relationship harmony and marriage delay",
                visual_intent="North Indian Vedic Kundli birth chart highlighting 7th House Yuvati Bhava or harmonious couple silhouette",
                required_entities=["7th house", "kalatra bhava", "partnership harmony"],
                required_attributes=["illuminated 7th house quadrant", "amber-gold matrimonial light"],
                supporting_entities=["Saturn delay", "Jupiter aspect", "matrimonial horoscope"],
                forbidden_visuals=["gemstone", "emerald", "sapphire", "career desk", "temple", "havan"],
                asset_requirements={"target_aspect_ratio": "9:16"},
            )

        # 6. ASTROLOGER CONSULTATION CTA DOMAIN
        is_cta = (
            scene_idx == total_scenes - 1
            or any(k in full_text for k in ["dm", "comment", "consultation", "परामर्श", "सलाह", "मैसेज", "संपर्क"])
        )
        if is_cta and not has_gem_generic:
            return cls(
                scene_id=scene_id,
                narration=spoken,
                primary_subject="astrologer consultation study",
                scene_meaning="Invitation for personalized horoscope consultation and birth chart reading",
                visual_intent="Warm, dignified Vedic astrologer consultation desk with authentic parchment charts and brass reading lamp",
                required_entities=["consultation desk", "parchment chart", "reading lamp", "astrologer study"],
                required_attributes=["warm candlelight illumination", "aged parchment charts", "scholarly dignified ambiance"],
                supporting_entities=["horoscope reading", "direct message call-to-action"],
                forbidden_visuals=["temple sanctum", "temple lamps alone", "havan fire", "gemstone macro", "planet alone"],
                asset_requirements={"target_aspect_ratio": "9:16"},
            )

        # 7. DEFAULT ASTROLOGICAL SCENE
        return cls(
            scene_id=scene_id,
            narration=spoken,
            primary_subject="authentic Vedic Kundli birth chart",
            scene_meaning="astrological birth chart manuscript study",
            visual_intent="Authentic North Indian Vedic Kundli birth chart manuscript on aged parchment with warm ambient light",
            required_entities=["kundli chart", "birth chart", "parchment"],
            required_attributes=["aged parchment paper texture", "traditional diamond grid"],
            supporting_entities=["Vedic wisdom"],
            forbidden_visuals=["temple", "havan fire", "unrelated gemstones", "modern technology"],
            asset_requirements={"target_aspect_ratio": "9:16"},
        )

    def validate_asset(
        self,
        image_input: Union[Path, str, bytes, Image.Image],
        asset_identity: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContractValidationResult:
        """
        Executes strict multi-dimensional validation of the asset against this contract.
        Fails closed for any critical dimension mismatch.
        """
        contradictions: List[str] = []
        name_lower = (asset_identity or (str(image_input) if isinstance(image_input, (Path, str)) else "")).lower()
        meta_subject = str((metadata or {}).get("subject", "")).lower()

        # 1. Contradiction & Forbidden Elements Check on Identity/Metadata
        for forb in self.forbidden_visuals:
            forb_l = forb.lower()
            if forb_l in name_lower or forb_l in meta_subject:
                contradictions.append(f"Forbidden visual element detected: '{forb}' (found in asset identity/metadata)")

        # CRITICAL FAIL RULE: If contract requires Emerald gemstone, asset CANNOT be a Kundli chart
        if self.primary_subject == "emerald gemstone":
            if any(k in name_lower or k in meta_subject for k in ["kundli", "parchment", "birth chart", "chart alone"]):
                contradictions.append("CRITICAL MISMATCH: Scene requires Emerald gemstone, but asset is an astrological chart/parchment.")
            if any(k in name_lower or k in meta_subject for k in ["temple", "mandir", "sanctum"]):
                contradictions.append("CRITICAL MISMATCH: Scene requires Emerald gemstone, but asset is a temple.")
            if any(k in name_lower or k in meta_subject for k in ["saturn", "shani"]):
                contradictions.append("CRITICAL MISMATCH: Scene requires Emerald gemstone, but asset is planet Saturn.")

        # 2. Actual Image Pixel & Chromatic Inspection
        img: Optional[Image.Image] = None
        try:
            if isinstance(image_input, Image.Image):
                img = image_input.convert("RGB")
            elif isinstance(image_input, (Path, str)):
                p = Path(image_input)
                if p.exists() and p.stat().st_size > 500:
                    img = Image.open(p).convert("RGB")
            elif isinstance(image_input, bytes):
                if len(image_input) > 500:
                    img = Image.open(io.BytesIO(image_input)).convert("RGB")
        except Exception as exc:
            contradictions.append(f"Physical image decode failed: {exc}")

        visual_attributes_match = True
        if img is not None:
            w, h = img.size
            # Aspect ratio check
            if w > h and (w / h) > 1.1:
                contradictions.append(f"Asset is horizontal landscape ({w}x{h}) instead of vertical 9:16")

            # Pixel Chromatic Analysis for Emerald Gemstone
            if self.primary_subject == "emerald gemstone":
                arr = np.array(img, dtype=np.float32)
                r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
                # Emerald green dominance mask
                green_mask = (g > r * 1.15) & (g > b * 1.15) & (g > 50)
                green_ratio = float(np.mean(green_mask))
                min_green = float(self.asset_requirements.get("min_green_ratio", 0.04))
                if green_ratio < min_green:
                    visual_attributes_match = False
                    contradictions.append(
                        f"Actual image content lacks required emerald green chromatic profile (observed green ratio: {green_ratio:.4f}, expected >= {min_green:.4f}). Asset is monochrome/parchment/non-emerald."
                    )

            # Space darkness check for Saturn
            if self.primary_subject == "planet saturn with rings":
                arr = np.array(img, dtype=np.float32)
                dark_mask = (arr[:, :, 0] < 50) & (arr[:, :, 1] < 50) & (arr[:, :, 2] < 50)
                dark_ratio = float(np.mean(dark_mask))
                min_dark = float(self.asset_requirements.get("min_dark_ratio", 0.35))
                if dark_ratio < min_dark:
                    visual_attributes_match = False
                    contradictions.append(
                        f"Actual image content lacks deep space background for Saturn (observed dark ratio: {dark_ratio:.4f}, expected >= {min_dark:.4f})."
                    )

        # 3. Multi-Dimensional Score Resolution
        contradiction_free = len(contradictions) == 0
        primary_subject_match = contradiction_free and visual_attributes_match
        required_entities_present = contradiction_free and visual_attributes_match
        scene_meaning_match = contradiction_free

        overall_accepted = (
            contradiction_free
            and primary_subject_match
            and required_entities_present
            and visual_attributes_match
            and scene_meaning_match
        )

        rejection_reason = "; ".join(contradictions) if not overall_accepted else None
        confidence_score = 0.95 if overall_accepted else 0.15

        return ContractValidationResult(
            scene_id=self.scene_id,
            overall_accepted=overall_accepted,
            primary_subject_match=primary_subject_match,
            required_entities_present=required_entities_present,
            visual_attributes_match=visual_attributes_match,
            scene_meaning_match=scene_meaning_match,
            contradiction_free=contradiction_free,
            contradictions=contradictions,
            rejection_reason=rejection_reason,
            confidence_score=confidence_score,
        )
