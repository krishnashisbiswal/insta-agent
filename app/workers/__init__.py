"""
Background Workers Package for Insta-Agent Distributed Tasks.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.workers.publishing_worker import PublishingWorker


def __getattr__(name: str):
    if name == "PublishingWorker":
        from app.workers.publishing_worker import PublishingWorker
        return PublishingWorker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["PublishingWorker"]
