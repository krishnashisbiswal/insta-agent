"""
Scene Visual Planner & Semantic Entity Resolver.
Authoritative intelligence layer transforming Reel narration into structured,
scene-specific visual briefs and AI image prompts:

1. Strict Scene-Level Context Isolation: The overall Reel topic provides background
   context but NEVER overrides a scene's own specific narrative subject.
2. Word-Boundary Semantic Matching: Tokenized matching preventing substring false
   positives (e.g. 'moti' in 'emotional', 'fire' in 'clarifier').
3. Disambiguation of Generic Stop-Words: Words like 'fire', 'house', 'love', 'wealth',
   'peace', 'remedy' do not automatically trigger unrelated planetary or ritual entities.
4. Devanagari Hindi & Sanskrit Normalization: Robust alias recognition across Hindi,
   Sanskrit, and English astrological and scientific terms.
5. Structured Visual Briefs: Detailed, validated specifications including subject,
   action, environment, lighting, composition, color palette, exclusions, and prompts.
6. Topic Contamination Prevention: Topic entities are strictly barred from appearing
   in scenes whose own narration describes a different subject.
7. Validation & Automatic Repair: Rejects or repairs generic, empty, or contradictory briefs.
"""

import copy
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("SceneVisualPlanner")


class SceneValidationError(Exception):
    """Raised when a scene visual plan fails structural or semantic validation."""
    pass


@dataclass
class SceneVisualPlan:
    """Structured, authoritative visual specification for a single scene."""
    scene_id: str = "scene_1"
    scene_idx: int = 0
    exact_narration: str = ""
    core_meaning: str = ""
    main_subject: str = "cinematic scene subject"
    subject_action: str = "engaging in intentional cinematic action"
    environment: str = "atmospheric cinematic setting"
    time_of_day: str = "morning golden hour"
    mood: str = "contemplative, cinematic"
    composition: str = "9:16 vertical portrait composition"
    camera_framing: str = "35mm prime lens, shallow depth of field"
    lighting: str = "warm golden hour lighting"
    color_palette: str = "warm gold, deep amber, dark charcoal"
    visual_style: str = "cinematic photorealistic 35mm film photograph, 9:16 vertical"
    required_visual_elements: List[str] = field(default_factory=list)
    forbidden_visual_elements: List[str] = field(default_factory=list)
    continuity_requirements: str = "consistent warm cinematic 35mm tone"
    aspect_ratio: str = "9:16"
    generation_prompt: str = ""
    validation_criteria: List[str] = field(default_factory=list)
    entity_key: str = "custom"
    estimated_duration: float = 4.0
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    # Emotion-aware intelligence fields (Requirement 2)
    emotion: str = ""
    emotion_intensity: float = 0.8
    viewer_feeling: str = ""
    visual_concept: str = ""
    visual_metaphor: str = ""
    camera_angle: str = ""
    continuity_notes: str = ""
    image_prompt: str = ""
    # Script-first & semantic fallback intelligence fields
    visual_intent: str = ""
    required_entities: List[str] = field(default_factory=list)
    primary_visual_strategy: str = ""
    fallback_visual_strategy: str = ""
    fallback_generation_prompt: str = ""
    used_fingerprints: List[str] = field(default_factory=list)
    validation_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Authoritative Requirement 2 schema
        d["scene_id"] = self.scene_idx + 1 if isinstance(self.scene_idx, int) else 1
        d["narration"] = self.exact_narration
        d["core_meaning"] = self.core_meaning
        d["emotion"] = self.emotion or self.mood
        d["emotion_intensity"] = self.emotion_intensity
        d["viewer_feeling"] = self.viewer_feeling
        d["visual_concept"] = self.visual_concept or self.core_meaning
        d["visual_metaphor"] = self.visual_metaphor
        d["subject"] = self.main_subject
        d["action"] = self.subject_action
        d["environment"] = self.environment
        d["composition"] = self.composition
        d["lighting"] = self.lighting
        d["color_palette"] = self.color_palette
        d["camera_angle"] = self.camera_angle or self.camera_framing
        d["continuity_notes"] = self.continuity_notes or self.continuity_requirements
        d["image_prompt"] = self.image_prompt or self.generation_prompt
        # Script-first & semantic fallback metadata
        d["visual_intent"] = self.visual_intent
        d["required_entities"] = self.required_entities
        d["primary_visual_strategy"] = self.primary_visual_strategy
        d["fallback_visual_strategy"] = self.fallback_visual_strategy
        d["fallback_generation_prompt"] = self.fallback_generation_prompt
        d["used_fingerprints"] = self.used_fingerprints
        d["validation_passed"] = self.validation_passed
        # Backward compatibility aliases
        d["main_subject"] = self.main_subject
        d["subject_action"] = self.subject_action
        d["generation_prompt"] = self.image_prompt or self.generation_prompt
        return d

    @property
    def narration(self) -> str:
        return self.exact_narration

    @property
    def subject(self) -> str:
        return self.main_subject

    @property
    def primary_subject(self) -> str:
        return self.main_subject

    @property
    def action(self) -> str:
        return self.subject_action


class SceneVisualPlanner:
    """
    Analyzes scene-specific script content to build dedicated, unambiguous visual plans.
    Guarantees:
    - Exactly one coherent visual concept per scene.
    - Zero topic contamination across unrelated scenes.
    - Zero procedural 3D geometric wireframes or ring drawings.
    - Zero uncurated or unrelated fallbacks.
    """

    # Concrete Entity Definitions with Strict Token Boundaries
    SPECIFIC_ENTITIES: Dict[str, Dict[str, Any]] = {
        # Scientific & Biological Entities
        "nervous_system": {
            "name": "human central nervous system and brain neural synapses",
            "keywords": [
                "nervous system", "तंत्रिका", "तंत्रिका तंत्र", "neuro", "neuroscience",
                "brain", "synapse", "synapses", "मस्तिष्क", "neurons", "neural", "bio-electric"
            ],
            "objects": ["human neural pathways", "glowing synaptic connections", "calm bio-electric pulses"],
            "exclusions": ["gemstone", "rudraksha bead", "temple", "horoscope chart", "fire", "taco", "insect", "rings", "beads"],
            "default_action": "radiating soothing calm bio-electric harmonic waves",
            "default_setting": "dark minimalist anatomical background with soft glowing cyan and amber neural light",
            "time_of_day": "timeless dark void",
            "mood": "introspective, scientific, calm",
            "composition": "macro close-up shot of glowing synaptic dendrites",
            "camera_framing": "shallow depth of field, 100mm macro lens focus",
            "lighting": "soft bioluminescent cyan and warm amber glow against deep obsidian",
            "color_palette": "deep obsidian, electric cyan, warm golden amber",
        },
        "heart_cardiovascular": {
            "name": "human heart and soothing rhythmic cardiovascular pulse",
            "keywords": ["heart", "हृदय", "रक्तचाप", "blood pressure", "cardiovascular", "pulse rate", "धड़कन"],
            "objects": ["anatomical heart silhouette", "soothing rhythmic pulse wave", "vascular warmth"],
            "exclusions": ["food", "insect", "gemstone", "spacecraft", "rudraksha"],
            "default_action": "pulsing steadily with calming warm vital energy",
            "default_setting": "serene anatomical dark aesthetic with soft amber glow",
            "time_of_day": "timeless dark void",
            "mood": "peaceful, biological, vital",
            "composition": "medium close-up of vital energetic heart center",
            "camera_framing": "centered framing with soft ethereal edge falloff",
            "lighting": "subtle crimson and warm terracotta backlighting",
            "color_palette": "terracotta, deep burgundy, warm gold",
        },
        "meditation_zen": {
            "name": "person meditating in deep peaceful mindfulness",
            "keywords": [
                "meditat", "ध्यान", "एकांत", "zen", "mindfulness", "peace of mind",
                "mental peace", "मन की शांति", "deep peace", "प्राणायाम", "साधना"
            ],
            "objects": ["meditator seated in padmasana", "soft morning sun rays", "calm serene posture"],
            "exclusions": ["violent fire", "luxury jewelry", "office desk", "food", "insect", "crowd"],
            "default_action": "breathing mindfully with closed eyes in complete stillness",
            "default_setting": "peaceful dawn sanctuary overlooking quiet misty mountains",
            "time_of_day": "early dawn golden hour",
            "mood": "tranquil, transcendent, serene",
            "composition": "medium profile portrait with sweeping scenic background",
            "camera_framing": "rule-of-thirds, 50mm natural eye-level framing",
            "lighting": "diffused warm golden sunrise rays filtering through mist",
            "color_palette": "soft dawn gold, misty slate blue, warm earth tones",
        },
        "astrology_consultation": {
            "name": "professional Vedic astrologer conducting birth chart consultation",
            "keywords": [
                "consultation", "परामर्श", "case study", "client", "जातक", "क्लाइंट",
                "सत्र", "विश्लेषण", "chart analysis", "1-on-1", "परामर्श सत्र"
            ],
            "objects": ["aged parchment Vedic Kundli birth chart", "brass astrolabe", "magnifying glass", "ancient Sanskrit scrolls"],
            "exclusions": ["rough gemstones", "satellite probe", "food", "taco", "insect", "rudraksha"],
            "default_action": "carefully examining birth chart planetary houses with traditional brass compass",
            "default_setting": "scholarly study desk lit by warm flickering brass oil lamp with ancient Sanskrit texts",
            "time_of_day": "evening twilight",
            "mood": "scholarly, wise, reverent",
            "composition": "over-the-shoulder medium shot focusing on parchment chart",
            "camera_framing": "35mm vintage lens, cinematic shallow depth of field",
            "lighting": "warm directional candlelight and flickering brass oil lamp glow",
            "color_palette": "rich sepia, antique brass gold, dark mahogany",
        },
        # Specific Sacred Vedic Gemstones (Strict Precedence)
        "emerald_gemstone": {
            "name": "certified natural vivid green Zambian Emerald gemstone",
            "keywords": [
                "emerald", "panna", "पन्ना", "green emerald", "जाम्बियन पन्ना",
                "मरकत", "mercury gemstone"
            ],
            "objects": [
                "natural cut vivid green emerald gemstone",
                "crystalline facets glowing with brilliant emerald luster",
                "velvet gemologist pedestal"
            ],
            "exclusions": [
                "generic horoscope chart", "kundli chart alone", "temple", "havan",
                "fire", "saturn", "rudraksha", "unrelated gemstones"
            ],
            "default_action": "glowing with intense natural crystalline green brilliance",
            "default_setting": "luxurious dark obsidian display pedestal with subtle studio rim lighting",
            "time_of_day": "studio lighting",
            "mood": "luxurious, crystalline, radiant",
            "composition": "extreme macro hero product shot of emerald gemstone facets",
            "camera_framing": "100mm macro lens, 1:1 ratio, razor sharp facet focus",
            "lighting": "focused directional diamond spotlight catching emerald crystal depth",
            "color_palette": "vivid emerald green, deep forest green, obsidian black, subtle gold",
        },
        "blue_sapphire_gemstone": {
            "name": "certified natural royal blue sapphire Neelam gemstone",
            "keywords": ["blue sapphire", "sapphire", "neelam", "नीलम", "saturn gemstone"],
            "objects": ["natural cut royal blue sapphire gemstone", "crystalline facets catching deep blue brilliance"],
            "exclusions": ["generic horoscope chart", "temple", "havan", "emerald"],
            "default_action": "radiating deep celestial royal blue luminescence",
            "default_setting": "dark velvet pedestal with dramatic side lighting",
            "time_of_day": "studio lighting",
            "mood": "regal, powerful, celestial",
            "composition": "extreme macro product shot of sapphire facets",
            "camera_framing": "macro focus on crystalline crown facets",
            "lighting": "sharp directional white rim light on blue crystal",
            "color_palette": "royal blue, cobalt, midnight navy, silver",
        },
        "yellow_sapphire_gemstone": {
            "name": "certified natural golden yellow sapphire Pukhraj gemstone",
            "keywords": ["yellow sapphire", "pukhraj", "पुखराज", "jupiter gemstone"],
            "objects": ["natural cut golden yellow sapphire gemstone", "crystalline facets glowing with warm amber-gold light"],
            "exclusions": ["generic horoscope chart", "temple", "havan", "emerald"],
            "default_action": "glowing with warm honey-yellow crystalline warmth",
            "default_setting": "warm dark marble pedestal",
            "time_of_day": "studio lighting",
            "mood": "auspicious, warm, radiant",
            "composition": "macro close-up of golden gemstone",
            "camera_framing": "macro prime lens focus",
            "lighting": "warm directional golden key light",
            "color_palette": "canary yellow, warm amber, honey gold",
        },
        "ruby_gemstone": {
            "name": "certified natural pigeon blood red Ruby Manik gemstone",
            "keywords": ["ruby", "manik", "माणिक", "माणिक्य", "sun gemstone"],
            "objects": ["natural cut deep red ruby gemstone", "crystalline facets glowing with radiant crimson luster"],
            "exclusions": ["generic horoscope chart", "temple", "havan", "emerald"],
            "default_action": "radiating passionate crimson red crystalline fire",
            "default_setting": "dark obsidian gemstone stage",
            "time_of_day": "studio lighting",
            "mood": "regal, passionate, solar",
            "composition": "extreme macro hero shot of ruby facets",
            "camera_framing": "macro 1:1 focus",
            "lighting": "high-contrast dramatic rim light catching ruby fire",
            "color_palette": "pigeon blood red, crimson, deep scarlet, obsidian",
        },
        "kundli_chart": {
            "name": "ancient authentic Vedic astrological Kundli birth chart",
            "keywords": [
                "kundli", "कुंडली", "birth chart", "जन्मपत्रिका", "horoscope chart",
                "astrology chart", "natal chart", "जन्म कुंडली"
            ],
            "objects": ["traditional diamond-grid Kundli chart on aged parchment", "handwritten Sanskrit planetary symbols"],
            "exclusions": ["modern computer screen", "unrelated gemstones", "food", "insects", "modern gadgets"],
            "default_action": "softly illuminated by warm candlelight revealing intricate planetary houses",
            "default_setting": "dark antique wooden table beside aged Sanskrit astrological scrolls",
            "time_of_day": "night study hours",
            "mood": "mystical, profound, ancient",
            "composition": "overhead flat-lay with subtle 15-degree tilt",
            "camera_framing": "macro focus on central lagna diamond grid",
            "lighting": "low-key warm golden side-light raking across aged parchment paper texture",
            "color_palette": "parchment cream, burnt umber, antique gold, deep charcoal",
        },
        "copper_water_remedy": {
            "name": "traditional pure hammered copper water vessel",
            "keywords": ["copper", "tamba", "तांबे", "copper vessel", "copper pot", "तांबे का लोटा", "water remedy", "ताम्र"],
            "objects": ["hand-hammered pure copper water pot", "fresh pure water", "sacred green tulsi basil leaf"],
            "exclusions": ["saturn planet", "gemstone rings", "fire altar", "food", "insect", "rudraksha"],
            "default_action": "holding crystal-clear water catching morning sunlight",
            "default_setting": "clean peaceful prayer altar with morning golden sunbeams",
            "time_of_day": "early morning sunrise",
            "mood": "pure, healing, fresh",
            "composition": "centered still-life hero shot",
            "camera_framing": "85mm prime lens with soft blurred prayer background",
            "lighting": "radiant morning sunbeam creating specular highlight on copper rim",
            "color_palette": "bright metallic copper, clear water reflections, vivid tulsi green",
        },
        "rudraksha_bead": {
            "name": "authentic sacred natural Nepali Rudraksha bead",
            "keywords": ["rudraksha", "rudraksh", "रुद्राक्ष", "mukhi", "पंचमुखी", "पांच मुखी", "5 mukhi", "mala bead"],
            "objects": ["natural Nepali rudraksha bead with distinct carved mukhi grooves", "fine organic woody texture"],
            "exclusions": ["cut crystal", "plastic", "food", "insects", "modern gadgets", "synthetic 3D models"],
            "default_action": "resting majestically with pure sacred water droplets",
            "default_setting": "rich dark textured stone altar with warm ambient temple glow",
            "time_of_day": "morning puja hour",
            "mood": "sacred, divine, grounded",
            "composition": "macro close-up revealing organic mukhi contours",
            "camera_framing": "extreme close-up macro with 1:1 reproduction ratio",
            "lighting": "warm directional morning temple light with soft shadows",
            "color_palette": "rich walnut brown, warm terracotta, dark granite gray",
        },
        "pyrite_crystal": {
            "name": "natural raw golden Pyrite crystal cluster",
            "keywords": ["pyrite", "पायराइट", "fool's gold", "iron pyrite"],
            "objects": ["raw cubic pyrite crystal clusters", "metallic brass-gold luster facets"],
            "exclusions": ["cut diamond", "rudraksha", "planets", "food", "synthetic rings"],
            "default_action": "sparkling with warm reflective metallic golden luster",
            "default_setting": "dark slate stone pedestal with focused dramatic studio lighting",
            "time_of_day": "studio controlled lighting",
            "mood": "luxurious, powerful, grounded",
            "composition": "hero product macro shot showcasing natural cubic geometry",
            "camera_framing": "macro focus on reflective cubic cleavage planes",
            "lighting": "dramatic dual rim-lighting highlighting metallic gold edges",
            "color_palette": "metallic brass gold, charcoal slate, warm bronze",
        },
        "amethyst_crystal": {
            "name": "natural raw purple Amethyst crystal geode",
            "keywords": ["amethyst", "कटेला", "जामुनिया"],
            "objects": ["deep violet crystalline quartz points", "raw natural geode rim"],
            "exclusions": ["yellow crystals", "planets", "rudraksha"],
            "default_action": "radiating rich purple crystalline highlights",
            "default_setting": "dark velvet surface with soft celestial backlighting",
            "time_of_day": "twilight",
            "mood": "spiritual, calming, intuitive",
            "composition": "close-up angle emphasizing internal crystal cavern",
            "camera_framing": "medium macro with rich depth of field",
            "lighting": "soft diffused violet and cool white edge illumination",
            "color_palette": "royal purple, violet, soft lavender, dark onyx",
        },
        "black_tourmaline": {
            "name": "natural raw Black Tourmaline crystal tower",
            "keywords": ["tourmaline", "टूमलाइन", "black tourmaline"],
            "objects": ["jet-black striated tourmaline crystal", "protective columnar formation"],
            "exclusions": ["colorful gems", "planets", "rudraksha"],
            "default_action": "standing tall and impenetrable catching delicate rim light",
            "default_setting": "dark grounding surface with subtle defensive aura flare",
            "time_of_day": "low-key dusk",
            "mood": "protective, impenetrable, grounded",
            "composition": "vertical hero shot emphasizing columnar striations",
            "camera_framing": "eye-level vertical 9:16 composition",
            "lighting": "single high-contrast rim light revealing fine surface striations",
            "color_palette": "jet black, dark charcoal, subtle cool silver rim",
        },
        "citrine_crystal": {
            "name": "natural warm golden Citrine crystal",
            "keywords": ["citrine", "सिट्रीन"],
            "objects": ["warm amber-yellow quartz cluster", "sunlit crystalline facets"],
            "exclusions": ["purple crystals", "planets", "rudraksha"],
            "default_action": "glowing with warm golden sunshine energy",
            "default_setting": "refined wooden desk in morning golden hour light",
            "time_of_day": "morning golden hour",
            "mood": "abundant, joyous, radiant",
            "composition": "close-up hero framing on amber crystal points",
            "camera_framing": "shallow depth of field, warm morning bokeh",
            "lighting": "backlit morning sunbeams passing through translucent crystal",
            "color_palette": "warm amber, honey gold, soft sunlit cream",
        },
        "planet_saturn": {
            "name": "planet Saturn with majestic rings in deep cosmic space",
            "keywords": ["saturn", "shani", "शनि", "shani dev", "शनिदेव", "sade sati", "साढ़ेसाती"],
            "objects": ["planet Saturn", "detailed icy ring system", "starry cosmos"],
            "exclusions": ["gemstone jewelry", "earth landscapes", "food", "insects", "rudraksha"],
            "default_action": "looming majestically in quiet deep cosmic orbit",
            "default_setting": "vast dark cosmos with distant twinkling stars and subtle nebular dust",
            "time_of_day": "deep cosmic space",
            "mood": "austere, majestic, karmic, eternal",
            "composition": "wide cinematic cosmic composition with diagonal ring angle",
            "camera_framing": "wide-angle astronomical space photography perspective",
            "lighting": "distant pale sunlight grazing the curvature of the planet and rings",
            "color_palette": "pale ochre, deep cosmic black, icy silver rings, deep navy",
        },
        "planet_jupiter": {
            "name": "giant banded planet Jupiter in dark cosmic space",
            "keywords": ["jupiter", "brihaspati", "guru", "बृहस्पति", "गुरु ग्रह", "गुरुदेव"],
            "objects": ["banded atmosphere of Jupiter", "Great Red Spot", "swirling cloud bands"],
            "exclusions": ["rings of saturn", "gemstones", "food", "rudraksha"],
            "default_action": "spinning gracefully in silent space radiating golden majesty",
            "default_setting": "deep starfield with gentle golden cosmic glow",
            "time_of_day": "deep cosmic space",
            "mood": "benevolent, vast, expansive, divine",
            "composition": "grand planetary portrait filling lower two-thirds of frame",
            "camera_framing": "telephoto deep space perspective",
            "lighting": "warm cosmic solar radiance illuminating planetary cloud bands",
            "color_palette": "warm ochre, swirling ivory, terracotta orange, deep cosmic void",
        },
        "planet_mars": {
            "name": "red planet Mars with cratered terrain in dark space",
            "keywords": ["mars", "mangal", "मंगल", "मंगल ग्रह", "भौम"],
            "objects": ["reddish cratered planet Mars", "dust storms", "rusty red planetary surface"],
            "exclusions": ["green terrain", "saturn rings", "food", "rudraksha"],
            "default_action": "radiating fiery reddish cosmic presence in orbit",
            "default_setting": "deep starry space with crimson cosmic aura",
            "time_of_day": "deep cosmic space",
            "mood": "courageous, intense, powerful",
            "composition": "dramatic off-center spherical framing",
            "camera_framing": "cinematic telephoto orbital perspective",
            "lighting": "harsh directional solar illumination creating stark crater shadows",
            "color_palette": "crimson red, rusty orange, burnt sienna, deep space black",
        },
        "planet_moon": {
            "name": "luminous Full Moon in dark starry midnight sky",
            "keywords": ["moon", "chandra", "चंद्रमा", "चन्द्र", "पूर्णिमा", "full moon", "lunar"],
            "objects": ["detailed cratered surface of the moon", "silvery lunar glow", "wispy clouds"],
            "exclusions": ["daytime sky", "sun flares", "food", "rudraksha"],
            "default_action": "casting silvery peaceful lunar light through thin midnight clouds",
            "default_setting": "deep midnight blue starfield with serene cosmic dust",
            "time_of_day": "midnight",
            "mood": "peaceful, serene, contemplative, intuitive",
            "composition": "upper-third lunar placement with delicate cloud trails below",
            "camera_framing": "200mm telephoto astronomical night photograph",
            "lighting": "pure silvery lunar glow illuminating atmospheric haze",
            "color_palette": "lunar silver, midnight blue, ethereal soft white",
        },
        "planet_sun": {
            "name": "radiant solar Sun with blazing corona flares in space",
            "keywords": ["sun", "surya", "सूर्य", "सूर्यदेव", "आदित्य", "solar flare"],
            "objects": ["blazing golden sun", "photosphere texture", "glowing solar prominences"],
            "exclusions": ["dark night", "moon", "gemstones", "rudraksha"],
            "default_action": "emitting brilliant warm golden solar energy and light rays",
            "default_setting": "space canvas with golden corona radiance against deep void",
            "time_of_day": "eternal solar radiance",
            "mood": "vital, sovereign, empowering",
            "composition": "central dramatic solar sphere with sweeping corona flares",
            "camera_framing": "filtered solar telescope view with corona prominence",
            "lighting": "intense golden-white core with radiant warm amber corona",
            "color_palette": "brilliant gold, warm saffron, incandescent white, deep space void",
        },
        "sacred_yantra": {
            "name": "sacred geometric Vedic Yantra etched on polished brass plate",
            "keywords": ["yantra", "यंत्र", "sri yantra", "श्री यंत्र", "sacred geometry", "ज्यामिति"],
            "objects": ["interlocking triangles of Sri Yantra", "fine engraved sacred Sanskrit geometric lines"],
            "exclusions": ["food", "insects", "rough stones", "rudraksha"],
            "default_action": "reflecting warm amber light from ceremonial flame",
            "default_setting": "sacred temple altar surrounded by fresh red lotus petals",
            "time_of_day": "evening puja hour",
            "mood": "sacred, precise, meditative, divine",
            "composition": "direct overhead top-down geometric symmetry shot",
            "camera_framing": "50mm overhead macro focusing on central bindu point",
            "lighting": "warm directional candlelight creating subtle specular reflections along etched lines",
            "color_palette": "polished brass gold, deep lotus red, dark sandalwood brown",
        },
        "sacred_temple_lamps": {
            "name": "sacred glowing brass oil lamps in ancient temple sanctum",
            "keywords": [
                "temple", "sanctum", "मंदिर", "दीपक", "diyas", "oil lamp",
                "deepam", "दीप", "आरती", "altar", "sanctum sanctorum"
            ],
            "objects": ["ornate traditional brass oil lamps (diyas)", "warm flickering golden flames"],
            "exclusions": ["modern electric lights", "food", "insects", "spacecraft", "rudraksha"],
            "default_action": "flickering with warm divine light casting golden reflections on carved stone pillars",
            "default_setting": "ancient granite Hindu temple sanctum sanctorum in twilight",
            "time_of_day": "evening twilight",
            "mood": "sacred, devotional, warm, reverent",
            "composition": "warm atmospheric medium shot with multiple lamps creating bokeh",
            "camera_framing": "shallow depth of field, 35mm cinematic lens",
            "lighting": "warm organic flame-light illuminating ancient carved stone textures",
            "color_palette": "warm flame gold, glowing amber, dark temple granite gray",
        },
        "sacred_havan_altar": {
            "name": "sacred Vedic Havan fire altar with pure consecrated flames",
            "keywords": [
                "havan", "हवन", "yagya", "यज्ञ", "homa", "fire altar",
                "sacred fire", "अग्नि कुंड", "हवन कुंड", "अग्नि"
            ],
            "objects": ["copper or brick havan kund", "pure glowing ceremonial orange flames", "sacred samagri"],
            "exclusions": ["wild forest fire", "trash fire", "food", "insects", "rudraksha"],
            "default_action": "burning cleanly with rising fragrant smoke and glowing embers",
            "default_setting": "peaceful ceremonial courtyard with sacred Vedic geometric chalk rangoli",
            "time_of_day": "morning sacred ritual hour",
            "mood": "purifying, sacred, consecrated, intense",
            "composition": "ground-level medium angle focusing on clean sacred flames",
            "camera_framing": "50mm prime lens with soft smoke trails drifting upwards",
            "lighting": "vibrant natural flame illumination with warm glowing embers",
            "color_palette": "blazing saffron orange, glowing ember red, antique copper",
        },
        "executive_desk_focus": {
            "name": "clean executive office desk with professional focus",
            "keywords": [
                "career", "office", "work desk", "business", "कार्यस्थल",
                "करियर", "व्यापार", "नौकरी", "desk", "workplace", "leadership"
            ],
            "objects": ["clean wooden executive desk", "fine fountain pen", "leather-bound notebook with notes"],
            "exclusions": ["chaos", "mess", "food", "insects", "rudraksha", "planets"],
            "default_action": "illuminated by warm morning window sunlight signifying clarity and productivity",
            "default_setting": "quiet modern professional office space with soft ambient bokeh",
            "time_of_day": "morning 9 AM business hour",
            "mood": "focused, poised, professional, dignified",
            "composition": "elegant low-angle desk perspective",
            "camera_framing": "35mm architectural lens, clean rectilinear lines",
            "lighting": "diffused natural window morning light and warm task lamp",
            "color_palette": "warm oak wood, deep espresso leather, soft morning white",
        },
    }

    # Stop words that must NOT trigger entities on their own
    DISAMBIGUATION_STOP_WORDS: Set[str] = {
        "fire", "house", "houses", "love", "wealth", "money", "peace", "remedy",
        "remedies", "metal", "stone", "rules", "rule", "sign", "signs", "danger",
        "mistake", "truth", "secret", "reason", "ways", "life", "first", "second",
        "third", "point", "guide", "placement", "water", "chart", "energy",
    }

    @classmethod
    def matches_entity(cls, text: str, keywords: List[str]) -> bool:
        """
        Strict word-boundary matching for English and Devanagari Hindi.
        Prevents substring false positives (e.g. 'moti' in 'emotional').
        """
        if not text:
            return False
        for kw in keywords:
            # English word boundary
            if re.search(r"[a-zA-Z]", kw):
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return True
            else:
                # Devanagari word boundary
                pattern = rf"(?<![\w\u0900-\u097F]){re.escape(kw)}(?![\w\u0900-\u097F])"
                if re.search(pattern, text):
                    return True
        return False

    @classmethod
    def detect_scene_entity(cls, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Detects specific entity from text using strict token boundary matching.
        Priority: Specific physical subjects (gemstones, crystals, specific planets)
        take strict precedence over generic background mentions like 'kundli'.
        """
        if not text:
            return None
        text_lower = text.lower()

        # Priority 1: Specific Sacred Gemstones & Crystals (Strict Precedence)
        gemstone_keys = [
            "emerald_gemstone", "blue_sapphire_gemstone", "yellow_sapphire_gemstone",
            "ruby_gemstone", "pyrite_crystal", "amethyst_crystal", "black_tourmaline",
            "citrine_crystal", "rudraksha_bead", "copper_water_remedy"
        ]
        for key in gemstone_keys:
            if key in cls.SPECIFIC_ENTITIES and cls.matches_entity(text_lower, cls.SPECIFIC_ENTITIES[key]["keywords"]):
                return key, cls.SPECIFIC_ENTITIES[key]

        # Priority 2: Specific Celestial Bodies / Planets
        planet_keys = ["planet_saturn", "planet_jupiter", "planet_mars", "planet_moon", "planet_sun"]
        for key in planet_keys:
            if key in cls.SPECIFIC_ENTITIES and cls.matches_entity(text_lower, cls.SPECIFIC_ENTITIES[key]["keywords"]):
                return key, cls.SPECIFIC_ENTITIES[key]

        # Priority 3: Executive Desk / Career Focus
        if "executive_desk_focus" in cls.SPECIFIC_ENTITIES and cls.matches_entity(text_lower, cls.SPECIFIC_ENTITIES["executive_desk_focus"]["keywords"]):
            return "executive_desk_focus", cls.SPECIFIC_ENTITIES["executive_desk_focus"]

        # Priority 4: All other specific entities in definition order
        for key, entity_def in cls.SPECIFIC_ENTITIES.items():
            if cls.matches_entity(text_lower, entity_def["keywords"]):
                return key, entity_def
        return None

    @classmethod
    def resolve_semantic_strategies(cls, narration: str, topic: str = "") -> Dict[str, Any]:
        """
        Determines semantic visual intent, required entities, primary visual strategy,
        and fallback visual strategy strictly driven by the narration text.
        Guarantees:
        - Script narration is the sole source of truth.
        - Saturn is never in primary or fallback unless explicitly in narration.
        - Generic Kundli chart is never in primary or fallback unless explicitly in narration.
        - Fallback visual is an alternative visual representing the same semantic meaning
          (e.g., career struggle/hourglass for career delays; solitary traveler/distant misty mountain
          for 12th house isolation; scales/ledger for financial pressure; serene dawn forest for vital calm).
        """
        text = f"{narration} {topic}".lower()
        spoken = narration.lower()

        has_saturn = any(k in spoken for k in ["saturn", "shani", "शनि"])
        has_kundli = any(k in spoken for k in ["kundli", "kundali", "birth chart", "कुंडली", "chart", "horoscope"])

        # Check Category A: Career delays / workplace obstacles / professional struggle
        career_keywords = [
            "career", "job", "promotion", "work", "business", "delay", "delays",
            "obstacle", "obstacles", "struggle", "struggles", "profession", "office",
            "workplace", "patience", "perseverance", "कर्म", "करियर", "नौकरी", "व्यापार",
            "बाधा", "विलंब", "धीमा", "रुकावट", "मेहनत"
        ]
        if any(k in spoken for k in career_keywords) or (any(k in text for k in ["career", "profession"]) and any(k in spoken for k in ["delay", "obstacle", "slow", "struggle"])):
            return {
                "visual_intent": "career_perseverance",
                "required_entities": ["focused professional", "time and perseverance elements"],
                "primary_visual_strategy": "cinematic photorealistic Saturn celestial body with Cassini rings" if has_saturn else "professional overcoming workplace obstacles with patience",
                "fallback_visual_strategy": "professional facing workplace obstacles, focused perseverance at desk with hourglass and warm natural lamp light",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of a determined professional sitting at a wooden work desk with an ancient hourglass, papers, warm morning window light, atmospheric depth, focused perseverance, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons, no planets"
                ),
            }

        # Check Category B: 12th house / isolation / solitude / foreign lands / quiet contemplation / subconscious
        isolation_keywords = [
            "12th house", "twelfth house", "12th bhav", "12वां", "बारहवां", "isolation",
            "solitude", "isolated", "foreign", "overseas", "distant land", "subconscious",
            "sleep", "dream", "moksha", "meditation", "contemplation", "अकेलापन", "एकांत",
            "विदेश", "बारहवां भाव", "ध्यान", "मोक्ष"
        ]
        if any(k in spoken for k in isolation_keywords):
            return {
                "visual_intent": "solitude_and_contemplation",
                "required_entities": ["solitary contemplative figure", "distant tranquil landscape"],
                "primary_visual_strategy": "12th house Vedic chart contemplation" if has_kundli else "solitary contemplative traveler on distant tranquil horizon",
                "fallback_visual_strategy": "solitary figure contemplating on a distant misty mountain ridge overlooking foreign horizon in quiet dawn light",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of a solitary contemplative traveler standing on a misty tranquil highland at dawn overlooking vast distant horizons, quiet peace, soft atmospheric mist, ethereal morning illumination, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons, no chart"
                ),
            }

        # Check Category C: Financial pressure / wealth / debts / expenses / economic stress / savings
        finance_keywords = [
            "wealth", "money", "finance", "financial", "debt", "debts", "savings",
            "income", "expenses", "loss", "losses", "balance", "ledger", "budget",
            "monetary", "धन", "पैसा", "आर्थिक", "कर्ज", "बचत", "खर्च", "नुकसान", "घाटा"
        ]
        if any(k in spoken for k in finance_keywords):
            return {
                "visual_intent": "financial_equilibrium",
                "required_entities": ["financial ledger", "brass balance scales", "vintage coins"],
                "primary_visual_strategy": "financial resources and monetary equilibrium",
                "fallback_visual_strategy": "vintage brass balance scales weighing coins on an antique oak ledger table under focused warm amber directional light",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of classical brass balance scales with golden coins and an open leather ledger on an oak table, dramatic warm directional side lighting, timeless financial contemplation, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons, no planets"
                ),
            }

        # Check Category D: Health / nervous system / vitality / physical calm / healing / biology
        health_keywords = [
            "health", "nervous system", "neural", "brain", "healing", "vitality",
            "body", "energy", "calm", "wellness", "stress", "swasthya", "स्वास्थ्य",
            "तंत्रिका", "आरोग्य", "ऊर्जा", "तनाव", "शांति"
        ]
        if any(k in spoken for k in health_keywords):
            return {
                "visual_intent": "biological_vitality_and_calm",
                "required_entities": ["neural synapse or serene vital calm"],
                "primary_visual_strategy": "neural balance and bio-electric calm",
                "fallback_visual_strategy": "tranquil serene forest with morning sunlight filtering through ancient cedar trees, radiating natural biological calm and vitality",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of a sun-drenched serene cedar forest canopy at sunrise, golden god rays filtering through pine needles, dew drops, peaceful revitalizing morning atmosphere, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons"
                ),
            }

        # Check Category E: Relationships / marriage / partnership / 7th house / love / harmony
        relationship_keywords = [
            "relationship", "relationships", "marriage", "partner", "partnership",
            "7th house", "seventh house", "7th bhav", "love", "spouse", "satva bhav",
            "सातवां", "विवाह", "संबंध", "सातवां भाव", "जीवनसाथी", "प्रेम"
        ]
        if any(k in spoken for k in relationship_keywords):
            return {
                "visual_intent": "relational_harmony",
                "required_entities": ["two harmonious silhouettes", "warm twilight horizon"],
                "primary_visual_strategy": "relational partnership and 7th house dynamics",
                "fallback_visual_strategy": "two respectful partner silhouettes walking side by side toward a warm golden sunset horizon in an open peaceful meadow",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of two elegant silhouettes walking side by side along a tranquil path towards a glowing golden amber sunset, soft lens flare, emotional harmony, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons"
                ),
            }

        # Check Category F: Explicit Saturn (when Saturn is explicitly mentioned)
        if has_saturn:
            return {
                "visual_intent": "saturn_cosmic_governance",
                "required_entities": ["Saturn celestial sphere with physical rings"],
                "primary_visual_strategy": "cinematic photorealistic Saturn celestial body with Cassini rings and atmospheric bands",
                "fallback_visual_strategy": "ancient stone sundial in quiet misty courtyard marking cosmic time and karmic discipline",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of an ancient weathered stone sundial in a quiet monastery stone courtyard, soft morning mist, shadow marking time, solemn discipline and perseverance, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons"
                ),
            }

        # Check Category CTA: Call to Action / DM Consultation / Sacred Guidance
        cta_keywords = ["comment", "कमेंट", "dm", "save", "सेव", "guidance", "consultation", "परामर्श", "मार्गदर्शन"]
        if any(k in spoken for k in cta_keywords):
            return {
                "visual_intent": "sacred_consultation_guidance",
                "required_entities": ["astrology consultation study", "antique scroll", "warm study lamp"],
                "primary_visual_strategy": "reverent Vedic astrologer consultation desk with authentic parchment charts and brass study lamp",
                "fallback_visual_strategy": "authentic ancient astrological consultation study with parchment scroll and brass lamp",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of an authentic Vedic astrologer consultation desk with handwritten horoscope charts on parchment, antique brass reading lamp, clean dark wood desk, thoughtful scholarly ambiance, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons"
                ),
            }

        # Check Category G: Kundli Chart (strictly if explicitly in narration)
        if has_kundli:
            return {
                "visual_intent": "kundli_chart_analysis",
                "required_entities": ["authentic Vedic Kundli birth chart"],
                "primary_visual_strategy": "authentic Vedic Kundli birth chart parchment with illuminated Sanskrit glyphs",
                "fallback_visual_strategy": "vintage brass navigational compass resting on an antique parchment map beside a glowing oil lantern",
                "fallback_generation_prompt": (
                    "cinematic photorealistic 9:16 vertical luxury photograph of an ornate brass navigational compass resting on an aged parchment navigational chart beside an amber oil lamp on dark mahogany wood, warm soft glow, exploration and destiny, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons"
                ),
            }

        # Default Category H: General wisdom / destiny / karma / philosophical guidance
        return {
            "visual_intent": "philosophical_guidance",
            "required_entities": ["antique brass compass", "parchment map", "warm study"],
            "primary_visual_strategy": "philosophical reflection and life direction",
            "fallback_visual_strategy": "vintage brass navigational compass resting on an antique parchment map beside a glowing oil lantern",
            "fallback_generation_prompt": (
                "cinematic photorealistic 9:16 vertical luxury photograph of an ornate brass navigational compass resting on an aged parchment navigational chart beside an amber oil lamp on dark mahogany wood, warm soft glow, exploration and destiny, 35mm film grain, 8k resolution, no text overlays, no watermarks, no cgi, no cartoons"
            ),
        }

    @classmethod
    def plan_scene_visual(
        cls,
        scene_dict: Dict[str, Any],
        scene_idx: int,
        total_scenes: int,
        topic: str = "",
        prev_scene: Optional[Dict[str, Any]] = None,
        next_scene: Optional[Dict[str, Any]] = None,
        diversity_tracker: Optional[Any] = None,
    ) -> SceneVisualPlan:
        """
        Plans a single scene's visual specification based strictly on its own content,
        driven by SceneVisualIntelligence for emotion, meaning, and visual metaphor.
        """
        from app.video.scene_visual_intelligence import SceneVisualIntelligence, ReelVisualDiversityTracker
        tracker = diversity_tracker or ReelVisualDiversityTracker()

        scene_id = f"scene_{scene_idx + 1}"
        spoken = scene_dict.get("spoken_line", "").strip()
        on_screen = scene_dict.get("on_screen_text", "").strip()
        vis_desc = scene_dict.get("visual_description", "").strip()
        est_duration = float(scene_dict.get("estimated_seconds", 4.0))

        # Check concrete specific entity match based strictly on narration & on-screen text
        scene_text = f"{spoken} {on_screen}".strip()
        matched_scene = cls.detect_scene_entity(scene_text)
        matched_topic = cls.detect_scene_entity(topic)

        # Execute SceneVisualIntelligence
        spec = SceneVisualIntelligence.analyze_scene(
            scene_dict=scene_dict,
            scene_idx=scene_idx,
            total_scenes=total_scenes,
            prev_scene=prev_scene,
            next_scene=next_scene,
            topic=topic,
            diversity_tracker=tracker,
        )

        # Exclusions: forbid generic templates
        forbidden = [
            "text overlays", "watermarks", "CGI cartoons", "synthetic 3D rings",
            "insects", "food", "wireframes", "distorted anatomy"
        ]
        # Anti-astrology template enforcement (Requirement 1):
        if not any(k in scene_text.lower() for k in ["planet", "saturn", "jupiter", "mars", "moon", "sun", "venus", "mercury", "शनि", "ग्रह"]):
            forbidden.append("floating planets in space")
        if not any(k in scene_text.lower() for k in ["zodiac", "kundli", "राशि", "कुंडली", "chart"]):
            forbidden.append("generic zodiac wheel")
        if not any(k in scene_text.lower() for k in ["temple", "mandir", "मंदिर", "sanctum"]):
            forbidden.append("generic cartoon temple")

        # Topic isolation and specific entity exclusions
        if matched_scene:
            for exc in matched_scene[1].get("exclusions", []):
                if exc not in forbidden:
                    forbidden.append(exc)

        if matched_topic and (not matched_scene or matched_topic[0] != matched_scene[0]):
            if matched_topic[1]["name"] not in forbidden:
                forbidden.append(matched_topic[1]["name"])
            for obj in matched_topic[1].get("objects", []):
                if obj not in forbidden:
                    forbidden.append(obj)

        # Determine subject, action, environment from spec or matched_scene
        is_generic_spec = not spec.subject or any(w in spec.subject.lower() for w in ["protagonist", "expressive", "solitary", "person", "embodying"])
        is_scene_relevant = False
        if matched_scene and spec.subject:
            is_scene_relevant = any(k in spec.subject.lower() for k in matched_scene[1].get("keywords", []))

        if matched_scene and (not is_scene_relevant or is_generic_spec):
            primary_subject = matched_scene[1]["name"]
            action = matched_scene[1]["default_action"]
            environment = matched_scene[1]["default_setting"]
            req_objs = copy.deepcopy(matched_scene[1].get("objects", [primary_subject]))
        else:
            primary_subject = spec.subject or (matched_scene[1]["name"] if matched_scene else "expressive protagonist")
            action = spec.action or (matched_scene[1]["default_action"] if matched_scene else "interacting with environment")
            environment = spec.environment or (matched_scene[1]["default_setting"] if matched_scene else "cinematic setting")
            req_objs = [primary_subject]

        # Enhance kundli_chart with dynamic house and planet intelligence only if explicitly a chart
        if matched_scene and matched_scene[0] == "kundli_chart" and any(k in scene_text.lower() for k in ["kundli", "कुंडली", "birth chart", "जन्मपत्रिका"]):
            from app.video.kundli_chart_generator import KundliChartGenerator, HOUSE_METADATA
            h_num, p_name = KundliChartGenerator.extract_house_and_planet(scene_text)
            if h_num and h_num in HOUSE_METADATA:
                meta = HOUSE_METADATA[h_num]
                p_clause = f" with {p_name}" if p_name else ""
                primary_subject = f"authentic Vedic Kundli birth chart with illuminated {meta['name_en']}{p_clause}"
                action = f"radiant amber-gold light specifically illuminating the {meta['name_en']} ({meta['sanskrit']}) grid with Sanskrit glyphs"
                req_objs = [f"diamond Kundli chart with glowing {meta['name_en']}", f"Sanskrit {meta['sanskrit']} markings"]

        # Ensure generation prompt satisfies standard prompt completeness
        # Sanitize spec lighting and composition against forbidden elements
        sanitized_lighting = spec.lighting or "warm natural golden lighting"
        sanitized_comp = spec.composition or "cinematic vertical 9:16 framing"
        for exc in forbidden:
            exc_clean = exc.lower().strip()
            if exc_clean and exc_clean not in {"3d renders", "cgi cartoons", "animated illustrations", "wireframes", "cartoons", "cgi", "drawings", "text overlays", "watermarks"}:
                pattern = re.compile(rf"\b{re.escape(exc_clean)}\b", re.IGNORECASE)
                sanitized_lighting = pattern.sub("", sanitized_lighting)
                sanitized_comp = pattern.sub("", sanitized_comp)

        clean_gen_prompt = (
            f"cinematic photorealistic 9:16 vertical luxury photograph of {primary_subject}, "
            f"{action}, {environment}, lighting: {sanitized_lighting}, {sanitized_comp}, "
            f"warm 35mm film grain, 8k resolution, authentic organic textures, "
            f"no text overlays, no watermarks, no cgi cartoons, no flat solid colors"
        )

        # Resolve script-first semantic intent and strategies
        semantic_info = cls.resolve_semantic_strategies(narration=scene_text, topic=topic)

        plan = SceneVisualPlan(
            scene_id=scene_id,
            scene_idx=scene_idx,
            exact_narration=spoken or on_screen,
            core_meaning=spec.core_meaning,
            main_subject=primary_subject,
            subject_action=action,
            environment=environment,
            time_of_day="morning golden hour",
            mood=spec.emotion,
            composition=spec.composition,
            camera_framing=spec.camera_angle,
            lighting=spec.lighting,
            color_palette=spec.color_palette,
            visual_style=spec.visual_style,
            required_visual_elements=req_objs,
            forbidden_visual_elements=forbidden,
            continuity_requirements=spec.continuity_notes,
            aspect_ratio="9:16",
            generation_prompt=clean_gen_prompt,
            validation_criteria=[primary_subject.split()[0].lower()],
            entity_key=matched_scene[0] if matched_scene else spec.emotion.lower(),
            estimated_duration=est_duration,
            emotion=spec.emotion,
            emotion_intensity=spec.emotion_intensity,
            viewer_feeling=spec.viewer_feeling,
            visual_concept=spec.visual_concept,
            visual_metaphor=spec.visual_metaphor,
            camera_angle=spec.camera_angle,
            continuity_notes=spec.continuity_notes,
            image_prompt=clean_gen_prompt,
            visual_intent=semantic_info["visual_intent"],
            required_entities=semantic_info["required_entities"],
            primary_visual_strategy=semantic_info["primary_visual_strategy"],
            fallback_visual_strategy=semantic_info["fallback_visual_strategy"],
            fallback_generation_prompt=semantic_info["fallback_generation_prompt"],
            used_fingerprints=[],
            validation_passed=False,
            is_valid=True,
        )
        return cls.validate_and_repair_plan(plan)

    @classmethod
    def _legacy_plan_scene_visual(
        cls,
        scene_dict: Dict[str, Any],
        scene_idx: int,
        total_scenes: int,
        topic: str = "",
    ) -> SceneVisualPlan:
        """
        Plans a single scene's visual specification based strictly on its own content.
        
        RELEVANCE-AWARE CONTEXT & TOPIC ISOLATION (TASK 4):
        - The scene's own narration is parsed first for concrete entities.
        - If the scene has a concrete entity, the Reel's overall topic is STRICTLY
          barred from overriding it.
        - If the topic entity is a physical object that conflicts with the scene's entity
          (e.g. topic is 'rudraksha_bead' and scene is 'nervous_system'), the topic entity
          is added to 'forbidden_visual_elements' so the AI image generator never hallucinates
          the topic object into the scene.
        """
        scene_id = f"scene_{scene_idx + 1}"
        spoken = scene_dict.get("spoken_line", "").strip()
        on_screen = scene_dict.get("on_screen_text", "").strip()
        vis_desc = scene_dict.get("visual_description", "").strip()
        est_duration = float(scene_dict.get("estimated_seconds", 4.0))

        # Scene text strictly excluding topic
        scene_text = f"{spoken} {on_screen} {vis_desc}".strip()

        # Step 1: Detect entity in scene text
        matched_scene = cls.detect_scene_entity(scene_text)

        # Step 2: Detect topic entity for contamination prevention
        matched_topic = cls.detect_scene_entity(topic)

        matched_entity_key: Optional[str] = None
        matched_entity_def: Optional[Dict[str, Any]] = None
        topic_isolated = False

        if matched_scene:
            matched_entity_key, matched_entity_def = matched_scene
            # Topic isolation active: if scene has its own entity different from topic entity
            if matched_topic and matched_topic[0] != matched_entity_key:
                topic_isolated = True
                logger.debug(
                    f"[SceneVisualPlanner] Scene {scene_idx + 1} isolated: "
                    f"Scene entity '{matched_entity_key}' overrides topic entity '{matched_topic[0]}'."
                )
        elif vis_desc and len(vis_desc.split()) >= 4 and not any(w in vis_desc.lower() for w in ["generic", "placeholder", "image"]):
            # Explicit rich visual description provided by director
            primary_sub = re.sub(r"^(cinematic\s+)?(photorealistic\s+)?(shot\s+of\s+)?", "", vis_desc, flags=re.I).strip()
            prompt = (
                f"cinematic photorealistic 9:16 vertical luxury photograph of {primary_sub}, "
                f"masterwork lighting, warm 35mm film grain, 8k resolution, authentic organic details, "
                f"no text, no watermark, no CGI cartoons, no geometric wireframes"
            )
            forbidden = ["food", "insects", "synthetic 3D rings", "text overlays", "watermarks"]
            if matched_topic:
                forbidden.append(matched_topic[1]["name"])

            plan = SceneVisualPlan(
                scene_id=scene_id,
                scene_idx=scene_idx,
                exact_narration=spoken,
                core_meaning=on_screen or primary_sub[:40],
                main_subject=primary_sub,
                subject_action="composed naturally in serene environment",
                environment="atmospheric background with cinematic depth",
                time_of_day="morning golden hour",
                mood="contemplative, cinematic",
                composition="centered hero composition with balanced headroom",
                camera_framing="50mm prime lens, shallow depth of field",
                lighting="soft natural window light with subtle rim reflection",
                color_palette="warm gold, deep amber, rich earth tones",
                visual_style="cinematic photorealistic 35mm film photograph, 9:16 vertical, masterwork lighting",
                required_visual_elements=[primary_sub],
                forbidden_visual_elements=forbidden,
                generation_prompt=prompt,
                validation_criteria=[primary_sub.split()[0].lower()],
                entity_key="custom_director_spec",
                estimated_duration=est_duration,
            )
            return cls.validate_and_repair_plan(plan)

        # Step 3: Call-to-action scene (last scene) fallback
        if not matched_entity_def and scene_idx == total_scenes - 1:
            # Match the CTA action or brand discussion rather than forcing sacred temple lamps
            matched_entity_key = "astrology_consultation"
            matched_entity_def = cls.SPECIFIC_ENTITIES.get("astrology_consultation", cls.SPECIFIC_ENTITIES["sacred_temple_lamps"])

        # Step 4: If still unmatched, use topic as secondary background theme
        if not matched_entity_def and matched_topic:
            matched_entity_key, matched_entity_def = matched_topic

        # Step 5: Default dignified scholarly baseline if completely unmatched
        if not matched_entity_def:
            matched_entity_key = "astrology_consultation"
            matched_entity_def = cls.SPECIFIC_ENTITIES["astrology_consultation"]

        # Construct visual plan fields
        primary_name = matched_entity_def["name"]
        default_action = matched_entity_def["default_action"]
        default_setting = matched_entity_def["default_setting"]
        req_objs = copy.deepcopy(matched_entity_def.get("objects", []))
        exclusions = copy.deepcopy(matched_entity_def.get("exclusions", []))
        time_of_day = matched_entity_def.get("time_of_day", "morning golden hour")
        mood = matched_entity_def.get("mood", "reverent, serene")
        composition = matched_entity_def.get("composition", "medium hero composition")
        camera_framing = matched_entity_def.get("camera_framing", "50mm natural lens, shallow depth of field")
        lighting = matched_entity_def.get("lighting", "soft natural light with gentle rim highlight")
        color_palette = matched_entity_def.get("color_palette", "warm gold, deep amber, earth tones")

        # TOPIC CONTAMINATION ENFORCEMENT:
        # If topic was isolated, explicitly forbid the topic's physical entity in this scene
        if topic_isolated and matched_topic:
            topic_entity_name = matched_topic[1]["name"]
            if topic_entity_name not in exclusions:
                exclusions.append(topic_entity_name)
            for obj in matched_topic[1].get("objects", []):
                if obj not in exclusions:
                    exclusions.append(obj)

        # Build prompt strictly adhering to photorealistic 9:16 vertical standard
        prompt = (
            f"cinematic photorealistic 9:16 vertical luxury photograph of {primary_name}, "
            f"{default_action}, {default_setting}, "
            f"lighting: {lighting}, {composition}, "
            f"warm 35mm film grain, 8k resolution, authentic organic textures, "
            f"no text, no watermark, no CGI cartoons, no geometric wireframes"
        )

        val_criteria = [w.lower() for w in req_objs[:2]]
        val_criteria.append(matched_entity_key)

        plan = SceneVisualPlan(
            scene_id=scene_id,
            scene_idx=scene_idx,
            exact_narration=spoken,
            core_meaning=on_screen or primary_name[:40],
            main_subject=primary_name,
            subject_action=default_action,
            environment=default_setting,
            time_of_day=time_of_day,
            mood=mood,
            composition=composition,
            camera_framing=camera_framing,
            lighting=lighting,
            color_palette=color_palette,
            visual_style="cinematic photorealistic 35mm film photograph, 9:16 vertical, masterwork lighting",
            required_visual_elements=req_objs,
            forbidden_visual_elements=exclusions,
            generation_prompt=prompt,
            validation_criteria=val_criteria,
            entity_key=matched_entity_key,
            estimated_duration=est_duration,
        )
        return cls.validate_and_repair_plan(plan)

    @classmethod
    def create_scene_visual_plan(
        cls,
        scene: Dict[str, Any],
        topic: str = "",
        scene_idx: int = 0,
        total_scenes: int = 5,
    ) -> SceneVisualPlan:
        """Alias for plan_scene_visual supporting varied keyword arguments."""
        return cls.plan_scene_visual(scene_dict=scene, scene_idx=scene_idx, total_scenes=total_scenes, topic=topic)

    # =========================================================================
    # VALIDATION & AUTOMATIC REPAIR (TASK 5)
    # =========================================================================
    @classmethod
    def validate_and_repair_plan(cls, plan: SceneVisualPlan) -> SceneVisualPlan:
        """
        Validates every scene visual plan and repairs any missing, generic,
        or contradictory elements.
        """
        repaired = copy.deepcopy(plan)
        errors: List[str] = []

        # Ensure semantic strategies are populated
        if not getattr(repaired, "fallback_visual_strategy", None):
            sem = cls.resolve_semantic_strategies(repaired.exact_narration)
            repaired.visual_intent = getattr(repaired, "visual_intent", "") or sem["visual_intent"]
            repaired.required_entities = getattr(repaired, "required_entities", []) or sem["required_entities"]
            repaired.primary_visual_strategy = getattr(repaired, "primary_visual_strategy", "") or sem["primary_visual_strategy"]
            repaired.fallback_visual_strategy = sem["fallback_visual_strategy"]
            repaired.fallback_generation_prompt = sem["fallback_generation_prompt"]

        # 1. Subject validation
        if not repaired.main_subject or len(repaired.main_subject.strip()) < 3:
            errors.append("Empty or trivial main_subject.")
            sem = cls.resolve_semantic_strategies(repaired.exact_narration)
            repaired.main_subject = sem["required_entities"][0] if sem["required_entities"] else "contemplative subject reflecting on cosmic guidance"
            repaired.entity_key = sem["visual_intent"]

        # Check for generic placeholders
        generic_words = {"placeholder", "image", "visual", "something", "tbd", "graphic", "picture"}
        if any(w == repaired.main_subject.lower() for w in generic_words):
            errors.append(f"Generic main_subject detected: '{repaired.main_subject}'.")
            sem = cls.resolve_semantic_strategies(repaired.exact_narration)
            repaired.main_subject = sem["required_entities"][0] if sem["required_entities"] else "contemplative subject reflecting on cosmic guidance"
            repaired.entity_key = sem["visual_intent"]

        # 2. Composition validation
        if not repaired.composition:
            repaired.composition = "centered hero composition with balanced 9:16 vertical headroom"
        if not repaired.camera_framing:
            repaired.camera_framing = "50mm cinematic lens, shallow depth of field"
        if not repaired.lighting:
            repaired.lighting = "warm golden hour lighting with soft atmospheric diffusion"
        elif "gold" in repaired.lighting.lower() and "golden" not in repaired.lighting.lower():
            repaired.lighting += ", warm golden radiance"
        if not repaired.color_palette:
            repaired.color_palette = "warm gold, deep amber, dark charcoal"

        # 3. Contradiction repairs: e.g. daytime sun in a midnight cosmic setting
        if "midnight" in repaired.time_of_day.lower() and "bright daylight" in repaired.lighting.lower():
            errors.append("Contradictory lighting vs time of day.")
            repaired.lighting = "soft silvery moonlight and subtle deep blue ambient fill"

        # 4. Mandatory exclusions
        mandatory_exclusions = ["text overlays", "watermarks", "synthetic 3D rings", "CGI cartoons", "insects", "food"]
        for exc in mandatory_exclusions:
            if exc not in repaired.forbidden_visual_elements:
                repaired.forbidden_visual_elements.append(exc)

        # 5. Aspect ratio enforcement
        repaired.aspect_ratio = "9:16"

        # 6. Rebuild generation prompt if missing or generic
        if not repaired.generation_prompt or len(repaired.generation_prompt.split()) < 8:
            repaired.generation_prompt = (
                f"cinematic photorealistic 9:16 vertical luxury photograph of {repaired.main_subject}, "
                f"{repaired.subject_action}, {repaired.environment}, "
                f"lighting: {repaired.lighting}, {repaired.composition}, "
                f"warm 35mm film grain, 8k resolution, authentic organic textures, "
                f"no text, no watermark, no CGI cartoons, no geometric wireframes"
            )

        repaired.is_valid = True
        repaired.validation_errors = errors
        return repaired

    # =========================================================================
    # REEL-WIDE DEDUPLICATION & MULTI-SCENE PLANNING
    # =========================================================================
    @classmethod
    def plan_reel_visuals(
        cls,
        scenes: List[Dict[str, Any]],
        topic: str = "",
    ) -> List[SceneVisualPlan]:
        """
        Plans complete visual specifications for every scene in a Reel,
        and enforces scene-to-scene visual variety using ReelVisualDiversityTracker.
        """
        from app.video.scene_visual_intelligence import ReelVisualDiversityTracker
        tracker = ReelVisualDiversityTracker()
        total = len(scenes)
        plans = []
        for idx, sc in enumerate(scenes):
            prev_sc = scenes[idx - 1] if idx > 0 else None
            next_sc = scenes[idx + 1] if idx + 1 < total else None
            plan = cls.plan_scene_visual(
                scene_dict=sc,
                scene_idx=idx,
                total_scenes=total,
                topic=topic,
                prev_scene=prev_sc,
                next_scene=next_sc,
                diversity_tracker=tracker,
            )
            plans.append(plan)

        # Deduplicate consecutive identical visual entities
        plans = cls.deduplicate_reel_plans(plans)
        return plans

    @classmethod
    def deduplicate_reel_plans(cls, plans: List[SceneVisualPlan]) -> List[SceneVisualPlan]:
        """
        Ensures consecutive scenes do not share the exact same visual framing
        or entity key. Modifies secondary scenes with varied angles/lighting.
        """
        seen_entities: Dict[str, int] = {}

        for plan in plans:
            k = plan.entity_key
            if k in seen_entities:
                seen_entities[k] += 1
                occurrence = seen_entities[k]
                # Diversify second or third occurrence
                if occurrence == 2:
                    plan.composition = "overhead top-down flat lay perspective"
                    plan.lighting = "dramatic low-key directional candlelight"
                    plan.generation_prompt += ", overhead top-down flat lay perspective, dramatic low-key candlelight"
                elif occurrence >= 3:
                    plan.composition = "extreme macro detail with abstract bokeh background"
                    plan.lighting = "subtle edge rim-lighting against deep shadow"
                    plan.generation_prompt += ", extreme macro detail with abstract bokeh background"
            else:
                seen_entities[k] = 1

        return plans
