"""Unit tests for the LinkedIn 429 circuit breaker (rate_limit.py)."""

import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit

_MOD = "cqc_lem.utilities.linkedin.rate_limit"


@pytest.fixture
def fake_redis():
    client = MagicMock()
    with patch(f"{_MOD}._redis_client", return_value=client):
        yield client


class TestCooldownSeconds:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("LINKEDIN_RATE_LIMIT_COOLDOWN_SECONDS", raising=False)
        from cqc_lem.utilities.linkedin.rate_limit import _cooldown_seconds
        assert _cooldown_seconds() == 1800

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LINKEDIN_RATE_LIMIT_COOLDOWN_SECONDS", "60")
        from cqc_lem.utilities.linkedin.rate_limit import _cooldown_seconds
        assert _cooldown_seconds() == 60

    def test_bad_env_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("LINKEDIN_RATE_LIMIT_COOLDOWN_SECONDS", "not-a-number")
        from cqc_lem.utilities.linkedin.rate_limit import _cooldown_seconds
        assert _cooldown_seconds() == 1800


class TestMarkRateLimited:
    def test_sets_key_with_ttl(self, fake_redis, monkeypatch):
        monkeypatch.setenv("LINKEDIN_RATE_LIMIT_COOLDOWN_SECONDS", "120")
        from cqc_lem.utilities.linkedin.rate_limit import mark_rate_limited
        mark_rate_limited("boom")
        fake_redis.set.assert_called_once_with("linkedin:429_cooldown", "boom", ex=120)

    def test_defaults_reason(self, fake_redis):
        from cqc_lem.utilities.linkedin.rate_limit import mark_rate_limited
        mark_rate_limited()
        _, kwargs = fake_redis.set.call_args
        args = fake_redis.set.call_args.args
        assert args[1] == "429"

    def test_no_redis_is_noop(self):
        with patch(f"{_MOD}._redis_client", return_value=None):
            from cqc_lem.utilities.linkedin.rate_limit import mark_rate_limited
            mark_rate_limited("x")  # must not raise

    def test_redis_error_is_swallowed(self, fake_redis):
        fake_redis.set.side_effect = RuntimeError("connection lost")
        from cqc_lem.utilities.linkedin.rate_limit import mark_rate_limited
        mark_rate_limited("x")  # must not raise


class TestCooldownRemaining:
    def test_returns_positive_ttl(self, fake_redis):
        fake_redis.ttl.return_value = 42
        from cqc_lem.utilities.linkedin.rate_limit import rate_limit_cooldown_remaining
        assert rate_limit_cooldown_remaining() == 42

    def test_zero_when_key_absent(self, fake_redis):
        fake_redis.ttl.return_value = -2  # redis: key does not exist
        from cqc_lem.utilities.linkedin.rate_limit import rate_limit_cooldown_remaining
        assert rate_limit_cooldown_remaining() == 0

    def test_zero_when_no_redis(self):
        with patch(f"{_MOD}._redis_client", return_value=None):
            from cqc_lem.utilities.linkedin.rate_limit import rate_limit_cooldown_remaining
            assert rate_limit_cooldown_remaining() == 0

    def test_zero_on_redis_error(self, fake_redis):
        fake_redis.ttl.side_effect = RuntimeError("down")
        from cqc_lem.utilities.linkedin.rate_limit import rate_limit_cooldown_remaining
        assert rate_limit_cooldown_remaining() == 0


class TestClearRateLimit:
    def test_deletes_key(self, fake_redis):
        from cqc_lem.utilities.linkedin.rate_limit import clear_rate_limit
        clear_rate_limit()
        fake_redis.delete.assert_called_once_with("linkedin:429_cooldown")

    def test_no_redis_is_noop(self):
        with patch(f"{_MOD}._redis_client", return_value=None):
            from cqc_lem.utilities.linkedin.rate_limit import clear_rate_limit
            clear_rate_limit()  # must not raise

    def test_error_swallowed(self, fake_redis):
        fake_redis.delete.side_effect = RuntimeError("down")
        from cqc_lem.utilities.linkedin.rate_limit import clear_rate_limit
        clear_rate_limit()  # must not raise


class TestRedisClientSelection:
    def test_prefers_redis_broker_url(self, monkeypatch):
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/0")
        fake = MagicMock()
        with patch.dict("sys.modules", {"redis": MagicMock(Redis=MagicMock(from_url=MagicMock(return_value=fake)))}):
            import importlib
            mod = importlib.import_module(_MOD)
            client = mod._redis_client()
        assert client is fake

    def test_falls_back_to_result_backend_when_broker_is_sqs(self, monkeypatch):
        monkeypatch.setenv("CELERY_BROKER_URL", "sqs://")
        monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://cache:6379/1")
        captured = {}

        def _from_url(url, **kw):
            captured["url"] = url
            return MagicMock()

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=MagicMock(from_url=_from_url))}):
            import importlib
            mod = importlib.import_module(_MOD)
            mod._redis_client()
        assert captured["url"] == "redis://cache:6379/1"

    def test_returns_none_when_redis_missing(self, monkeypatch):
        with patch.dict("sys.modules", {"redis": None}):
            import importlib
            mod = importlib.import_module(_MOD)
            assert mod._redis_client() is None
