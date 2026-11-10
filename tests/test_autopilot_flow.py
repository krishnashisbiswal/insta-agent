import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.analytics.self_learning_engine import SelfLearningEngine
from app.autonomous.timing_engine import get_current_time, is_in_optimal_window, seconds_until_next_optimal, PEAK_WINDOWS
from app.autonomous.content_manager import ContentManager
from config.settings import TIMEZONE


def test_timing_engine_slots():
    now = get_current_time(TIMEZONE)
    assert now is not None
    in_peak, slot_name = is_in_optimal_window(TIMEZONE)
    assert isinstance(in_peak, bool)
    assert isinstance(slot_name, str)
    assert len(PEAK_WINDOWS) > 0


def test_self_learning_playbook_load():
    engine = SelfLearningEngine()
    playbook = engine.load_playbook()
    assert isinstance(playbook, dict)
    assert "evolution_level" in playbook


def test_content_manager_queue_structure():
    cm = ContentManager()
    queue = cm.load_queue()
    assert isinstance(queue, list)
