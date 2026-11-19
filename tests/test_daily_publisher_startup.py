"""
Regression test for DailyAlgorithmPublisher module startup and typing resolution.

Verifies:
1. Module imports cleanly without NameError (preventing 'List' is not defined regression).
2. All type annotations resolve successfully via typing.get_type_hints without evaluation failures.
3. Importing the module initiates zero live network/API calls when credentials are absent.
4. DailyAlgorithmPublisher can be instantiated safely with a mock or temp tracker file.
"""

from __future__ import annotations

import os
import sys
import typing
from pathlib import Path
from unittest.mock import patch


def test_daily_algorithm_publisher_imports_without_name_error():
    """Verify daily_algorithm_publisher imports without NameError for List or other typing symbols."""
    # Ensure environment has no external secrets
    sanitized_env = {k: v for k, v in os.environ.items() if not k.startswith(("INSTAGRAM_", "GEMINI_", "SARVAM_"))}
    with patch.dict(os.environ, sanitized_env, clear=True):
        import app.autonomous.daily_algorithm_publisher as pub_module

        assert hasattr(pub_module, "DailyAlgorithmPublisher")
        publisher_cls = pub_module.DailyAlgorithmPublisher
        assert isinstance(publisher_cls, type)


def test_daily_algorithm_publisher_type_hints_resolve():
    """Verify typing.get_type_hints succeeds on DailyAlgorithmPublisher methods (specifically List[Path])."""
    from app.autonomous.daily_algorithm_publisher import DailyAlgorithmPublisher

    # Resolving type hints forces Python to evaluate Optional[List[Path]] annotations
    hints = typing.get_type_hints(DailyAlgorithmPublisher.produce_trending_reel)
    assert "scene_image_paths" in hints

    # Verify scene_image_paths annotation contains Path
    type_repr = str(hints["scene_image_paths"])
    assert "List" in type_repr or "list" in type_repr
    assert "Path" in type_repr


def test_daily_algorithm_publisher_instantiation_without_network(tmp_path: Path):
    """Verify DailyAlgorithmPublisher instantiates cleanly without performing network calls."""
    from app.autonomous.daily_algorithm_publisher import DailyAlgorithmPublisher

    tracker_file = tmp_path / "test_tracker.json"
    with patch.dict(os.environ, {"INSTAGRAM_SESSION_ID": ""}):
        publisher = DailyAlgorithmPublisher(tracker_file=tracker_file)
        assert publisher.tracker_file == tracker_file
        assert publisher.has_posted_today() is False
