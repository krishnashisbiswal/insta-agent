import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.gemini_client import generate_json
from config.settings import CONTENT_QUEUE_FILE, PUBLISHED_LOG_FILE

logger = logging.getLogger(__name__)


class ContentManager:
    """
    Manages autonomous topic queues and history.
    Ensures the agent NEVER generates duplicate topics and continuously
    refills its buffer with fresh viral angles.
    """

    def __init__(
        self,
        queue_file: Optional[Path] = None,
        history_file: Optional[Path] = None,
    ):
        self.queue_file = queue_file or CONTENT_QUEUE_FILE
        self.history_file = history_file or PUBLISHED_LOG_FILE
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def load_history(self) -> List[Dict[str, Any]]:
        """Load list of previously generated/published reels."""
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Error reading history file: {exc}")
            return []

    def load_queue(self) -> List[Dict[str, Any]]:
        """Load current topic queue."""
        if not self.queue_file.exists():
            return []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Error reading queue file: {exc}")
            return []

    def save_queue(self, queue: List[Dict[str, Any]]):
        """Save topic queue to disk."""
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)

    def save_history(self, history: List[Dict[str, Any]]):
        """Save history to disk."""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def refill_queue_with_gemini(
        self,
        niche: str = "Vedic Astrology, Gemstone Energy, Psychic Karma & Spiritual Devotion",
        language: str = "Hindi mixed with English",
        batch_size: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Use TrendDiscoveryEngine to brainstorm a fresh batch of viral topics that differ
        completely from previously published topics.
        """
        from app.analytics.trend_discovery_engine import TrendDiscoveryEngine
        trend_engine = TrendDiscoveryEngine()

        new_items = []
        for _ in range(batch_size):
            try:
                trend = trend_engine.discover_next_viral_trend(niche=niche, language=language)
                if trend and trend not in new_items:
                    new_items.append(trend)
                    trend_engine.record_generated_topic(trend)
            except Exception as exc:
                logger.warning(f"Error discovering trend in batch: {exc}")

        if not new_items:
            raise ValueError("TrendDiscoveryEngine returned no new topics for the queue.")

        current_queue = self.load_queue()
        current_queue.extend(new_items)
        self.save_queue(current_queue)
        print(f"[CONTENT MANAGER] Added {len(new_items)} trending, diverse topics to autonomous queue.")
        return new_items

    def pop_next_topic(
        self,
        niche: str = "Vedic Astrology, Gemstone Energy, Psychic Karma & Spiritual Devotion",
        language: str = "Hindi mixed with English",
    ) -> Dict[str, Any]:
        """
        Get the next topic to produce. Automatically refills the queue
        with Gemini if the buffer is running low.
        """
        queue = self.load_queue()
        if len(queue) < 2:
            print("[CONTENT MANAGER] Queue buffer low. Generating fresh topics with Gemini...")
            self.refill_queue_with_gemini(niche=niche, language=language)
            queue = self.load_queue()

        if not queue:
            raise RuntimeError("Failed to populate topic queue.")

        next_item = queue.pop(0)
        self.save_queue(queue)
        print(f"[CONTENT MANAGER] Selected next topic: \"{next_item['topic']}\" ({len(queue)} remaining in queue)")
        return next_item

    def record_published(self, record: Dict[str, Any]):
        """Append published reel entry to history log."""
        history = self.load_history()
        record["timestamp"] = int(time.time())
        record["formatted_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        history.append(record)
        self.save_history(history)
        print(f"[CONTENT MANAGER] Recorded publish in {self.history_file.name} (Total published: {len(history)})")


if __name__ == "__main__":
    cm = ContentManager()
    print("Testing Content Manager...")
    item = cm.pop_next_topic()
    print("Next topic to create:", item)
