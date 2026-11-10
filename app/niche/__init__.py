"""
Niche management and profile definitions.
"""
from app.niche.niche_profile import (
    NicheProfile,
    NicheRegistry,
    detect_niche_from_prompt,
    get_default_niche,
)

__all__ = [
    "NicheProfile",
    "NicheRegistry",
    "detect_niche_from_prompt",
    "get_default_niche",
]
