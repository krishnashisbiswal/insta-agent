"""
Empirical Instagram Insights and Statistical Performance Tracker.

Replaces arbitrary counter increments with real statistical analysis of Instagram reach,
saves, shares, and engagement rates fetched via Meta Graph API.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import STORAGE_DIR

logger = logging.getLogger(__name__)


@dataclass
class PostMetrics:
    media_id: str
    permalink: str
    topic: str
    niche_id: str
    format: str
    published_at: float
    reach: int = 0
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    saves: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    save_rate: float = 0.0
    share_rate: float = 0.0

    def compute_rates(self) -> None:
        if self.reach > 0:
            total_interactions = self.likes + self.comments + self.saves + self.shares
            self.engagement_rate = round((total_interactions / self.reach) * 100, 2)
            self.save_rate = round((self.saves / self.reach) * 100, 2)
            self.share_rate = round((self.shares / self.reach) * 100, 2)


@dataclass
class PerformanceSummary:
    total_posts: int
    total_reach: int
    mean_reach: float
    median_reach: float
    std_dev_reach: float
    mean_engagement_rate: float
    mean_save_rate: float
    top_performing_topics: List[Dict[str, Any]] = field(default_factory=list)


class EmpiricalPerformanceTracker:
    """
    Empirical statistical analysis engine for Instagram content.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir or (STORAGE_DIR / "analytics"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.storage_dir / "posts_metrics.json"
        self._metrics: Dict[str, PostMetrics] = {}
        self._load()

    def record_post(
        self,
        media_id: str,
        topic: str,
        niche_id: str,
        content_format: str = "REEL",
        permalink: str = "",
        published_at: Optional[float] = None,
    ) -> PostMetrics:
        now = published_at or time.time()
        pm = PostMetrics(
            media_id=media_id,
            permalink=permalink,
            topic=topic,
            niche_id=niche_id,
            format=content_format.upper(),
            published_at=now,
        )
        self._metrics[media_id] = pm
        self._save()
        return pm

    def update_metrics(
        self,
        media_id: str,
        reach: int,
        impressions: int,
        likes: int,
        comments: int,
        saves: int,
        shares: int,
    ) -> Optional[PostMetrics]:
        pm = self._metrics.get(media_id)
        if not pm:
            logger.warning(f"Media {media_id} not found in performance tracker.")
            return None

        pm.reach = reach
        pm.impressions = impressions
        pm.likes = likes
        pm.comments = comments
        pm.saves = saves
        pm.shares = shares
        pm.compute_rates()
        self._save()
        return pm

    def calculate_summary(self, niche_id: Optional[str] = None) -> PerformanceSummary:
        records = list(self._metrics.values())
        if niche_id:
            records = [r for r in records if r.niche_id == niche_id]

        if not records:
            return PerformanceSummary(
                total_posts=0,
                total_reach=0,
                mean_reach=0.0,
                median_reach=0.0,
                std_dev_reach=0.0,
                mean_engagement_rate=0.0,
                mean_save_rate=0.0,
            )

        reaches = [r.reach for r in records]
        engagements = [r.engagement_rate for r in records]
        save_rates = [r.save_rate for r in records]

        total_posts = len(records)
        total_reach = sum(reaches)
        mean_reach = round(statistics.mean(reaches), 2)
        median_reach = round(statistics.median(reaches), 2)
        std_reach = round(statistics.stdev(reaches), 2) if total_posts > 1 else 0.0
        mean_eng = round(statistics.mean(engagements), 2)
        mean_save = round(statistics.mean(save_rates), 2)

        sorted_by_eng = sorted(records, key=lambda x: (x.save_rate + x.engagement_rate), reverse=True)
        top_topics = [
            {"media_id": r.media_id, "topic": r.topic, "reach": r.reach, "engagement_rate": r.engagement_rate, "save_rate": r.save_rate}
            for r in sorted_by_eng[:5]
        ]

        return PerformanceSummary(
            total_posts=total_posts,
            total_reach=total_reach,
            mean_reach=mean_reach,
            median_reach=median_reach,
            std_dev_reach=std_reach,
            mean_engagement_rate=mean_eng,
            mean_save_rate=mean_save,
            top_performing_topics=top_topics,
        )

    def _save(self) -> None:
        try:
            data = {mid: asdict(pm) for mid, pm in self._metrics.items()}
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to save post metrics: {exc}")

    def _load(self) -> None:
        if not self.metrics_file.exists():
            return
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._metrics = {mid: PostMetrics(**val) for mid, val in data.items()}
        except Exception as exc:
            logger.error(f"Failed to load post metrics: {exc}")
