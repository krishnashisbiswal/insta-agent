"""
Dependency Integrity & Production Import Test Suite.
Verifies that all declared production dependencies are resolvable and importable
without missing modules, syntax errors, or circular import side-effects.
"""

import importlib
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Map PyPI package names to their canonical top-level import names
PACKAGE_IMPORT_MAP = {
    "google-genai": "google.genai",
    "moviepy": "moviepy",
    "Pillow": "PIL",
    "imagehash": "imagehash",
    "imageio-ffmpeg": "imageio_ffmpeg",
    "numpy": "numpy",
    "opencv-python-headless": "cv2",
    "edge-tts": "edge_tts",
    "httpx": "httpx",
    "requests": "requests",
    "instagrapi": "instagrapi",
    "filelock": "filelock",
    "python-dotenv": "dotenv",
    "pydantic": "pydantic",
    "cryptography": "cryptography",
    "pyjwt": "jwt",
    "bcrypt": "bcrypt",
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic",
    "fastapi": "fastapi",
}


def test_requirements_files_exist():
    """Verify requirements.txt and requirements-dev.txt are present."""
    req_prod = PROJECT_ROOT / "requirements.txt"
    req_dev = PROJECT_ROOT / "requirements-dev.txt"
    assert req_prod.exists(), "requirements.txt must exist"
    assert req_dev.exists(), "requirements-dev.txt must exist"


def test_production_dependencies_importable():
    """Verify that every core production dependency can be imported."""
    for pkg_name, import_name in PACKAGE_IMPORT_MAP.items():
        try:
            mod = importlib.import_module(import_name)
            assert mod is not None, f"Failed to import {import_name} for package {pkg_name}"
        except ImportError as exc:
            pytest.fail(f"Required package '{pkg_name}' ({import_name}) failed to import: {exc}")


def test_core_app_packages_importable():
    """Verify that all core application modules import cleanly without side-effects."""
    core_modules = [
        "app.agents.gemini_client",
        "app.agents.script_agent",
        "app.agents.caption_agent",
        "app.video.cinematic_composer",
        "app.video.video_quality_gate",
        "app.video.tts_engine",
        "app.video.smart_voice_router",
        "app.video.scene_visual_planner",
        "app.storage.permanent_visual_memory",
        "app.storage.production_workspace",
        "app.publishing.publishing_service",
        "app.instagram.uploader",
    ]
    for mod_name in core_modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Core module {mod_name} must import cleanly"
