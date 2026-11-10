"""
AI Creative Director.

Evaluates topics, niche strategies, and audience objectives to dynamically route
content into the highest-impact Instagram format (Reels, Carousels, Stories, Single Posts).
Eliminates one-size-fits-all Reel forcing.
"""

from __future__ import annotations

import enum
import logging
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.niche.niche_profile import NicheProfile, get_default_niche
from app.agents.gemini_client import generate_json

logger = logging.getLogger(__name__)


class ContentFormat(str, enum.Enum):
    REEL = "REEL"
    CAROUSEL = "CAROUSEL"
    STORY = "STORY"
    POST = "POST"


@dataclass
class CreativeBrief:
    topic: str
    niche_id: str
    format: ContentFormat
    rationale: str
    target_audience: str
    visual_direction: str
    call_to_action: str
    outline: List[Dict[str, Any]] = field(default_factory=list)
    caption_draft: str = ""
    suggested_hashtags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["format"] = self.format.value
        return data


def determine_optimal_format(topic: str, niche_profile: NicheProfile) -> ContentFormat:
    """
    Heuristically or via AI determines the highest-performing Instagram format.
    - Deep-dive guides, step-by-step tutorials, checklists -> CAROUSEL
    - Quick questions, daily transits, polls, behind-the-scenes -> STORY
    - Contrarian truths, high-energy demonstrations, dramatic traits -> REEL
    - Quotations, infographics, announcement banners -> POST
    """
    t_lower = topic.lower()

    # Step-by-step or list indicators thrive as Carousels
    if any(k in t_lower for k in ["step-by-step", "guide", "checklist", "slides", "carousel", "framework", "roadmap", "blueprint", "5 tools", "10 rules", "cheat sheet"]):
        return ContentFormat.CAROUSEL

    # Real-time questions or flash polls thrive as Stories
    if any(k in t_lower for k in ["poll", "quiz", "ask me", "q&a", "today's update", "flash transit", "quick check"]):
        return ContentFormat.STORY

    # Single quotes or stat announcements
    if any(k in t_lower for k in ["quote", "stat of the day", "infographic", "wallpaper", "announcement"]):
        return ContentFormat.POST

    # High-retention narrative, dynamic video
    return ContentFormat.REEL


class CreativeDirector:
    """
    Directs the strategic ideation and format assignment.
    """

    def __init__(self, default_niche: Optional[NicheProfile] = None):
        self.default_niche = default_niche or get_default_niche()

    def create_brief(
        self,
        topic: str,
        niche_profile: Optional[NicheProfile] = None,
        force_format: Optional[ContentFormat] = None,
    ) -> CreativeBrief:
        profile = niche_profile or self.default_niche
        chosen_format = force_format or determine_optimal_format(topic, profile)

        # AI-directed detailed brief
        prompt = f"""
You are an executive Creative Director for an elite Instagram brand in {profile.name}.
Target Audience: {profile.target_audience}
Tone: {profile.tone}
Topic: {topic}
Selected Instagram Format: {chosen_format.value}

Design a comprehensive creative brief for this content.
Return ONLY valid JSON matching this schema:
{{
  "rationale": "Why {chosen_format.value} is the highest-converting format for this specific topic",
  "visual_direction": "Lighting, typography, color palette, pacing matching {profile.visual_style}",
  "call_to_action": "{profile.cta_presets[0]}",
  "outline": [
    {{"part": 1, "title": "Opening Hook", "description": "What happens in the first frame"}},
    {{"part": 2, "title": "Core Value Point 1", "description": "Key breakdown"}},
    {{"part": 3, "title": "Core Value Point 2", "description": "Expansion"}},
    {{"part": 4, "title": "Summary / CTA", "description": "Closing takeaway"}}
  ],
  "caption_draft": "Engaging caption draft with line breaks and hook in first 100 characters",
  "suggested_hashtags": ["#Tag1", "#Tag2", "#Tag3"]
}}
"""
        try:
            ai_data = generate_json(prompt)
            return CreativeBrief(
                topic=topic,
                niche_id=profile.niche_id,
                format=chosen_format,
                rationale=ai_data.get("rationale", f"Selected {chosen_format.value} as optimal format"),
                target_audience=profile.target_audience,
                visual_direction=ai_data.get("visual_direction", profile.visual_style),
                call_to_action=ai_data.get("call_to_action", profile.cta_presets[0]),
                outline=ai_data.get("outline", []),
                caption_draft=ai_data.get("caption_draft", ""),
                suggested_hashtags=ai_data.get("suggested_hashtags", []),
            )
        except Exception as exc:
            logger.warning(f"AI creative brief fallback: {exc}")
            return CreativeBrief(
                topic=topic,
                niche_id=profile.niche_id,
                format=chosen_format,
                rationale=f"Selected {chosen_format.value} by heuristic strategy",
                target_audience=profile.target_audience,
                visual_direction=profile.visual_style,
                call_to_action=profile.cta_presets[0],
                outline=[{"part": 1, "title": "Hook", "description": topic}],
                caption_draft=f"Check out this breakdown on {topic}.\n\n{profile.cta_presets[0]}",
                suggested_hashtags=[f"#{profile.niche_id.replace('_', '')}", "#InstagramGrowth"],
            )
