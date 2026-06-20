"""Unit tests for GET /api/post_url/ endpoint."""

import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit

_DB = "cqc_lem.api.main"


@pytest.fixture(scope="module")
def client():
    patches = [
        patch("cqc_lem.utilities.observability.track_api_call"),
        patch("cqc_lem.app.run_automation.automate_invites_to_company_page_for_user"),
        patch("cqc_lem.app.run_automation.automate_reply_commenting"),
        patch("cqc_lem.app.run_content_plan.auto_create_weekly_content"),
        patch("cqc_lem.app.aws_test_celery_task.test_get_my_profile"),
    ]
    for p in patches:
        p.start()
    try:
        from fastapi.testclient import TestClient
        from cqc_lem.api.main import app
        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc
    finally:
        for p in patches:
            p.stop()


_URL = "/api/post_url/"
_USER_ID = 60
_POST_ID = 42
_EMAIL = "test@example.com"
_LI_URL = "https://www.linkedin.com/feed/update/urn:li:ugcPost:123/"


class TestGetPostUrl:
    def test_missing_email_returns_422(self, client):
        """FastAPI rejects the request before the function body when email is absent."""
        resp = client.get(_URL, params={"post_id": _POST_ID})
        assert resp.status_code == 422

    def test_empty_email_string_returns_400(self, client):
        """Empty email passes FastAPI validation but is caught by application guard."""
        resp = client.get(_URL, params={"post_id": _POST_ID, "email": ""})
        assert resp.status_code == 400

    def test_missing_post_id_returns_422(self, client):
        resp = client.get(_URL, params={"email": _EMAIL})
        assert resp.status_code == 422

    def test_unknown_user_returns_403(self, client):
        with patch(f"{_DB}.get_user_id", return_value=None):
            resp = client.get(_URL, params={"post_id": _POST_ID, "email": _EMAIL})
        assert resp.status_code == 403

    def test_returns_linkedin_url_when_found(self, client):
        with patch(f"{_DB}.get_user_id", return_value=_USER_ID), \
             patch(f"{_DB}.get_post_url_from_log_for_user", return_value=_LI_URL):
            resp = client.get(_URL, params={"post_id": _POST_ID, "email": _EMAIL})
        assert resp.status_code == 200
        assert resp.json()["detail"]["post_url"] == _LI_URL

    def test_returns_null_when_no_log_url_exists(self, client):
        with patch(f"{_DB}.get_user_id", return_value=_USER_ID), \
             patch(f"{_DB}.get_post_url_from_log_for_user", return_value=None):
            resp = client.get(_URL, params={"post_id": _POST_ID, "email": _EMAIL})
        assert resp.status_code == 200
        assert resp.json()["detail"]["post_url"] is None

    def test_calls_correct_user_and_post_id(self, client):
        """Verifies get_post_url_from_log_for_user is called with resolved user_id, not email."""
        with patch(f"{_DB}.get_user_id", return_value=_USER_ID) as mock_uid, \
             patch(f"{_DB}.get_post_url_from_log_for_user", return_value=None) as mock_url:
            client.get(_URL, params={"post_id": _POST_ID, "email": _EMAIL})
        mock_uid.assert_called_once_with(_EMAIL)
        mock_url.assert_called_once_with(_USER_ID, _POST_ID)
