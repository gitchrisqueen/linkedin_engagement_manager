from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from cqc_lem.utilities.linkedin.token_refresh import (
    attempt_token_refresh,
    get_token_expiry,
    is_token_expired,
    is_token_expiring_soon,
)


def make_token_info(
    seconds_until_expiry: int,
    refresh_token: str | None = None,
    refresh_seconds_remaining: int = 60 * 60 * 24 * 60,
):
    now = datetime.now(timezone.utc)
    info: dict = {
        'access_token': 'tok_abc',
        'access_token_created_at': now,
        'access_token_expires_in': seconds_until_expiry,
        'refresh_token': refresh_token,
        'refresh_token_created_at': now if refresh_token else None,
        'refresh_token_expires_in': refresh_seconds_remaining if refresh_token else None,
    }
    return info


class TestGetTokenExpiry:
    def test_returns_correct_expiry(self):
        now = datetime.now(timezone.utc)
        info = {'access_token_created_at': now, 'access_token_expires_in': 3600}
        expiry = get_token_expiry(info)
        delta = abs((expiry - (now + timedelta(seconds=3600))).total_seconds())
        assert delta < 1

    def test_returns_none_when_missing_fields(self):
        assert get_token_expiry({'access_token_created_at': None, 'access_token_expires_in': None}) is None
        assert get_token_expiry({}) is None

    def test_handles_naive_datetime(self):
        naive = datetime.now(timezone.utc).replace(tzinfo=None)
        info = {'access_token_created_at': naive, 'access_token_expires_in': 3600}
        expiry = get_token_expiry(info)
        assert expiry is not None


class TestIsTokenExpired:
    def test_fresh_token_not_expired(self):
        info = make_token_info(seconds_until_expiry=3600)
        assert not is_token_expired(info)

    def test_expired_token(self):
        info = make_token_info(seconds_until_expiry=-1)
        assert is_token_expired(info)

    def test_none_expiry_treated_as_expired(self):
        assert is_token_expired({})


class TestIsTokenExpiringSoon:
    def test_60_days_not_expiring_soon(self):
        info = make_token_info(seconds_until_expiry=60 * 24 * 3600)
        assert not is_token_expiring_soon(info)

    def test_15_days_is_expiring_soon(self):
        info = make_token_info(seconds_until_expiry=15 * 24 * 3600)
        assert is_token_expiring_soon(info)

    def test_custom_days_threshold(self):
        info = make_token_info(seconds_until_expiry=45 * 24 * 3600)
        assert not is_token_expiring_soon(info, days=30)
        assert is_token_expiring_soon(info, days=60)

    def test_none_treated_as_expiring_soon(self):
        assert is_token_expiring_soon({})


class TestAttemptTokenRefresh:
    # The DB functions are imported inside attempt_token_refresh to avoid circular
    # imports, so we patch them at their source module (cqc_lem.utilities.db).

    @patch('cqc_lem.utilities.linkedin.token_refresh.requests.post')
    @patch('cqc_lem.utilities.db.update_user_access_token')
    @patch('cqc_lem.utilities.db.get_user_token_info')
    def test_successful_refresh(self, mock_get_info, mock_update, mock_post):
        mock_get_info.return_value = make_token_info(
            seconds_until_expiry=3600, refresh_token='refresh_tok'
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'access_token': 'new_tok',
            'expires_in': 7200,
            'refresh_token': 'new_refresh',
            'refresh_token_expires_in': 60 * 24 * 3600,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        success, token = attempt_token_refresh(user_id=1)
        assert success is True
        assert token == 'new_tok'
        mock_update.assert_called_once()

    @patch('cqc_lem.utilities.db.get_user_token_info')
    def test_no_refresh_token_returns_false(self, mock_get_info):
        mock_get_info.return_value = make_token_info(
            seconds_until_expiry=3600, refresh_token=None
        )
        success, token = attempt_token_refresh(user_id=1)
        assert success is False
        assert token is None

    @patch('cqc_lem.utilities.db.get_user_token_info')
    def test_no_token_info_returns_false(self, mock_get_info):
        mock_get_info.return_value = None
        success, token = attempt_token_refresh(user_id=1)
        assert success is False

    @patch('cqc_lem.utilities.linkedin.token_refresh.requests.post')
    @patch('cqc_lem.utilities.db.get_user_token_info')
    def test_network_error_returns_false(self, mock_get_info, mock_post):
        import requests as req
        mock_get_info.return_value = make_token_info(
            seconds_until_expiry=3600, refresh_token='refresh_tok'
        )
        mock_post.side_effect = req.RequestException("timeout")
        success, token = attempt_token_refresh(user_id=1)
        assert success is False
        assert token is None

    @patch('cqc_lem.utilities.db.get_user_token_info')
    def test_expired_refresh_token_returns_false(self, mock_get_info):
        now = datetime.now(timezone.utc)
        mock_get_info.return_value = {
            'access_token': 'tok',
            'access_token_created_at': now,
            'access_token_expires_in': 3600,
            'refresh_token': 'expired_refresh',
            'refresh_token_created_at': now - timedelta(days=90),
            'refresh_token_expires_in': 60 * 24 * 3600,  # 60 days, but created 90 days ago
        }
        success, token = attempt_token_refresh(user_id=1)
        assert success is False
