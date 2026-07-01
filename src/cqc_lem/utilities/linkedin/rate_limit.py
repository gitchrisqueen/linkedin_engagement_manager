"""Shared circuit breaker for LinkedIn HTTP 429 rate-limiting.

LinkedIn rate-limits by egress IP, so a 429 hit by one engagement task means every
other Selenium task (comments, replies, viewer DMs, appreciation DMs) will also be
throttled. Without coordination each task independently spins up a browser, navigates
to the feed, and re-trips the limit — which prolongs the block. This breaker records
the 429 in Redis with a cooldown TTL so subsequent tasks skip the LinkedIn navigation
until it expires. Fails open: if Redis is unavailable the breaker no-ops and callers
behave as before.
"""

import os

from cqc_lem.utilities.logger import log_warning

_COOLDOWN_KEY = "linkedin:429_cooldown"
_DEFAULT_COOLDOWN_SECONDS = 1800  # 30 min


class LinkedInRateLimited(RuntimeError):
    """LinkedIn is rate-limiting this session (HTTP 429) — back off before retrying.

    Subclasses RuntimeError so existing broad handlers keep treating it as a fatal,
    back-off-worthy login failure.
    """


def _cooldown_seconds() -> int:
    try:
        return int(os.getenv("LINKEDIN_RATE_LIMIT_COOLDOWN_SECONDS", str(_DEFAULT_COOLDOWN_SECONDS)))
    except ValueError:
        return _DEFAULT_COOLDOWN_SECONDS


def _redis_client():
    """Redis handle for the breaker, or None if unavailable (breaker then no-ops).

    Uses the Celery broker URL when it points at Redis; on AWS the broker is SQS and
    the result backend is Redis, so fall back to that, then to the local default.
    """
    try:
        import redis
    except Exception:
        return None
    url = os.getenv("CELERY_BROKER_URL", "")
    if not url.startswith("redis"):
        url = os.getenv("CELERY_RESULT_BACKEND", "")
    if not url.startswith("redis"):
        url = f"redis://redis:{os.getenv('REDIS_PORT', '6379')}/0"
    try:
        return redis.Redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
    except Exception:
        return None


def mark_rate_limited(reason: str = "") -> None:
    seconds = _cooldown_seconds()
    client = _redis_client()
    if client is None:
        return
    try:
        client.set(_COOLDOWN_KEY, reason or "429", ex=seconds)
        log_warning(f"LinkedIn 429 circuit breaker OPEN for {seconds}s — Selenium engagement paused",
                    action_type="rate_limit", http_status=429)
    except Exception as e:
        log_warning("Failed to set LinkedIn 429 circuit breaker", exc=e, action_type="rate_limit")


def rate_limit_cooldown_remaining() -> int:
    """Seconds left on the breaker, or 0 if closed / Redis unavailable."""
    client = _redis_client()
    if client is None:
        return 0
    try:
        ttl = client.ttl(_COOLDOWN_KEY)
    except Exception:
        return 0
    return ttl if ttl and ttl > 0 else 0


def clear_rate_limit() -> None:
    client = _redis_client()
    if client is None:
        return
    try:
        client.delete(_COOLDOWN_KEY)
    except Exception:
        pass
