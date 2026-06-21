"""Unit tests for cqc_lem.utilities.observability."""

import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit

_MOD = "cqc_lem.utilities.observability"


class TestTrackLlmCall:
    def test_captures_llm_call_event(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_llm_call
            track_llm_call(model="lem-simple", prompt_tokens=10, completion_tokens=20, latency_ms=150)

        mock_ph.capture.assert_called_once()
        _, kwargs = mock_ph.capture.call_args
        assert kwargs["event"] == "llm_call"
        props = kwargs["properties"]
        assert props["model"] == "lem-simple"
        assert props["prompt_tokens"] == 10
        assert props["completion_tokens"] == 20
        assert props["total_tokens"] == 30
        assert props["latency_ms"] == 150
        assert props["success"] is True

    def test_uses_system_distinct_id_when_no_user(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_llm_call
            track_llm_call(model="lem-medium", prompt_tokens=5, completion_tokens=5, latency_ms=50)

        _, kwargs = mock_ph.capture.call_args
        assert kwargs["distinct_id"] == "system"

    def test_uses_user_id_as_distinct_id(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_llm_call
            track_llm_call(model="lem-complex", prompt_tokens=100, completion_tokens=200,
                           latency_ms=500, user_id=42)

        _, kwargs = mock_ph.capture.call_args
        assert kwargs["distinct_id"] == "42"

    def test_success_false_propagates(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_llm_call
            track_llm_call(model="lem-simple", prompt_tokens=0, completion_tokens=0,
                           latency_ms=10, success=False)

        _, kwargs = mock_ph.capture.call_args
        assert kwargs["properties"]["success"] is False


class TestTrackTask:
    def test_captures_celery_task_event(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_task
            track_task(task_name="auto_check_scheduled_posts", duration_ms=200)

        mock_ph.capture.assert_called_once()
        _, kwargs = mock_ph.capture.call_args
        assert kwargs["event"] == "celery_task"
        props = kwargs["properties"]
        assert props["task"] == "auto_check_scheduled_posts"
        assert props["duration_ms"] == 200
        assert props["success"] is True

    def test_extra_kwargs_included_in_properties(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_task
            track_task(task_name="some_task", duration_ms=100, user_id=7, post_count=5)

        _, kwargs = mock_ph.capture.call_args
        props = kwargs["properties"]
        assert props["post_count"] == 5

    def test_uses_user_id_as_distinct_id(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_task
            track_task(task_name="some_task", duration_ms=50, user_id=99)

        _, kwargs = mock_ph.capture.call_args
        assert kwargs["distinct_id"] == "99"

    def test_system_distinct_id_when_no_user(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_task
            track_task(task_name="sys_task", duration_ms=10)

        _, kwargs = mock_ph.capture.call_args
        assert kwargs["distinct_id"] == "system"


class TestTrackApiCall:
    def test_captures_api_call_event(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_api_call
            track_api_call(route="/api/posts/", method="GET", status_code=200, latency_ms=30)

        mock_ph.capture.assert_called_once()
        _, kwargs = mock_ph.capture.call_args
        assert kwargs["event"] == "api_call"
        props = kwargs["properties"]
        assert props["route"] == "/api/posts/"
        assert props["method"] == "GET"
        assert props["status_code"] == 200
        assert props["latency_ms"] == 30

    def test_anonymous_distinct_id_when_no_user(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_api_call
            track_api_call(route="/api/health", method="GET", status_code=200, latency_ms=5)

        _, kwargs = mock_ph.capture.call_args
        assert kwargs["distinct_id"] == "anonymous"

    def test_user_id_used_as_distinct_id(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import track_api_call
            track_api_call(route="/api/posts/", method="POST", status_code=201, latency_ms=80, user_id=5)

        _, kwargs = mock_ph.capture.call_args
        assert kwargs["distinct_id"] == "5"


class TestLlmTrackedDecorator:
    def test_success_calls_track_with_success_true(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import llm_tracked

            @llm_tracked("lem-simple")
            def my_fn():
                return "result"

            out = my_fn()

        assert out == "result"
        mock_ph.capture.assert_called_once()
        _, kwargs = mock_ph.capture.call_args
        assert kwargs["event"] == "llm_call"
        assert kwargs["properties"]["success"] is True
        assert kwargs["properties"]["model"] == "lem-simple"

    def test_exception_calls_track_with_success_false_and_reraises(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import llm_tracked

            @llm_tracked("lem-complex")
            def failing_fn():
                raise ValueError("boom")

            with pytest.raises(ValueError, match="boom"):
                failing_fn()

        mock_ph.capture.assert_called_once()
        _, kwargs = mock_ph.capture.call_args
        assert kwargs["properties"]["success"] is False
        assert kwargs["properties"]["model"] == "lem-complex"

    def test_decorator_preserves_function_name(self):
        from cqc_lem.utilities.observability import llm_tracked

        @llm_tracked("lem-medium")
        def named_function():
            pass

        assert named_function.__name__ == "named_function"

    def test_latency_is_non_negative_integer(self):
        with patch(f"{_MOD}.posthog") as mock_ph:
            from cqc_lem.utilities.observability import llm_tracked

            @llm_tracked("lem-simple")
            def quick_fn():
                return 42

            quick_fn()

        _, kwargs = mock_ph.capture.call_args
        latency = kwargs["properties"]["latency_ms"]
        assert isinstance(latency, int)
        assert latency >= 0
