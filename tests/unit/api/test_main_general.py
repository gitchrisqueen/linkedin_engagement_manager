"""Unit tests for general FastAPI endpoints in cqc_lem.api.main."""

import pytest
from unittest.mock import patch
from datetime import datetime

pytestmark = pytest.mark.unit

_MAIN = "cqc_lem.api.main"


@pytest.fixture(scope="module")
def client():
    """TestClient with all heavy module-level imports pre-mocked."""
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


# ---------------------------------------------------------------------------
# GET /api/dashboard/stats/
# ---------------------------------------------------------------------------

class TestDashboardStats:
    BASE = "/api/dashboard/stats/"

    def test_missing_email_param_returns_422(self, client):
        resp = client.get(self.BASE)
        assert resp.status_code == 422

    def test_empty_email_returns_400(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=None):
            resp = client.get(self.BASE, params={"email": ""})
        assert resp.status_code == 400

    def test_unknown_user_returns_403(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=None):
            resp = client.get(self.BASE, params={"email": "ghost@example.com"})
        assert resp.status_code == 403

    def test_known_user_with_no_posts_returns_zeros(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=1), \
             patch(f"{_MAIN}.get_posts", return_value=([], 0)):
            resp = client.get(self.BASE, params={"email": "user@example.com"})
        assert resp.status_code == 200
        detail = resp.json()["detail"]
        assert detail["scheduled_this_week"] == 0
        assert detail["pending_review"] == 0
        assert detail["posted_total"] == 0

    def test_start_of_month_does_not_crash(self, client):
        # Regression: week_start was computed with replace(day=day-weekday()), which
        # goes out of range in the first days of a month (Wed the 1st → day=-1 → 500).
        class _FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 7, 1, tzinfo=tz)  # Wednesday the 1st

        with patch(f"{_MAIN}.get_user_id", return_value=1), \
             patch(f"{_MAIN}.get_posts", return_value=([], 0)), \
             patch(f"{_MAIN}.datetime", _FixedDatetime):
            resp = client.get(self.BASE, params={"email": "user@example.com"})
        assert resp.status_code == 200

    def test_posted_total_counted_correctly(self, client):
        from cqc_lem.utilities.db import PostStatus
        posts = [
            {"status": PostStatus.POSTED, "scheduled_time": None},
            {"status": PostStatus.POSTED, "scheduled_time": None},
            {"status": PostStatus.PENDING, "scheduled_time": None},
        ]
        with patch(f"{_MAIN}.get_user_id", return_value=1), \
             patch(f"{_MAIN}.get_posts", return_value=(posts, 3)):
            resp = client.get(self.BASE, params={"email": "user@example.com"})
        assert resp.status_code == 200
        detail = resp.json()["detail"]
        assert detail["posted_total"] == 2
        assert detail["pending_review"] == 1


# ---------------------------------------------------------------------------
# GET /api/activity/
# ---------------------------------------------------------------------------

class TestGetActivity:
    BASE = "/api/activity/"

    def test_missing_email_returns_422(self, client):
        resp = client.get(self.BASE)
        assert resp.status_code == 422

    def test_unknown_user_returns_403(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=None):
            resp = client.get(self.BASE, params={"email": "nobody@example.com"})
        assert resp.status_code == 403

    def test_valid_user_returns_200_with_list(self, client):
        log_row = {
            "id": 1,
            "action_type": "POST",
            "result": "success",
            "post_id": 10,
            "post_url": "https://linkedin.com/p/123",
            "message": "Posted OK",
            "created_at": datetime(2024, 1, 15, 12, 0, 0),
        }
        with patch(f"{_MAIN}.get_user_id", return_value=5), \
             patch(f"{_MAIN}.get_recent_logs", return_value=[log_row]):
            resp = client.get(self.BASE, params={"email": "user@example.com"})
        assert resp.status_code == 200
        detail = resp.json()["detail"]
        assert isinstance(detail, list)
        assert len(detail) == 1
        assert detail[0]["id"] == 1
        assert detail[0]["action_type"] == "POST"

    def test_empty_log_list_returns_empty_array(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=5), \
             patch(f"{_MAIN}.get_recent_logs", return_value=[]):
            resp = client.get(self.BASE, params={"email": "user@example.com"})
        assert resp.status_code == 200
        assert resp.json()["detail"] == []


# ---------------------------------------------------------------------------
# PUT /api/user/
# ---------------------------------------------------------------------------

class TestUpdateUser:
    BASE = "/api/user/"

    def test_empty_email_returns_400(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=None):
            resp = client.put(self.BASE, json={"email": ""})
        assert resp.status_code == 400

    def test_unknown_user_returns_403(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=None):
            resp = client.put(self.BASE, json={"email": "unknown@example.com"})
        assert resp.status_code == 403

    def test_no_update_fields_returns_unchanged(self, client):
        # email present but no new_email/blog_url/sitemap_url
        with patch(f"{_MAIN}.get_user_id", return_value=3):
            resp = client.put(self.BASE, json={"email": "user@example.com"})
        assert resp.status_code == 200
        assert "unchanged" in resp.json()["detail"]

    def test_valid_update_returns_200(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=3), \
             patch(f"{_MAIN}.update_user", return_value=True):
            resp = client.put(self.BASE, json={"email": "user@example.com", "blog_url": "https://blog.example.com"})
        assert resp.status_code == 200
        assert "updated" in resp.json()["detail"]

    def test_update_user_returns_false_gives_404(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=3), \
             patch(f"{_MAIN}.update_user", return_value=False):
            resp = client.put(self.BASE, json={"email": "user@example.com", "blog_url": "https://blog.example.com"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/user_id/
# ---------------------------------------------------------------------------

class TestGetUserIdEndpoint:
    BASE = "/api/user_id/"

    def test_missing_email_returns_422(self, client):
        resp = client.get(self.BASE)
        assert resp.status_code == 422

    def test_empty_email_returns_400(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=None):
            resp = client.get(self.BASE, params={"email": ""})
        assert resp.status_code == 400

    def test_unknown_user_returns_403(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=None):
            resp = client.get(self.BASE, params={"email": "ghost@example.com"})
        assert resp.status_code == 403

    def test_valid_email_returns_user_id(self, client):
        with patch(f"{_MAIN}.get_user_id", return_value=42):
            resp = client.get(self.BASE, params={"email": "user@example.com"})
        assert resp.status_code == 200
        assert resp.json()["detail"] == 42


# ---------------------------------------------------------------------------
# GET /api/auth/session
# ---------------------------------------------------------------------------

class TestAuthCheckSession:
    BASE = "/api/auth/session"

    def test_invalid_session_token_returns_401(self, client):
        with patch(f"{_MAIN}.get_session_user_id", return_value=None):
            resp = client.get(self.BASE, params={"session_token": "bad-token"})
        assert resp.status_code == 401

    def test_valid_session_returns_user_id_and_email(self, client):
        with patch(f"{_MAIN}.get_session_user_id", return_value=7), \
             patch(f"{_MAIN}.get_user_email", return_value="me@example.com"):
            resp = client.get(self.BASE, params={"session_token": "valid-token-abc"})
        assert resp.status_code == 200
        detail = resp.json()["detail"]
        assert detail["user_id"] == 7
        assert detail["email"] == "me@example.com"


# ---------------------------------------------------------------------------
# GET /api/user/settings
# ---------------------------------------------------------------------------

class TestGetUserSettings:
    BASE = "/api/user/settings"

    def test_invalid_session_returns_401(self, client):
        with patch(f"{_MAIN}.get_session_user_id", return_value=None):
            resp = client.get(self.BASE, params={"session_token": "bad-token"})
        assert resp.status_code == 401

    def test_valid_session_returns_subscription_and_preferences(self, client):
        from datetime import datetime
        sub = {
            "subscription_status": "active",
            "subscription_tier": "starter",
            "trial_started_at": None,
            "trial_ends_at": None,
            "stripe_customer_id": "cus_abc",
        }
        prefs = {
            "last_login_inactivate_delay": 90,
            "auto_schedule_posts": False,
        }
        with patch(f"{_MAIN}.get_session_user_id", return_value=5), \
             patch(f"{_MAIN}.get_user_subscription_info", return_value=sub), \
             patch(f"{_MAIN}.get_user_preferences", return_value=prefs), \
             patch(f"{_MAIN}.get_user_blog_url", return_value="https://blog.example.com"), \
             patch(f"{_MAIN}.get_user_sitemap_url", return_value="https://blog.example.com/sitemap.xml"), \
             patch(f"{_MAIN}.get_company_linked_in_url_for_user", return_value=None):
            resp = client.get(self.BASE, params={"session_token": "valid-tok"})
        assert resp.status_code == 200
        detail = resp.json()["detail"]
        assert detail["subscription"]["status"] == "active"
        assert detail["subscription"]["tier"] == "starter"
        assert detail["preferences"]["last_login_inactivate_delay"] == 90
        assert detail["blog_url"] == "https://blog.example.com"
        assert detail["sitemap_url"] == "https://blog.example.com/sitemap.xml"

    def test_none_subscription_returns_null_subscription(self, client):
        with patch(f"{_MAIN}.get_session_user_id", return_value=5), \
             patch(f"{_MAIN}.get_user_subscription_info", return_value=None), \
             patch(f"{_MAIN}.get_user_preferences", return_value=None), \
             patch(f"{_MAIN}.get_user_blog_url", return_value=None), \
             patch(f"{_MAIN}.get_user_sitemap_url", return_value=None), \
             patch(f"{_MAIN}.get_company_linked_in_url_for_user", return_value=None):
            resp = client.get(self.BASE, params={"session_token": "valid-tok"})
        assert resp.status_code == 200
        detail = resp.json()["detail"]
        assert detail["subscription"] is None
        assert detail["preferences"] is None
