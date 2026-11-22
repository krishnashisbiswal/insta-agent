"""
Publishing Error Taxonomy & Classification.

Differentiates:
- Permanent errors (never retry): Auth, Config, Validation, Quota, Policy
- Transient errors (capped retry with backoff): Rate Limit, Network / Socket / Timeout
- Uncertain outcome errors (requires reconciliation; never re-publish blindly): Timeout during publish
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class PublishingError(Exception):
    """Base error for all publishing-related failures."""
    def __init__(self, message: str, error_category: str = "transient", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_category = error_category
        self.details = details or {}


class PublishingAuthError(PublishingError):
    """Permanent error: invalid, expired, revoked, or missing credentials."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_category="permanent_auth", details=details)


class PublishingConfigError(PublishingError):
    """Permanent error: misconfigured account, missing required settings, quota exceeded."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_category="permanent_config", details=details)


class PublishingValidationError(PublishingError):
    """Permanent error: media or caption failed pre-publish quality or format checks."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_category="permanent_validation", details=details)


class PublishingRateLimitError(PublishingError):
    """Transient error: API rate limit exceeded. Retry with backoff or Retry-After delay."""
    def __init__(self, message: str, retry_after_seconds: Optional[float] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_category="rate_limit", details=details)
        self.retry_after_seconds = retry_after_seconds


class PublishingNetworkError(PublishingError):
    """Transient error: network timeout, DNS failure, connection reset. Retry with backoff."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_category="transient_network", details=details)


class PublishingUncertainOutcomeError(PublishingError):
    """
    Recoverable error: request was dispatched to publish media, but response was lost
    or interrupted. The Reel MAY have succeeded on Instagram.
    NEVER re-publish blindly; must reconcile against Meta API or live profile.
    """
    def __init__(self, message: str, container_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_category="uncertain_outcome", details=details)
        self.container_id = container_id


class DuplicatePublishPreventedError(PublishingError):
    """Idempotency error: identical content or video already published or currently processing."""
    def __init__(self, message: str, existing_job_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_category="duplicate_prevented", details=details)
        self.existing_job_id = existing_job_id


class HardUploadGateError(PublishingValidationError):
    """
    Hard upload gate error: video failed mandatory technical verification,
    hash verification failed, artifact was modified, stale, or validation report is missing/rejected.
    NEVER upload a video when this error is raised.
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)

