"""Unit tests for the /api/admin/test/* engagement test-run endpoints."""

import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def client():
    patches = [
        patch("cqc_lem.utilities.observability.track_api_call"),
        patch("cqc_lem.app.run_automation.automate_invites_to_company_page_for_user"),
        patch("cqc_lem.app.run_content_plan.auto_create_weekly_content"),
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


_SECRET = "s3cret"


def _async_result(task_id="task-123"):
    m = MagicMock()
    m.id = task_id
    return m


class TestComment:
    def test_forbidden_without_secret(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET):
            r = client.post("/api/admin/test/comment", json={"user_id": 1})
        assert r.status_code == 403

    def test_queues_task(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET), \
             patch("cqc_lem.api.main.automate_commenting.apply_async", return_value=_async_result()) as t:
            r = client.post("/api/admin/test/comment", json={"user_id": 7},
                            headers={"x-admin-secret": _SECRET})
        assert r.status_code == 200
        assert r.json()["detail"]["task_id"] == "task-123"
        assert t.call_args.kwargs["kwargs"]["user_id"] == 7


class TestReply:
    def test_404_when_post_user_missing(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET), \
             patch("cqc_lem.api.main.get_post_user_id", return_value=None):
            r = client.post("/api/admin/test/reply", json={"post_id": 99},
                            headers={"x-admin-secret": _SECRET})
        assert r.status_code == 404

    def test_queues_task(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET), \
             patch("cqc_lem.api.main.get_post_user_id", return_value=5), \
             patch("cqc_lem.api.main.automate_reply_commenting.apply_async", return_value=_async_result()) as t:
            r = client.post("/api/admin/test/reply", json={"post_id": 12},
                            headers={"x-admin-secret": _SECRET})
        assert r.status_code == 200
        assert t.call_args.kwargs["kwargs"]["post_id"] == 12
        assert r.json()["detail"]["user_id"] == 5


class TestDM:
    def test_forbidden_without_secret(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET):
            r = client.post("/api/admin/test/dm", json={"user_id": 1})
        assert r.status_code == 403

    def test_queues_appreciation_dm(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET), \
             patch("cqc_lem.api.main.automate_appreciation_dms_for_user.apply_async",
                   return_value=_async_result()) as t:
            r = client.post("/api/admin/test/dm", json={"user_id": 3},
                            headers={"x-admin-secret": _SECRET})
        assert r.status_code == 200
        assert t.call_args.kwargs["kwargs"]["user_id"] == 3


class TestDirectDM:
    def test_queues_direct_dm(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET), \
             patch("cqc_lem.api.main.send_private_dm.apply_async", return_value=_async_result()) as t:
            r = client.post("/api/admin/test/dm-direct",
                            json={"user_id": 1, "profile_url": "https://linkedin.com/in/x",
                                  "message": "Hi there"},
                            headers={"x-admin-secret": _SECRET})
        assert r.status_code == 200
        assert t.call_args.kwargs["kwargs"]["profile_url"] == "https://linkedin.com/in/x"
        assert t.call_args.kwargs["kwargs"]["message"] == "Hi there"

    def test_forbidden_without_secret(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET):
            r = client.post("/api/admin/test/dm-direct",
                            json={"user_id": 1, "profile_url": "u", "message": "m"})
        assert r.status_code == 403


class TestTaskStatus:
    def test_returns_state(self, client):
        res = MagicMock()
        res.state = "SUCCESS"
        res.ready.return_value = True
        res.result = "done"
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET), \
             patch("cqc_lem.app.my_celery.app.AsyncResult", return_value=res):
            r = client.get("/api/admin/task-status/task-123",
                           headers={"x-admin-secret": _SECRET})
        assert r.status_code == 200
        assert r.json()["detail"]["state"] == "SUCCESS"
        assert r.json()["detail"]["result"] == "done"

    def test_forbidden_without_secret(self, client):
        with patch("cqc_lem.api.main.ADMIN_SECRET", _SECRET):
            r = client.get("/api/admin/task-status/task-123")
        assert r.status_code == 403
