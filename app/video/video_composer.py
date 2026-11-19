"""
Backward-compatibility adapter for video composition.

The production video pipeline uses `app.video.cinematic_composer.create_cinematic_reel_video`
which provides full 1080x1920 9:16 vertical video composition with synchronized TTS,
captions, dynamic motion effects, and strict quality control.

This module provides `create_reel_video` as a legacy entrypoint that forwards to
`create_cinematic_reel_video`.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.video.cinematic_composer import create_cinematic_reel_video

logger = logging.getLogger(__name__)


def create_reel_video(
    script_data: Dict[str, Any],
    audio_path: Optional[str] = None,
    output_filename: Optional[str] = None,
    theme_name: str = "cosmic",
) -> Path:
    """
    Assemble the complete 1080x1920 vertical Reel video using cinematic composer.
    Forwards directly to `app.video.cinematic_composer.create_cinematic_reel_video`.
    """
    logger.info("create_reel_video invoked; delegating to create_cinematic_reel_video")
    return create_cinematic_reel_video(
        script_data=script_data,
        audio_path=audio_path,
        output_filename=output_filename,
    )


__all__ = ["create_reel_video"]
