import pytest
from app.niche.niche_profile import (
    NicheProfile,
    NicheRegistry,
    detect_niche_from_prompt,
    get_default_niche,
)


def test_builtin_niches():
    tech = get_default_niche("tech_ai")
    assert tech.name == "Technology & Artificial Intelligence"
    assert "LLM" in tech.terminology_glossary

    fitness = get_default_niche("fitness")
    assert fitness.niche_id == "fitness_wellness"
    assert "Hypertrophy" in fitness.sub_niches

    finance = get_default_niche("money")
    assert finance.niche_id == "personal_finance"
    assert "Index Funds" in finance.sub_niches


def test_custom_niche_registration(tmp_path):
    registry = NicheRegistry(custom_dir=tmp_path)
    custom = NicheProfile(
        niche_id="gaming_retro",
        name="Retro Gaming & Pixel Art",
        sub_niches=["SNES", "PlayStation 1", "Chiptunes"],
        target_audience="90s gamers and pixel art collectors",
    )
    registry.register(custom, persist=True)

    # Verify memory
    retrieved = registry.get("gaming_retro")
    assert retrieved.name == "Retro Gaming & Pixel Art"

    # Verify disk persistence
    saved_file = tmp_path / "gaming_retro.json"
    assert saved_file.exists()

    # Verify reload
    registry2 = NicheRegistry(custom_dir=tmp_path)
    reloaded = registry2.get("gaming_retro")
    assert reloaded.name == "Retro Gaming & Pixel Art"


def test_heuristic_niche_detection():
    n1 = detect_niche_from_prompt("Best compound leg workout for building quadriceps")
    assert n1.niche_id == "fitness_wellness"

    n2 = detect_niche_from_prompt("Top 3 S&P 500 index funds to buy in your 20s")
    assert n2.niche_id == "personal_finance"

    n3 = detect_niche_from_prompt("How to build an AI agent using python and langchain")
    assert n3.niche_id == "tech_ai"

    n4 = detect_niche_from_prompt("Why the Roman Empire collapsed in 476 AD")
    assert n4.niche_id == "education_history"
