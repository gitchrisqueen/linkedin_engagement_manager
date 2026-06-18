import os
import time

from cqc_lem.utilities.logger import myprint

try:
    import posthog as _posthog

    _posthog.api_key = os.getenv("POSTHOG_API_KEY", "")
    _posthog.host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")
    _enabled = bool(_posthog.api_key)
except ImportError:
    _posthog = None  # type: ignore[assignment]
    _enabled = False


def track_llm_call(model: str, prompt_tokens: int, completion_tokens: int,
                   latency_ms: int, success: bool = True, user_id=None) -> None:
    if not _enabled or _posthog is None:
        return
    _posthog.capture(
        distinct_id=str(user_id or "system"),
        event="llm_call",
        properties={
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
            "success": success,
        },
    )


def track_task(task_name: str, duration_ms: int, success: bool = True,
               user_id=None, **extra) -> None:
    if not _enabled or _posthog is None:
        return
    _posthog.capture(
        distinct_id=str(user_id or "system"),
        event="celery_task",
        properties={"task": task_name, "duration_ms": duration_ms, "success": success, **extra},
    )


def track_api_call(route: str, method: str, status_code: int,
                   latency_ms: int, user_id=None) -> None:
    if not _enabled or _posthog is None:
        return
    _posthog.capture(
        distinct_id=str(user_id or "anonymous"),
        event="api_call",
        properties={
            "route": route,
            "method": method,
            "status_code": status_code,
            "latency_ms": latency_ms,
        },
    )
