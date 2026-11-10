import pytest
from pathlib import Path
from app.creative.creative_director import (
    ContentFormat,
    CreativeDirector,
    determine_optimal_format,
)
from app.creative.carousel_builder import CarouselBuilder
from app.creative.story_builder import StoryBuilder
from app.niche.niche_profile import get_default_niche


def test_determine_optimal_format():
    tech = get_default_niche("tech_ai")
    # Step-by-step topics should route to Carousel
    f1 = determine_optimal_format("Step-by-step roadmap to learn LangChain in 2026", tech)
    assert f1 == ContentFormat.CAROUSEL

    # Poll / quick checks should route to Story
    f2 = determine_optimal_format("Daily poll: Python vs Rust for backend?", tech)
    assert f2 == ContentFormat.STORY

    # Narrative traits / contrarian hooks should route to Reel
    f3 = determine_optimal_format("Why senior engineers avoid microservices", tech)
    assert f3 == ContentFormat.REEL


def test_carousel_builder(tmp_path):
    builder = CarouselBuilder(output_dir=tmp_path)
    slides = [
        {"title": "Slide 1: The Problem", "body": "Why most developers struggle with async Python loops."},
        {"title": "Slide 2: The Solution", "body": "Use asyncio task groups introduced in Python 3.11."},
        {"title": "Slide 3: Action Plan", "body": "Refactor your worker scripts and profile memory usage."},
    ]
    out_files = builder.build_deck(
        topic="Async Python Mastery",
        slides_data=slides,
        brand_handle="@pythontips",
        niche_profile=get_default_niche("tech_ai"),
    )
    assert len(out_files) == 3
    for p in out_files:
        assert p.exists()
        assert p.stat().st_size > 1000


def test_story_builder(tmp_path):
    builder = StoryBuilder(output_dir=tmp_path)
    story_path = builder.build_poll_story(
        question="Which AI coding tool do you use daily?",
        option_a="Cursor / Claude",
        option_b="GitHub Copilot",
        brand_handle="@aidaily",
    )
    assert story_path.exists()
    assert story_path.stat().st_size > 1000
