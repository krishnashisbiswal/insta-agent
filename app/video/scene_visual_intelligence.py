"""
Scene Visual Intelligence Pipeline (Script-Driven, Emotion-Aware).
Translates Reel narration into structured, emotionally resonant scene visual
specifications and detailed image prompts:

1. Script is Primary Source of Truth: Visuals are derived strictly from the
   exact narration text, emotional state, narrative context, and visual metaphors.
2. Anti-Generic Filtering: Rejects automatic dumping of floating planets,
   zodiac wheels, or meditating figures unless explicitly demanded by narration.
3. 20 Canonical Emotions: Dynamically detects emotion (Fear, Anxiety, Loneliness,
   Sadness, Confusion, Frustration, Betrayal, Hope, Curiosity, Mystery, Confidence,
   Peace, Relief, Empowerment, Awe, Devotion, Joy, Urgency, Realization, Transformation)
   and modulates composition, lighting, and color.
4. Visual Diversity Tracker: Enforces cinematic progression (Close-up -> Wide
   -> Symbolic Metaphor -> Epiphany -> Transformation -> Resolution) and bars
   consecutive repeating compositions or metaphors within the Reel.
5. Traceability: Persists complete audit records in storage/scene_visual_traceability.json.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("SceneVisualIntelligence")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = PROJECT_ROOT / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
TRACEABILITY_LOG_FILE = STORAGE_DIR / "scene_visual_traceability.json"

# Canonical 20 Emotions
VALID_EMOTIONS = [
    "Fear", "Anxiety", "Loneliness", "Sadness", "Confusion",
    "Frustration", "Betrayal", "Hope", "Curiosity", "Mystery",
    "Confidence", "Peace", "Relief", "Empowerment", "Awe",
    "Devotion", "Joy", "Urgency", "Realization", "Transformation"
]
CANONICAL_EMOTIONS = VALID_EMOTIONS

# Canonical Visual Styles
VALID_VISUAL_STYLES = [
    "Cinematic photorealism",
    "Mythological cinematic realism",
    "Surreal symbolic art",
    "Dark cinematic realism",
    "Ethereal spiritual realism",
    "Documentary realism",
    "Dramatic portrait photography",
    "High-end fantasy realism"
]

# Visual Direction per Emotion
EMOTION_VISUAL_MAP: Dict[str, Dict[str, str]] = {
    "Fear": {
        "lighting": "oppressive high-contrast chiaroscuro, heavy threatening shadows, sliver of cold edge light",
        "composition": "cramped off-center framing, vulnerable low subject positioning, looming atmospheric depth",
        "color_palette": "deep obsidian, murky charcoal, cold desaturated slate, hint of alarm crimson",
        "viewer_feeling": "gripping tension and urgent apprehension",
        "posture": "defensive, tense shoulders, guarded posture, vigilant eyes"
    },
    "Anxiety": {
        "lighting": "unsettled flickering amber task light against cold restless shadows",
        "composition": "tighter framing, restless negative space, asymmetrical tension",
        "color_palette": "stormy gray, uneasy pale ochre, deep bruised indigo",
        "viewer_feeling": "visceral unease and breathless anticipation",
        "posture": "fidgeting hands, troubled gaze, internal turmoil expressed in tightened jaw"
    },
    "Loneliness": {
        "lighting": "cool, distant diffused twilight, solitary single-source soft glow",
        "composition": "extreme wide shot, solitary figure dwarfed by vast empty environment, expansive negative space",
        "color_palette": "dusty twilight blue, lonely pale ash, solitary faint amber",
        "viewer_feeling": "profound solitude and empathetic longing",
        "posture": "downcast head, arms folded close to chest, solitary stillness"
    },
    "Sadness": {
        "lighting": "subdued overcast daylight filtered through rain mist, soft melancholy reflections",
        "composition": "contemplative medium close-up, downward visual vectors, gentle isolation",
        "color_palette": "muted slate blue, washed-out indigo, soft rain gray, weathered timber",
        "viewer_feeling": "deep sorrow, emotional weight, and heartfelt vulnerability",
        "posture": "slumped shoulders, head tilted down, eyes glistening with unspoken sorrow"
    },
    "Confusion": {
        "lighting": "fragmented cross-lighting, fractured shadow patterns, hazy diffused illumination",
        "composition": "disorienting Dutch angle, labyrinthine background lines, seeking focal point",
        "color_palette": "turbulent ochre, hazy smoke violet, muted bronze, murky teal",
        "viewer_feeling": "seeking orientation and craving clarity",
        "posture": "hesitant step, searching eyes, hand touching brow in perplexity"
    },
    "Frustration": {
        "lighting": "stark hard-edged lighting, harsh angular shadows emphasizing friction",
        "composition": "confrontational angle, physical obstacle or barrier cutting across the frame",
        "color_palette": "scorched rust, abrasive iron gray, sharp amber, dark basalt",
        "viewer_feeling": "palpable tension, resistance, and shared struggle",
        "posture": "clenched fists, tight jaw, strained neck muscles, resisting an invisible weight"
    },
    "Betrayal": {
        "lighting": "cold stark side-lighting, harsh rim light, fractured reflections",
        "composition": "protagonist in sharp foreground focus with distant blurry silhouettes turned indifferent",
        "color_palette": "chilled cyan, pale bone white, severed crimson ribbon, deep shadow black",
        "viewer_feeling": "sharp heartbreak, sudden awakening, and cold reality",
        "posture": "reeling slightly, hand over chest, stunned disbelief turning to cold resolve"
    },
    "Hope": {
        "lighting": "gradual warm golden sunrise light cutting through parting storm clouds, luminous rim light",
        "composition": "upward diagonal visual flow, subject looking toward a brighter opening horizon",
        "color_palette": "soft sunrise gold, tender amber, pale dawn sky blue, fresh dew green",
        "viewer_feeling": "renewed faith, rising warmth, and quiet optimism",
        "posture": "lifting chin, softening facial expression, chest opening forward"
    },
    "Curiosity": {
        "lighting": "intimate directional beam of light illuminating a hidden focal detail, soft surrounding bokeh",
        "composition": "compelling macro / medium close-up, partial occlusion creating intrigue",
        "color_palette": "rich warm parchment, luminous brass, deep emerald, warm candlelight",
        "viewer_feeling": "intense fascination and eager desire to discover the truth",
        "posture": "leaning forward intently, focused gaze, hand reaching toward discovery"
    },
    "Mystery": {
        "lighting": "atmospheric soft chiaroscuro, drifting veil of translucent mist, hidden light source",
        "composition": "layered depth of field, partial silhouette, ancient architectural veil",
        "color_palette": "deep midnight indigo, ethereal silver mist, antique gold accent",
        "viewer_feeling": "spellbound wonder and reverence for the unknown",
        "posture": "poised quiet contemplation, calm stillness, enigmatic expression"
    },
    "Confidence": {
        "lighting": "clean crisp key lighting, sculpted heroic rim light, well-defined contours",
        "composition": "centered grounded composition, direct eye-level perspective, powerful vertical posture",
        "color_palette": "noble deep navy, warm burnished gold, crisp white, rich walnut",
        "viewer_feeling": "complete certainty, authority, and steady calm",
        "posture": "tall upright spine, steady level gaze, relaxed open palms"
    },
    "Peace": {
        "lighting": "soft diffused morning window light, tranquil harmonic radiance, no harsh shadows",
        "composition": "balanced harmonious symmetrical framing, tranquil still waters, ample clean space",
        "color_palette": "soft sage green, serene sky cyan, warm alabaster, gentle lotus pink",
        "viewer_feeling": "deep stillness, unburdened serenity, and restorative calm",
        "posture": "soft relaxed facial features, steady peaceful breathing, gentle resting hands"
    },
    "Relief": {
        "lighting": "warm golden afternoon sun washing over a landscape after heavy rain",
        "composition": "open expansive framing, unencumbered horizon, clear breathing space",
        "color_palette": "radiant amber, fresh rain-washed earth, golden honey, clear azure",
        "viewer_feeling": "deep exhale, shedding of heavy burdens, and lighthearted freedom",
        "posture": "shoulders dropping in profound relaxation, eyes closed in grateful exhale"
    },
    "Empowerment": {
        "lighting": "bold dramatic low-angle backlight, radiant golden rim separating subject from dark past",
        "composition": "commanding low-angle perspective, dynamic upward lines, majestic headroom",
        "color_palette": "radiant royal saffron, blazing gold, deep bronze, commanding charcoal",
        "viewer_feeling": "surging inner strength, unstoppable courage, and sovereignty",
        "posture": "powerful grounded stance, shoulders back, eyes burning with quiet purpose"
    },
    "Awe": {
        "lighting": "monumental celestial radiance, god-rays streaming through ancient stone or majestic sky",
        "composition": "grand scale juxtaposition, human element humbled before immense cosmic or natural beauty",
        "color_palette": "celestial violet, shimmering starlight gold, deep cobalt, luminous cosmic white",
        "viewer_feeling": "profound humility, breathtaking wonder, and cosmic perspective",
        "posture": "head tilted back gazing upward, lips slightly parted in reverence"
    },
    "Devotion": {
        "lighting": "warm sacred oil lamp glow, dancing flame illumination, reverent golden chiaroscuro",
        "composition": "intimate sacred altar framing, respectful eye-level or slight high-angle reverence",
        "color_palette": "sacred saffron, temple brass gold, deep terracotta red, sandalwood yellow",
        "viewer_feeling": "sacred surrender, spiritual purity, and transcendent connection",
        "posture": "hands gently folded or held in gratitude, bowed head, peaceful devotion"
    },
    "Joy": {
        "lighting": "brilliant vibrant sunlight, dancing lens flares, warm sparkling reflections",
        "composition": "dynamic energetic framing, expansive upward motion, joyful movement",
        "color_palette": "vibrant marigold yellow, radiant coral, warm golden sunlight, sky turquoise",
        "viewer_feeling": "pure exuberance, contagious happiness, and emotional release",
        "posture": "radiant open smile, head thrown back, open welcoming posture"
    },
    "Urgency": {
        "lighting": "high-contrast dramatic side-lighting, stark dynamic shadow cuts, flashing intensity",
        "composition": "tight dynamic angle, rapid forward momentum, visual tension at the edge of the frame",
        "color_palette": "blazing signal amber, sharp obsidian black, high-visibility white, warning crimson",
        "viewer_feeling": "immediate alertness, sharp focus, and compelling necessity to act",
        "posture": "mid-stride forward motion, intense focused eye contact, decisive movement"
    },
    "Realization": {
        "lighting": "focused beam of warm crystalline light cutting directly through shadow onto subject's eyes",
        "composition": "dramatic medium close-up, clear depth of field, moment of insight captured in eyes",
        "color_palette": "illuminated gold, deep midnight navy, warm amber, pure clarity white",
        "viewer_feeling": "thrilling epiphany, sudden clarity, and profound understanding",
        "posture": "sudden stillness, eyes widening with understanding, hand opening in revelation"
    },
    "Transformation": {
        "lighting": "dual-tone lighting split across the frame: cold shadow behind, radiant golden dawn ahead",
        "composition": "threshold framing, subject stepping across doorway, archway, or dividing light line",
        "color_palette": "gradient transition from stormy indigo to triumphant golden dawn",
        "viewer_feeling": "profound renewal, crossing over to a higher life chapter",
        "posture": "stepping boldly forward across the threshold, leaving old shadows behind"
    }
}


@dataclass
class SceneVisualSpecification:
    """Authoritative, structured visual specification generated per scene."""
    scene_id: int
    narration: str
    core_meaning: str
    emotion: str
    emotion_intensity: float
    viewer_feeling: str
    visual_concept: str
    visual_metaphor: str
    subject: str
    action: str
    environment: str
    composition: str
    lighting: str
    color_palette: str
    camera_angle: str
    continuity_notes: str
    image_prompt: str
    visual_style: str = "Cinematic photorealism"
    semantic_quality_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # Aliases for backward compatibility with SceneVisualPlan
    @property
    def exact_narration(self) -> str:
        return self.narration

    @property
    def main_subject(self) -> str:
        return self.subject

    @property
    def primary_subject(self) -> str:
        return self.subject

    @property
    def subject_action(self) -> str:
        return self.action

    @property
    def mood(self) -> str:
        return self.emotion

    @property
    def generation_prompt(self) -> str:
        return self.image_prompt

    @property
    def camera_framing(self) -> str:
        return self.camera_angle


class ReelVisualDiversityTracker:
    """Tracks and enforces visual diversity across consecutive scenes in a single Reel."""

    def __init__(self) -> None:
        self.used_subjects: Set[str] = set()
        self.used_concepts: Set[str] = set()
        self.used_environments: Set[str] = set()
        self.used_compositions: List[str] = []
        self.used_camera_angles: List[str] = []
        self.used_metaphors: Set[str] = set()
        self.used_palettes: List[str] = []

    def record_scene(self, spec: SceneVisualSpecification) -> None:
        self.used_subjects.add(spec.subject.lower())
        self.used_concepts.add(spec.visual_concept.lower())
        self.used_environments.add(spec.environment.lower())
        self.used_compositions.append(spec.composition)
        self.used_camera_angles.append(spec.camera_angle)
        if spec.visual_metaphor:
            self.used_metaphors.add(spec.visual_metaphor.lower())
        self.used_palettes.append(spec.color_palette)

    def is_concept_repeated(self, concept: str) -> bool:
        c_low = concept.lower()
        return any(c_low in u or u in c_low for u in self.used_concepts)

    def get_recommended_angle(self, scene_idx: int, total_scenes: int) -> str:
        """Enforces narrative visual angle progression."""
        progression = [
            "Dramatic medium close-up, eye-level engagement",                      # Hook
            "Expansive wide atmospheric shot, vast environmental scale",           # Tension / Problem
            "Medium dynamic storytelling angle, layered diagonal depth",           # Deeper Explanation
            "Close-up focal perspective capturing intense emotional expression",   # Epiphany / Realization
            "Low-angle dynamic hero perspective, upward diagonal movement",        # Breakthrough / Action
            "Cinematic wide threshold angle, dramatic light transition",           # Transformation
            "Grounded medium hero shot, centered composed authority"              # Resolution / CTA
        ]
        if scene_idx < len(progression):
            candidate = progression[scene_idx]
        else:
            candidate = progression[-1]

        # Prevent exact repetition with immediately preceding scene
        if self.used_camera_angles and self.used_camera_angles[-1] == candidate:
            candidate = "Off-axis 45-degree cinematic perspective, dynamic depth"
        return candidate


class SceneVisualIntelligence:
    """
    Intelligent engine analyzing script narration to produce scene visual specifications.
    Translates raw narration into concrete, emotionally congruent, non-generic imagery.
    """

    @classmethod
    def analyze_scene(
        cls,
        scene_dict: Dict[str, Any],
        scene_idx: int,
        total_scenes: int = 5,
        prev_scene: Optional[Dict[str, Any]] = None,
        next_scene: Optional[Dict[str, Any]] = None,
        topic: str = "",
        diversity_tracker: Optional[ReelVisualDiversityTracker] = None,
    ) -> SceneVisualSpecification:
        """
        Main intelligence pipeline converting scene narration to a SceneVisualSpecification.
        """
        tracker = diversity_tracker or ReelVisualDiversityTracker()

        spoken = scene_dict.get("spoken_line", "").strip()
        on_screen = scene_dict.get("on_screen_text", "").strip()
        vis_desc = scene_dict.get("visual_description", "").strip()

        # Exact narration text is the primary source of truth (exclude old visual descriptions from matching)
        narration = spoken or on_screen or vis_desc or topic
        script_text = f"{spoken} {on_screen}".strip().lower()
        text_lower = f"{spoken} {on_screen} {vis_desc}".lower()

        # Step 1: Direct literal script matching takes precedence for core Vedic & astrological subjects
        direct_match = cls._get_direct_literal_match(script_text, scene_idx, total_scenes)

        ai_data = None
        if not direct_match:
            # Step 2: Attempt LLM-based Scene Script Understanding via Gemini
            ai_data = cls._analyze_scene_with_ai(
                narration=narration,
                on_screen=on_screen,
                scene_idx=scene_idx,
                total_scenes=total_scenes,
                topic=topic,
                prev_narration=prev_scene.get("spoken_line", "") if prev_scene else "",
                next_narration=next_scene.get("spoken_line", "") if next_scene else "",
            )

        if ai_data:
            raw_emotion = str(ai_data.get("emotion", "Hope"))
            emotion = "Hope"
            for valid_e in VALID_EMOTIONS:
                if valid_e.lower() in raw_emotion.lower():
                    emotion = valid_e
                    break

            try:
                intensity = float(ai_data.get("emotion_intensity", 0.85))
            except (ValueError, TypeError):
                intensity = 0.85

            emotion_dir = EMOTION_VISUAL_MAP.get(emotion, EMOTION_VISUAL_MAP["Hope"])
            meaning = str(ai_data.get("core_meaning") or f"Communicating the emotional essence of: {emotion}")
            concept = str(ai_data.get("visual_concept") or "")
            metaphor = str(ai_data.get("visual_metaphor") or concept)
            subject = str(ai_data.get("subject") or "expressive protagonist")
            action = str(ai_data.get("action") or "interacting meaningfully with surroundings")
            env = str(ai_data.get("environment") or "atmospheric cinematic setting")
            camera_angle = str(ai_data.get("camera_angle") or tracker.get_recommended_angle(scene_idx, total_scenes))
            composition = str(ai_data.get("composition") or f"{camera_angle}, {emotion_dir['composition']}")
            lighting = str(ai_data.get("lighting") or emotion_dir["lighting"])
            palette = str(ai_data.get("color_palette") or emotion_dir["color_palette"])
            viewer_feeling = str(ai_data.get("viewer_feeling") or emotion_dir["viewer_feeling"])
            visual_style = str(ai_data.get("visual_style") or cls._determine_visual_style(text_lower, emotion, topic))
            posture = emotion_dir.get("posture", "poised with quiet strength and grounded confidence")
            prompt = str(ai_data.get("image_prompt") or "")
            if not prompt or len(prompt) < 30:
                prompt = cls._build_detailed_prompt(
                    subject=subject,
                    action=action,
                    posture=posture,
                    environment=env,
                    emotion=emotion,
                    lighting=lighting,
                    composition=composition,
                    color_palette=palette,
                    visual_style=visual_style,
                    metaphor=metaphor
                )
            elif "9:16 vertical" not in prompt:
                prompt = f"cinematic photorealistic 9:16 vertical portrait composition, {prompt}"

            prev_sub = prev_scene.get("spoken_line", "")[:40] if prev_scene else "Opening scene of narrative"
            next_sub = next_scene.get("spoken_line", "")[:40] if next_scene else "Narrative resolution"
            continuity_notes = f"Preceded by [{prev_sub}], leads toward [{next_sub}]. Maintain {visual_style} tone."

            logger.info(
                f"[SceneVisualIntelligence] Scene {scene_idx + 1}/{total_scenes} AI-planned: "
                f"Subject='{subject[:50]}' | Emotion={emotion} | Concept='{concept[:60]}'"
            )
        else:
            # Fallback to local semantic rules
            # Step 1: Detect Emotion dynamically
            emotion, intensity = cls._detect_emotion(narration, text_lower, scene_idx, total_scenes)
            emotion_dir = EMOTION_VISUAL_MAP.get(emotion, EMOTION_VISUAL_MAP["Hope"])

            # Step 2: Determine Core Meaning & Visual Metaphor
            meaning, concept, metaphor, subject, action, env = cls._derive_visual_metaphor(
                narration=narration,
                text_lower=text_lower,
                emotion=emotion,
                scene_idx=scene_idx,
                total_scenes=total_scenes,
                topic=topic,
                tracker=tracker
            )

            # Step 3: Determine Visual Style matching content
            visual_style = cls._determine_visual_style(text_lower, emotion, topic)

            # Step 4: Camera angle & composition enforcing diversity progression
            camera_angle = tracker.get_recommended_angle(scene_idx, total_scenes)
            composition = f"{camera_angle}, {emotion_dir['composition']}"

            lighting = emotion_dir["lighting"]
            palette = emotion_dir["color_palette"]
            viewer_feeling = emotion_dir["viewer_feeling"]
            posture = emotion_dir["posture"]

            # Step 5: Continuity notes from preceding and following scenes
            prev_sub = prev_scene.get("spoken_line", "")[:40] if prev_scene else "Opening scene of narrative"
            next_sub = next_scene.get("spoken_line", "")[:40] if next_scene else "Narrative resolution"
            continuity_notes = f"Preceded by [{prev_sub}], leads toward [{next_sub}]. Maintain {visual_style} tone."

            # Step 6: Construct full, detailed 14-point image generation prompt
            prompt = cls._build_detailed_prompt(
                subject=subject,
                action=action,
                posture=posture,
                environment=env,
                emotion=emotion,
                lighting=lighting,
                composition=composition,
                color_palette=palette,
                visual_style=visual_style,
                metaphor=metaphor
            )

        spec = SceneVisualSpecification(
            scene_id=scene_idx + 1,
            narration=narration,
            core_meaning=meaning,
            emotion=emotion,
            emotion_intensity=intensity,
            viewer_feeling=viewer_feeling,
            visual_concept=concept,
            visual_metaphor=metaphor,
            subject=subject,
            action=action,
            environment=env,
            composition=composition,
            lighting=lighting,
            color_palette=palette,
            camera_angle=camera_angle,
            continuity_notes=continuity_notes,
            image_prompt=prompt,
            visual_style=visual_style,
            semantic_quality_score=0.95
        )

        tracker.record_scene(spec)
        return spec

    @classmethod
    def _analyze_scene_with_ai(
        cls,
        narration: str,
        on_screen: str,
        scene_idx: int,
        total_scenes: int,
        topic: str = "",
        prev_narration: str = "",
        next_narration: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini LLM to interpret scene script narration in context and generate
        a 100% script-faithful, emotion-aware visual concept, subject, action, and detailed prompt.
        """
        if os.getenv("TESTING", "").lower() in ("true", "1") or os.getenv("MOCK_AI", "").lower() in ("true", "1"):
            return None

        try:
            from app.agents.gemini_client import generate_text, parse_json_response

            prompt = f"""You are the master creative visual director for @neodivinestore.in, a premium Vedic Astrology, Gemstone Energy, and Sacred Karma Instagram channel.
Your goal is to design SUPER ATTRACTIVE, EYE-CATCHING, HIGH-QUALITY, SCRIPT-DRIVEN visual scenes that make Reels go viral.

Reel Context:
Topic: "{topic}"
Scene {scene_idx + 1} of {total_scenes}:
Spoken Narration: "{narration}"
On-screen text: "{on_screen}"
Previous scene context: "{prev_narration}"
Next scene context: "{next_narration}"

CREATIVE DIRECTION MANDATE (HIGH-END AESTHETIC):
1. SCRIPT IS PRIMARY TRUTH: The visual must directly illustrate or evoke the exact situation, emotion, object, or action in the spoken narration.
2. SACRED, MAJESTIC & CINEMATIC VIBE: The channel's visual universe is majestic, mystical, rich, and visually breathtaking.
   - Use dramatic lighting: Golden hour rays, warm amber oil lamps, celestial dusk, glowing auric light, deep chiaroscuro, volumetric haze.
   - Rich color grading: Imperial gold, deep midnight indigo, warm terracotta, emerald green, royal sapphire blue, warm sandstone.
3. STRICT BAN ON LOW-EFFORT / MUNDANE MODERN CLICHÉS:
   - NEVER generate: mundane domestic scenes (dining tables, kitchen, modern bedrooms, alarm clocks, casual hoodies, people slouching on phones, grey concrete).
   - NEVER generate: cheap flat clip-art, generic floating cartoon planets, or synthetic plastic 3D wireframes.
4. EXACT SCRIPT-DRIVEN LITERAL VISUAL TRANSLATIONS:
   - Tiger's Eye: If the scene explicitly mentions Tiger's Eye -> Depict an authentic radiant Tiger's Eye gemstone and bead bracelet showing vivid golden chatoyancy on sacred velvet or ancient Sanskrit parchment!
   - 7th House & Marriage / Relationships: If the scene mentions 7th house, marriage, or partnership -> Depict an authentic Vedic Kundli birth chart highlighting the 7th house (Yuvati Bhava) and partnership harmony symbolism (two respectful silhouettes or wedding knot on aged parchment). NEVER gemstones, havan, or temple!
   - 10th House & Career / Profession: If the scene mentions 10th house, career, job, or workplace struggle/breakthrough -> Depict an authentic Vedic Kundli birth chart highlighting the 10th house (Karma Bhava) in radiant golden light, or an executive study desk with journal and morning light. NEVER gemstones, havan, or temple!
   - Emerald & Mercury: If the scene mentions Emerald or Mercury -> Depict a natural certified vivid green Zambian Emerald gemstone glowing with crystalline facets beside Mercury planetary symbolism!
   - Sun & Rahu: If the scene mentions Sun and Rahu / Rahu in Kundali -> Depict a glowing sacred Vedic Kundli birth chart with Sun and Rahu highlighted in contrasting golden fire and dark cosmic eclipse shadow!
   - 12th House Energy: If the scene mentions 12th house / energy drain -> Depict an authentic Vedic Kundli birth chart with the 12th house distinctly illuminated in gold and ethereal energy streams dissipating outward!
   - Mars (Mangal): If the scene mentions Mars / Mangal -> Depict the majestic fiery red planet Mars glowing in deep cosmic space with powerful crimson energy flares!
   - Saturn (Shani): If the scene mentions Saturn/Shani cosmic aspect -> Depict the magnificent planet Saturn with detailed crystalline ice rings casting focused aspect rays!
   - Gemstones: ONLY if the scene explicitly mentions gemstones (Neelam, Ruby, Emerald, Pukhraj, Diamond, etc.) -> Depict radiant natural gemstones glowing with vibrant internal fire on sacred scriptures! NEVER insert gemstones for non-gemstone narration!
   - Call to Action / DM: If the scene is CTA / DM / consultation -> Depict a warm, dignified Vedic astrologer consultation desk with handwritten horoscope charts on parchment, antique brass reading lamp, clean dark wood desk inviting private guidance! NEVER force gemstones or temples on CTA!

Return ONLY a valid JSON object with the following fields:
{{
  "core_meaning": "What this scene actually communicates",
  "emotion": "Dominant emotion from: Fear, Anxiety, Loneliness, Sadness, Confusion, Frustration, Betrayal, Hope, Curiosity, Mystery, Confidence, Peace, Relief, Empowerment, Awe, Devotion, Joy, Urgency, Realization, Transformation",
  "emotion_intensity": 0.85,
  "viewer_feeling": "What the viewer should feel",
  "visual_concept": "Eye-catching, majestic visual idea",
  "visual_metaphor": "Metaphor matching the Vedic/astrological narrative",
  "subject": "Hero subject (majestic, dignified, captivating)",
  "action": "Action or posture with emotional resonance",
  "environment": "Grand, atmospheric, or mystical setting",
  "composition": "Cinematic vertical 9:16 framing",
  "lighting": "Dramatic golden hour, volumetric rays, or glowing aura",
  "color_palette": "Rich cohesive palette (e.g. Imperial Gold, Midnight Indigo)",
  "camera_angle": "Cinematic camera angle",
  "visual_style": "Cinematic photorealism or Ethereal spiritual realism",
  "image_prompt": "Concise (under 320 chars) prompt with maximum aesthetic punch: vertical 9:16 cinematic masterpiece, 8k, [Subject & Action], [Atmospheric Environment], [Dramatic Lighting & Palette], hyper-realistic, award-winning photography, no text overlays, no watermarks"
}}"""

            res = generate_text(prompt)
            data = parse_json_response(res)
            if data and isinstance(data, dict) and data.get("subject") and data.get("image_prompt"):
                return data
        except Exception as e:
            logger.debug(f"[SceneVisualIntelligence] AI scene analysis fallback to semantic rules: {e}")
        return None

    @classmethod
    def _detect_emotion(
        cls,
        narration: str,
        text_lower: str,
        scene_idx: int,
        total_scenes: int
    ) -> Tuple[str, float]:
        """Detects emotional state from narration semantics."""
        # Betrayal & Unreciprocated effort
        if any(w in text_lower for w in ["never give anything back", "never give back", "betray", "cheat", "धोखा", "छल", "swallow", "पीठ में छुरा"]):
            return "Betrayal", 0.90

        # Loneliness & Exhaustion of waiting
        if any(w in text_lower for w in ["never chooses you", "tired of waiting", "tired of chasing", "alone", "lonely", "इंतजार", "अकेले", "थक", "chasing people who have already left"]):
            return "Loneliness", 0.88

        # Fear & Threat
        if any(w in text_lower for w in ["danger", "threat", "destroy", "fear", "खतरा", "विनाश", "भय", "कहर", "भारी नुकसान", "चेतावनी", "warning", "ruin"]):
            return "Fear", 0.85

        # Anxiety & Mental Agitation
        if any(w in text_lower for w in ["anxiety", "restless", "confused", "stress", "तनाव", "बेचैनी", "घबराहट", "चिंता", "3 am", "अनिद्रा"]):
            return "Anxiety", 0.82

        # Financial Breakthrough & Hope
        if any(w in text_lower for w in ["financial breakthrough", "breakthrough", "coming after", "abundance", "wealth", "धन लाभ", "बरकत", "सफलता", "समृद्धि"]):
            return "Hope", 0.86

        # Frustration & Struggle against obstacles
        if any(w in text_lower for w in ["testing your patience", "patience", "struggle", "testing", "कठिन", "परीक्षा", "बाधा", "रुकावट", "blockage"]):
            return "Frustration", 0.80

        # Sacred Devotion & Spiritual Stillness
        if any(w in text_lower for w in ["shiva", "mahadev", "lord shiva", "शिव", "महादेव", "silence is powerful", "prayer", "प्रार्थना", "भक्ति", "साधना"]):
            return "Devotion", 0.92

        # Transformation & Major life shift
        if any(w in text_lower for w in ["about to change", "transform", "shift", "नया मोड़", "बदलाव", "परिवर्तन", "threshold", "new chapter"]):
            return "Transformation", 0.88

        # Realization & Sudden Epiphany
        if any(w in text_lower for w in ["realize", "truth", "secret", "reality", "सच", "रहस्य", "चौंकाने वाला", "eye opening", "listen carefully", "stop wearing"]):
            return "Realization", 0.84

        # Urgency & Immediate Action
        if any(w in text_lower for w in ["immediately", "stop", "urgent", "don't make this mistake", "तुरंत", "अभी", "सावधान", "गलती मत करना"]):
            return "Urgency", 0.85

        # Peace & Grounded Relief
        if any(w in text_lower for w in ["calm", "peace", "healed", "relief", "शांति", "राहत", "सुकून", "स्थिरता"]):
            return "Peace", 0.80

        # Empowerment
        if any(w in text_lower for w in ["power", "strength", "lead", "conquer", "शक्ति", "सामर्थ्य", "जीत"]):
            return "Empowerment", 0.85

        # Default narrative curve
        if scene_idx == 0:
            return "Curiosity", 0.80
        elif scene_idx == 1:
            return "Anxiety", 0.75
        elif scene_idx == total_scenes - 1:
            return "Confidence", 0.82
        elif scene_idx == total_scenes - 2:
            return "Transformation", 0.80
        return "Realization", 0.75

    @classmethod
    def _get_direct_literal_match(
        cls,
        text_lower: str,
        scene_idx: int,
        total_scenes: int
    ) -> Optional[Tuple[str, str, str, str, str, str]]:
        """
        Direct 1-to-1 literal script mapping for core Vedic astrology & gemstone subjects.
        Returns: (core_meaning, visual_concept, visual_metaphor, subject, action, environment)
        """
        # 1. Tiger's Eye gemstone (Explicit mention only)
        if any(w in text_lower for w in ["tiger's eye", "tiger eye", "टाइगर आई", "टाइगर"]):
            return (
                "The grounding yet intense energetic frequency of genuine Tiger's Eye",
                "An ultra-sharp, luxurious macro shot of an authentic radiant Tiger's Eye gemstone and bead bracelet showing intense golden-brown silky chatoyancy (tiger eye shimmer) resting on sacred velvet or ancient Sanskrit parchment, glowing in warm volumetric golden light",
                "The golden chatoyant eye of the earth grounding scattered energy",
                "An authentic, radiant polished Tiger's Eye gemstone and bracelet showing vivid golden chatoyancy",
                "resting prominently on aged Sanskrit parchment, reflecting warm amber volumetric light rays",
                "an opulent astrological sanctuary with soft candlelight and ancient Vedic manuscripts"
            )

        # 2. 7th House & Marriage / Relationships (Strict: relationship/marriage dynamics, delays, or 7th house)
        has_7th_or_marriage = any(w in text_lower for w in [
            "7th house", "seventh house", "7th bhav", "सातवां भाव", "सातवें भाव", "marriage",
            "विवाह", "शादी", "delay marriage", "relationship", "relationships", "spouse",
            "partner", "partnership", "दांपत्य", "जीवनसाथी", "marriage delay", "delayed marriage"
        ])
        if has_7th_or_marriage:
            has_saturn = any(w in text_lower for w in ["saturn", "shani", "शनि"])
            p_desc = "Saturn (Shani) karmic delay aspect" if has_saturn else "partnership timing"
            return (
                f"The astrological dynamics of the 7th house governing marriage, partnership karma, and {p_desc}",
                "An authentic North Indian Vedic Kundli birth chart highlighting the 7th house (Yuvati Bhava) in warm amber-gold light, with partnership and marriage symbolism beside an ancient Sanskrit matrimonial scroll, in warm evening light",
                "Illuminating the karmic blueprint of union, marriage timing, and relational harmony",
                "An authentic Vedic Kundli birth chart with illuminated 7th House (Yuvati Bhava) and partnership harmony",
                "radiating focused amber-gold light specifically illuminating the 7th house grid beside an ancient rolled marriage parchment",
                "a dignified Vedic astrological study at warm twilight with antique brass instruments and soft candlelight"
            )

        # 3. 10th House & Career / Profession (Strict: career direction, workplace, leadership, or 10th house)
        has_10th_or_career = any(w in text_lower for w in [
            "10th house", "tenth house", "10th bhav", "दसवां भाव", "दसवें भाव", "career",
            "करियर", "profession", "business", "job", "नौकरी", "व्यापार", "workplace",
            "कार्यक्षेत्र", "head of department", "breakthrough", "leadership role", "career direction"
        ])
        if has_10th_or_career:
            return (
                "The astrological placement of the 10th house governing career direction, professional endurance, and leadership breakthroughs",
                "An authentic North Indian Vedic Kundli birth chart highlighting the 10th house (Karma Bhava) in radiant golden light, beside an executive wooden desk with fountain pen and journal in morning sunlight",
                "The karmic forge of the 10th house transforming disciplined struggle into unshakeable career leadership",
                "An authentic Vedic Kundli birth chart with illuminated 10th House (Karma Bhava) and executive leadership desk",
                "radiating focused amber-gold light on the 10th house grid alongside a clean executive leather journal and pen",
                "a refined executive astrological study with warm morning sunlight streaming across polished dark oak"
            )

        # 4. Emerald & Mercury (Strict: Panna / Emerald gemstone strengthening Mercury)
        if any(w in text_lower for w in ["emerald", "panna", "पन्ना"]):
            return (
                "Strengthening Mercury's communicative, analytical, and intellectual frequency through authentic natural Emerald",
                "A luxurious macro photograph of a certified natural vivid green Zambian Emerald gemstone glowing with crystalline facets on sacred parchment inscribed with the Sanskrit symbol for Mercury (Budha)",
                "The vibrant crystalline green fire of Emerald awakening Mercurial intellect",
                "A certified natural vivid green Zambian Emerald gemstone glowing with rich emerald luster",
                "reflecting crisp morning light with sharp crystalline facets beside an ink-drawn Sanskrit chart of Mercury",
                "a scholarly gemological sanctuary with rich dark wood textures and warm ambient study light"
            )

        # 5. Sun & Rahu in Kundali
        if (any(w in text_lower for w in ["rahu", "राहु"]) and any(w in text_lower for w in ["sun", "सूर्य", "surya"])) or "sun rahu" in text_lower or "सूर्य और राहु" in text_lower or "सूर्य-राहु" in text_lower:
            return (
                "The intense cosmic tension between solar confidence and Rahu's shadowy eclipse in the birth chart",
                "A glowing sacred Vedic Kundli birth chart inscribed with radiant golden lines on dark midnight parchment, with the Sun (Surya) blazing in golden fire and shadowy Rahu casting an intense cosmic eclipse shadow inside the chart house",
                "The solar life-force eclipsed by cosmic illusion inside the birth chart",
                "An illuminated Vedic Kundli chart featuring the glowing golden glyph of Sun and dark celestial shadow of Rahu",
                "pulsing with contrasting solar radiance and deep indigo eclipse aura across the chart grid",
                "a mystical Vedic observatory desk surrounded by brass astrological instruments and ancient charts"
            )

        # 6. 12th House Energy Drain
        if any(w in text_lower for w in ["12th house", "twelfth house", "बारहवें भाव", "बारहवां भाव", "12 भाव", "12वां"]):
            return (
                "The 12th house representing subconscious energy dissipation, sleep disruption, and spiritual release",
                "An authentic glowing Vedic Kundli birth chart highlighting the 12th house (Vyaya Bhava) in radiant golden light, with streams of ethereal golden energy gracefully flowing outward into the cosmos, illustrating energy release",
                "The 12th house portal where internal energy flows outward into the cosmos",
                "A sacred North Indian diamond Kundli birth chart with the 12th house distinctly illuminated in gold",
                "radiating ethereal streams of glowing golden light particles outward into dark celestial indigo space",
                "a tranquil astrological sanctum bathed in warm amber diya light and mystical starlight"
            )

        # 7. Mars (Mangal) Planet & Fiery Energy
        if any(w in text_lower for w in ["mars", "mangal", "मंगल", "मंगलेश"]):
            return (
                "The intense, decisive fire and warrior focus governed by planet Mars",
                "The majestic, glowing red planet Mars floating in deep cosmic space surrounded by fiery crimson and amber celestial nebulae, casting powerful heroic energy rays across the stars",
                "The unyielding crimson fire of Mars driving determination and focus",
                "The magnificent red planet Mars rendered in breathtaking 8k detail with glowing crimson aura",
                "radiating powerful dramatic beams of warm red and golden light through cosmic stellar dust",
                "deep cosmic space with dramatic swirling interstellar clouds and distant twinkling constellations"
            )

        # 8. Saturn (Shani Dev) Drishti & Karmic Aspects (Celestial context)
        if any(w in text_lower for w in ["shani ki drishti", "drishti", "दृष्टि", "saturn aspect", "saturn's aspect", "shani", "शनि", "saturn"]):
            return (
                "The formidable, all-seeing gaze and karmic discipline of Saturn across the chart",
                "The awe-inspiring planet Saturn with its majestic, crystalline ice rings glowing in deep cosmic space, casting three powerful focused volumetric beams of golden-indigo light representing planetary drishti across the cosmos",
                "Saturn's piercing gaze testing patience and establishing unshakeable karma",
                "The majestic planet Saturn with razor-sharp detailed rings and luminous golden-indigo aura",
                "projecting three distinct radiant cosmic rays of light piercing through deep space toward distant stars",
                "the deep majestic cosmos with rich indigo and violet nebulae and celestial starlight"
            )

        # 9. Explicit Gemstones (Strict: only when gemstone names or ratna are explicitly spoken; NOT for general 'remedy' or 'stone')
        gem_explicit_words = [
            "gemstone", "gemstones", "रत्न", "ratna", "neelam", "blue sapphire", "नीलम",
            "pukhraj", "yellow sapphire", "पुखराज", "panna", "emerald", "पन्ना", "manik",
            "ruby", "माणिक", "heera", "diamond", "हीरा", "moti", "pearl", "मोती",
            "moonga", "coral", "मूँगा", "मूंगा"
        ]
        if any(w in text_lower for w in gem_explicit_words):
            return (
                "The critical importance of exact chart alignment before wearing powerful gemstones",
                "A breathtaking, luxurious macro shot of authentic royal gemstones (deep blue Neelam sapphire, glowing red ruby, sparkling green emerald, and golden topaz) radiating pure internal light atop ancient Sanskrit palm leaves",
                "The pure crystalline energy of sacred gemstones awaiting rightful alignment",
                "A collection of flawless, faceted natural gemstones glowing with vivid jewel tones",
                "catching warm golden candlelight and casting prismatic color refractions across aged parchment",
                "an ancient Vedic sanctuary study with rich teakwood textures and antique brass instruments"
            )

        # 10. Call to Action / DM Consultation / Personal Chart Reading
        cta_words = ["dm", "डीएम", "comment", "कमेंट", "save", "सेव", "consultation", "परामर्श", "मार्गदर्शन", "booking", "बुक", "message", "मैसेज"]
        if any(w in text_lower for w in cta_words):
            # If gemstones are explicitly discussed in the CTA sentence, allow gemstone presentation
            if any(w in text_lower for w in gem_explicit_words):
                return (
                    "Inviting the viewer to discover their personal chart placements through private consultation",
                    "A captivating, warm cinematic close-up of open hands gently cradling authentic glowing gemstones and an ancient rolled Vedic birth chart, bathed in welcoming, radiant golden light that draws the viewer in",
                    "The inviting gateway to personal astrological guidance and energetic harmony",
                    "Dignified, welcoming hands presenting radiant natural gemstones and a rolled parchment Kundli",
                    "held gracefully in warm inviting golden light with soft inviting bokeh in the background",
                    "a serene, luxurious Vedic consultation study bathed in warm amber glow and quiet elegance"
                )
            # Default CTA: Professional astrologer consultation setting without forcing gemstones or temples
            return (
                "Inviting the viewer to discover their personal chart placements through private astrological consultation",
                "A warm, dignified cinematic close-up of a professional Vedic astrologer consultation desk with handwritten horoscope charts on aged parchment, antique brass reading lamp, and traditional reading instruments in inviting golden light",
                "The scholarly gateway to personal astrological clarity and charted guidance",
                "A professional Vedic astrologer consultation desk with authentic parchment Kundli chart and brass reading lamp",
                "illuminated by warm golden candlelight and soft atmospheric study bokeh, welcoming the viewer for personal guidance",
                "a serene, scholarly Vedic consultation study bathed in warm amber glow and dignified elegance"
            )

        return None

    @classmethod
    def _derive_visual_metaphor(
        cls,
        narration: str,
        text_lower: str,
        emotion: str,
        scene_idx: int,
        total_scenes: int,
        topic: str,
        tracker: ReelVisualDiversityTracker
    ) -> Tuple[str, str, str, str, str, str]:
        """
        Translates abstract concepts into concrete storytelling visual metaphors.
        Returns: (core_meaning, visual_concept, visual_metaphor, subject, action, environment)
        """
        script_text = (f"{narration}").lower()
        direct_match = cls._get_direct_literal_match(script_text, scene_idx, total_scenes)
        if direct_match:
            return direct_match

        # =========================================================================
        # 2. STORYTELLING & EMOTIONAL METAPHORS
        # =========================================================================
        # Specific Script A: Unreciprocated effort / Exhaustion
        if any(w in text_lower for w in ["never give anything back", "giving everything", "giving too much", "all you have", "pour"]):
            return (
                "Giving emotional energy endlessly to indifferent recipients who never reciprocate",
                "A worn, emotionally exhausted person offering luminous glowing water from cupped hands toward distant shadowy silhouettes who remain indifferent",
                "An overflowing vessel pouring sacred glowing life-water into an unresponsive void",
                "An emotionally exhausted protagonist with worn garments and gentle sorrowful gaze",
                "standing kneeling on cracked earth, open hands glowing softly as shimmering liquid dissipates fruitlessly",
                "a vast desolate cracked clay pan at cool dusky twilight, distant silhouettes fading into shadow"
            )

        # Specific Script: Waiting for someone who never chooses you
        if any(w in text_lower for w in ["never chooses you", "tired of waiting", "waiting for someone"]):
            return (
                "The emotional weariness of longing for a partner or person who does not value you",
                "A solitary reflective person sitting on a weathered bench at an empty railway station platform as an empty train departs into blue fog",
                "Waiting at a deserted terminal for an arrival that was never scheduled",
                "A solitary young adult with thoughtful sorrowful eyes and slumped reflective posture",
                "sitting in quiet stillness holding an unread handwritten letter resting gently on lap",
                "a deserted open-air brick railway platform bathed in cool blue dusk fog and soft glowing vintage lamp"
            )

        # Specific Script: Stop chasing people who left
        if any(w in text_lower for w in ["chasing people who have already left", "already left", "stop chasing"]):
            return (
                "Deciding to release past attachments and move forward rather than chasing memories",
                "A person walking forward along a sun-dappled cobblestone path while a translucent fading silhouette dissolves peacefully in the misty distance behind them",
                "Releasing a dissolving thread to walk freely into the morning light",
                "A grounded person walking decisively forward away from the camera, shoulders unburdened",
                "walking with calm pace along a pathway while looking ahead toward warm dawn horizon",
                "a quiet tree-lined coastal lane bathed in early morning golden sun, ocean mist in the background"
            )

        # Specific Script: Saturn testing patience / karmic struggle
        if any(w in text_lower for w in ["saturn is testing", "testing your patience", "patience"]):
            return (
                "Experiencing heavy life resistance as a karmic test that builds unyielding endurance",
                "A determined traveler ascending a steep, rugged stone mountain pass against howling wind and rain, holding a bronze lantern that cuts through the tempest",
                "The solitary mountain climber forged through storm and stone",
                "A resilient climber in weathered traveling cloak with determined set jaw and focused eyes",
                "climbing steadily up steep wet stone steps against swirling wind, gripping a sturdy walking staff",
                "a towering dark granite mountain pass with brooding rain clouds, faint celestial dusk hue"
            )

        # Specific Script: Life about to change / threshold of transformation
        if any(w in text_lower for w in ["about to change", "life is about to change", "major shift"]):
            return (
                "Standing on the exact dividing line before a monumental life transformation",
                "A person standing at a massive ancient arched stone portal, one hand resting on the weathered arch, gazing out from dark shadows into a sunlit blooming valley",
                "Standing on the threshold between the completed past and an illuminated new world",
                "A contemplative person silhouetted in an open stone doorway looking toward the light",
                "pausing in wonder at the doorway, hand poised on the stone frame as morning breeze catches hair",
                "an ancient stone temple terrace overlooking an expansive verdant valley glowing in sunrise gold"
            )

        # Specific Script: Financial breakthrough after struggle
        if any(w in text_lower for w in ["financial breakthrough", "after a period of struggle", "breakthrough"]):
            return (
                "Emerging from prolonged financial scarcity and pressure into expansive abundance",
                "A hardworking person stepping out from a narrow, shadowed alleyway onto an expansive open terrace overlooking a prosperous city bathed in golden morning light",
                "Emerging from the cramped shadowed tunnel into wide-open abundance",
                "A focused professional holding a leather-bound notebook catching the first rays of sunlight",
                "stepping out onto the open stone parapet with an expression of quiet triumph and relief",
                "a high stone terrace overlooking a sprawling, luminous historic city waking up in amber sunrise"
            )

        # Specific Script: Lord Shiva & sacred silence
        if any(w in text_lower for w in ["lord shiva", "shiva teaches", "silence is powerful", "shiva"]):
            return (
                "The supreme, unshakeable power found in deep inner stillness and cosmic meditation",
                "A magnificent carved stone effigy of Lord Shiva in serene deep meditation on a high Himalayan peak at twilight, with a steady brass diya burning in the calm breeze",
                "The absolute stillness and unshakeable power of cosmic consciousness",
                "An ancient sculpted granite bust of Lord Shiva with tranquil closed eyes, crescent moon in matted locks, sacred ashes",
                "resting in timeless meditative samadhi as faint mountain mist curls around the pedestal",
                "a serene high-altitude Himalayan mountain ridge under a deep indigo sky with a single steady oil lamp"
            )

        # Specific Gemstone: Pyrite & 5th house karmic caution
        if any(w in text_lower for w in ["pyrite", "पायराइट"]):
            return (
                "Cautioning against blindly wearing Pyrite without analyzing 5th house solar energy",
                "An astrologer's hands examining a raw glittering golden Pyrite mineral cluster on a dark polished wooden consultation desk beside an authentic parchment birth chart",
                "Scrutinizing the solar mineral against the cosmic blueprint of destiny",
                "An authentic golden crystalline Pyrite cluster with natural cubic metallic facets",
                "resting on an antique dark teakwood desk beside an open ink-drawn Sanskrit horoscope parchment",
                "a scholarly dimly-lit astrological study with warm candlelight, brass instruments, and antique manuscripts"
            )

        # Specific Sacred Item: Rudraksha & sacred beads
        if any(w in text_lower for w in ["rudraksha", "रुद्राक्ष", "mukhi", "पंचमुखी", "पांच मुखी", "5 mukhi"]):
            return (
                "The sacred energetic properties and organic structure of authentic Rudraksha beads",
                "An extreme macro close-up of an authentic natural Nepali 5-mukhi Rudraksha bead resting on wet dark slate stone, delicate water droplets highlighting organic deep mukhi grooves under warm golden temple light",
                "The natural tactile sacred geometry of the divine seed",
                "An authentic natural Nepali 5-mukhi Rudraksha bead with deep organic mukhi contours",
                "resting serenely on textured dark slate stone with delicate droplets of sacred water reflecting warm temple candlelight",
                "a quiet temple altar sanctuary with soft burning brass diyas and warm golden shadows"
            )

        # Specific Energetic: Bio-Energy Field & Aura Protection
        if any(w in text_lower for w in ["bio-energy", "bio energy", "बायो-एनर्जी", "aura", "ऊर्जा क्षेत्र", "energy shield", "shield", "नकारात्मक ऊर्जा"]):
            return (
                "Harmonizing and shielding the human bio-energy field from external disharmony",
                "A serene individual centered in quiet mindfulness, surrounded by a subtle, luminous golden-cyan harmonic energy boundary that deflects faint dark chaotic dust",
                "The impenetrable sanctuary of a balanced personal aura",
                "A peaceful meditating individual seated in poised stillness",
                "breathing steadily as a soft, translucent harmonic field of warm golden light pulses gently around their physical form",
                "a tranquil minimalist meditation space with subtle dawn light filtering through sheer curtains"
            )

        # Specific Sleep: Nocturnal restlessness & 3 AM awakening
        if any(w in text_lower for w in ["sleep", "नींद", "3 am", "3 बजे", "अनिद्रा", "insomnia", "रात को"]):
            return (
                "Breaking the cycle of 3 AM nocturnal anxiety and restoring deep restorative sleep",
                "A person sitting up on the edge of a bed in a dark moody bedroom, looking thoughtfully toward a warm amber bedside lamp, tension visibly melting away into calm stillness",
                "Finding calm stillness in the deep quiet hours of the night",
                "A thoughtful person sitting on the edge of a bed in a peaceful dimly lit room",
                "pausing with relaxed shoulders and serene expression, gazing softly at warm bedside light",
                "a quiet contemporary bedroom bathed in cool midnight shadows and a gentle warm bedside lamp glow"
            )

        # Specific Consultation: Client seeking guidance
        if any(w in text_lower for w in ["client", "क्लाइंट", "सत्र", "consultation", "परामर्श", "केस स्टडी", "session"]):
            return (
                "A meaningful one-on-one consultation examining life challenges and energetic remedies",
                "An empathetic guide and an expressive client seated across an antique dark wooden consultation table in a warm study, engaged in thoughtful, supportive dialogue",
                "The compassionate guidance illuminating personal confusion",
                "Two individuals seated across an antique consultation desk in meaningful conversation",
                "one person gesturing with supportive wisdom while the other listens with deep relieved realization",
                "a scholarly study lined with warm wooden shelves, soft amber reading lamp, and tranquil atmosphere"
            )

        # Specific Astrological: Dynamic Kundli House analysis & chart mapping (Strict: only when explicitly discussing horoscope charts)
        from app.video.kundli_chart_generator import KundliChartGenerator, HOUSE_METADATA
        house_num, planet_name = KundliChartGenerator.extract_house_and_planet(text_lower)
        is_explicit_chart = any(k in text_lower for k in ["kundli", "कुंडली", "birth chart", "natal chart", "horoscope chart", "जन्मपत्रिका", "जन्म कुंडली", "house", "भाव", "लग्न", "chart"])
        if is_explicit_chart and house_num and house_num in HOUSE_METADATA:
            meta = HOUSE_METADATA[house_num]
            planet_clause = f" with {planet_name} placement" if planet_name else ""
            return (
                f"Analyzing the astrological influence of the {meta['name_en']}{planet_clause} governing {meta['significance']}",
                f"An authentic ancient North Indian Vedic Kundli birth chart on dark celestial parchment where the {meta['name_en']} ({meta['name_hi']}) is prominently highlighted and glowing in brilliant golden-amber light",
                f"Illuminating the karmic blueprint of {meta['sanskrit']} ({meta['significance']})",
                f"An authentic weathered parchment Vedic Kundli birth chart with glowing {meta['name_en']}{planet_clause}",
                f"displaying intricate Sanskrit planetary glyphs and fine geometric house divisions with radiant golden aura on {meta['name_en']}",
                "a quiet astrological scholar sanctuary bathed in warm candlelight with brass astrolabe and palm-leaf manuscripts"
            )
        elif is_explicit_chart:
            return (
                "Examining the overall geometry and planetary alignments in an authentic Vedic Kundli birth chart",
                "A complete North Indian diamond Vedic Kundli birth chart drawn in gold leaf on dark celestial parchment, glowing with sacred geometry",
                "Tracing the cosmic web of destiny across the twelve astrological houses",
                "An authentic complete North Indian diamond-grid Kundli birth chart",
                "delicately illuminated by warm oil lamps revealing all twelve Sanskrit houses and planetary degrees",
                "an ancient stone observatory library at dusk with brass armillary sphere and astrological texts"
            )

        # Specific Astrological: Shani / Saturn planetary influence
        if any(w in text_lower for w in ["saturn", "shani", "शनि"]):
            return (
                "The stern, disciplining, and transformative karmic influence of Saturn",
                "A solitary scholar contemplating an antique bronze armillary celestial sphere by candlelight as deep indigo night settles outside an arched stone window",
                "The tireless watcher measuring the unyielding laws of time and cosmic retribution",
                "A focused scholar seated beside an intricate antique brass armillary sphere",
                "observing the mechanical alignments of cosmic rings with deep thoughtful reverence",
                "an ancient stone observatory library at midnight with starlight filtering through arched windows"
            )

        # Content-driven opening or closing realization (NEVER forces gemstones or temples by position)
        if any(w in text_lower for w in ["consultation", "परामर्श", "मार्गदर्शन", "dm", "comment", "save"]):
            return (
                "Personal astrological consultation and charted guidance",
                "A warm, dignified cinematic close-up of a professional Vedic astrologer consultation desk with handwritten horoscope charts on aged parchment, antique brass reading lamp, and traditional reading instruments in inviting golden light",
                "The scholarly gateway to personal astrological clarity and charted guidance",
                "A professional Vedic astrologer consultation desk with authentic parchment Kundli chart and brass reading lamp",
                "illuminated by warm golden candlelight and soft atmospheric study bokeh, welcoming the viewer for personal guidance",
                "a serene, scholarly Vedic consultation study bathed in warm amber glow and dignified elegance"
            )

        # Universal storytelling fallback based on emotion
        return (
            f"Communicating the emotional essence of the scene: {emotion}",
            f"A deeply evocative cinematic frame capturing a solitary protagonist expressing {emotion} in an atmospheric setting",
            f"The human journey through {emotion} toward clarity",
            f"A solitary expressive protagonist embodying {emotion}",
            "interacting meaningfully with their surroundings with authentic emotional expression",
            "a cinematic 35mm atmosphere with deep volumetric lighting and narrative depth"
        )

    @classmethod
    def _determine_visual_style(cls, text_lower: str, emotion: str, topic: str) -> str:
        """Selects the visual style that matches script tone."""
        if any(w in text_lower for w in ["shiva", "mahadev", "god", "deity", "divine"]):
            return "Mythological cinematic realism"
        elif any(w in text_lower for w in ["symbol", "metaphor", "dream", "surreal"]):
            return "Surreal symbolic art"
        elif emotion in ["Fear", "Betrayal", "Frustration"]:
            return "Dark cinematic realism"
        elif emotion in ["Peace", "Devotion", "Awe"]:
            return "Ethereal spiritual realism"
        elif any(w in text_lower for w in ["science", "nervous system", "bio-electric"]):
            return "Documentary realism"
        else:
            return "Cinematic photorealism"

    @classmethod
    def _build_detailed_prompt(
        cls,
        subject: str,
        action: str,
        posture: str,
        environment: str,
        emotion: str,
        lighting: str,
        composition: str,
        color_palette: str,
        visual_style: str,
        metaphor: str
    ) -> str:
        """
        Builds high-impact, punchy vertical 9:16 prompt adhering to literal script context.
        Guarantees objects, charts, and planets NEVER receive human postures or facial tokens.
        """
        full_text = f"{subject} {action} {environment}".lower()
        is_object_or_celestial = any(w in full_text for w in [
            "chart", "kundli", "planet", "saturn", "mars", "sun", "rahu", "ketu", "jupiter",
            "gemstone", "crystal", "bracelet", "bead", "yantra", "parchment", "macro", "tiger",
            "stone", "sapphire", "ruby", "emerald", "altar", "lamp", "sanctum", "hands"
        ])

        if is_object_or_celestial:
            prompt = (
                f"vertical 9:16 cinematic masterpiece, 8k, hyper-detailed, award-winning photography. "
                f"{subject}, {action}. "
                f"Atmospheric environment: {environment}. "
                f"Mood & lighting: luxurious warm volumetric amber lighting, radiant golden glow, sharp focus, 35mm lens. "
                f"Color grading: {color_palette}. "
                f"Stunning tactile textures, ultra-photorealistic, high contrast. "
                f"no human faces, no anime characters, no text overlays, no watermarks, no logos, no cgi cartoons, no flat solid colors"
            )
        else:
            clean_posture = re.sub(r"\b(?:fidgeting|clenched|tightened|defensive|slumped|vigilant)\b", "composed", posture or "", flags=re.I).strip()
            posture_str = f"{clean_posture}. " if clean_posture else ""
            prompt = (
                f"vertical 9:16 cinematic masterpiece, 8k, hyper-detailed, award-winning photography. "
                f"{subject}, {action}. {posture_str}"
                f"Atmospheric environment: {environment}. "
                f"Mood & lighting: {lighting}. "
                f"Color grading: {color_palette}. "
                f"Shot on 35mm masterwork lens, rich volumetric lighting, sharp focus, stunning tactile textures. "
                f"no text overlays, no watermarks, no logos, no cgi cartoons, no flat solid colors"
            )
        return prompt

    @classmethod
    def record_traceability(
        cls,
        reel_id: str,
        scene_id: int | str,
        narration: str,
        visual_concept: str,
        emotion: str,
        image_prompt: str,
        generation_model: str,
        image_hash: str,
        quality_review: Dict[str, Any],
        approved: bool = True
    ) -> Dict[str, Any]:
        """
        Records full script-to-image traceability metadata into storage/scene_visual_traceability.json.
        """
        parsed_scene_id = int(scene_id) if str(scene_id).isdigit() else str(scene_id)
        record = {
            "reel_id": str(reel_id),
            "scene_id": parsed_scene_id,
            "narration": str(narration),
            "visual_concept": str(visual_concept),
            "emotion": str(emotion),
            "image_prompt": str(image_prompt),
            "generation_model": str(generation_model),
            "image_hash": str(image_hash),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "quality_review": quality_review,
            "approved": approved
        }

        try:
            records: List[Dict[str, Any]] = []
            if TRACEABILITY_LOG_FILE.exists() and TRACEABILITY_LOG_FILE.stat().st_size > 0:
                try:
                    with open(TRACEABILITY_LOG_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            records = data
                        elif isinstance(data, dict):
                            records = data.get("traceability_records", [])
                except Exception:
                    records = []

            records.append(record)
            # Retain last 500 scene traceability records to bound file size
            if len(records) > 500:
                records = records[-500:]

            temp_file = TRACEABILITY_LOG_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({"traceability_records": records}, f, indent=2, ensure_ascii=False)
            temp_file.replace(TRACEABILITY_LOG_FILE)
            logger.info(f"[Traceability] Recorded metadata for Scene {scene_id} in Reel {reel_id}.")
        except Exception as exc:
            logger.warning(f"[Traceability] Failed to write scene traceability record: {exc}")

        return record
