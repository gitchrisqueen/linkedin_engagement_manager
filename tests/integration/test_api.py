"""Integration tests for FastAPI endpoints."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.integration
class TestHealthEndpoint:
    def test_health_returns_200(self):
        with patch("cqc_lem.utilities.observability.posthog"):
            from fastapi.testclient import TestClient
            from cqc_lem.api.main import app

            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            assert response.json()["status"] == "healthy"


@pytest.mark.integration
class TestSchedulePostEndpoint:
    def test_schedule_post_returns_200_for_known_user(self):
        with patch("cqc_lem.utilities.observability.posthog"), \
             patch("cqc_lem.utilities.db.get_user_id") as mock_user, \
             patch("cqc_lem.utilities.db.insert_post") as mock_insert:
            from fastapi.testclient import TestClient
            from cqc_lem.api.main import app

            mock_user.return_value = 1
            mock_insert.return_value = True

            client = TestClient(app)
            response = client.post("/schedule_post/", json={
                "email": "test@example.com",
                "content": "Test post content",
                "scheduled_datetime": "2025-06-01T12:00:00",
                "post_type": "text",
                "status": "pending",
            })

            assert response.status_code == 200
            assert response.json()["status_code"] == 200

    def test_schedule_post_returns_403_for_unknown_user(self):
        with patch("cqc_lem.utilities.observability.posthog"), \
             patch("cqc_lem.utilities.db.get_user_id") as mock_user:
            from fastapi.testclient import TestClient
            from cqc_lem.api.main import app

            mock_user.return_value = None

            client = TestClient(app)
            response = client.post("/schedule_post/", json={
                "email": "nobody@example.com",
                "content": "Test post",
                "scheduled_datetime": "2025-06-01T12:00:00",
                "post_type": "text",
                "status": "pending",
            })

            assert response.status_code == 403


@pytest.mark.integration
class TestGetPostsEndpoint:
    def test_get_posts_returns_200_with_posts(self):
        with patch("cqc_lem.utilities.observability.posthog"), \
             patch("cqc_lem.utilities.db.get_user_id") as mock_user, \
             patch("cqc_lem.utilities.db.get_post_by_email") as mock_posts:
            from fastapi.testclient import TestClient
            from cqc_lem.api.main import app

            mock_user.return_value = 1
            mock_posts.return_value = [
                {
                    "id": 1, "content": "Hello world", "video_url": None,
                    "scheduled_time": "2025-01-01T12:00:00", "post_type": "text", "status": "pending"
                }
            ]

            client = TestClient(app)
            response = client.get("/posts/?email=test@example.com")

            assert response.status_code == 200
            body = response.json()
            assert body["status_code"] == 200
            assert len(body["detail"]) == 1

    def test_get_posts_returns_404_when_no_posts(self):
        with patch("cqc_lem.utilities.observability.posthog"), \
             patch("cqc_lem.utilities.db.get_post_by_email") as mock_posts:
            from fastapi.testclient import TestClient
            from cqc_lem.api.main import app

            mock_posts.return_value = []

            client = TestClient(app)
            response = client.get("/posts/?email=test@example.com")

            assert response.status_code == 404

    def test_get_posts_returns_400_without_email(self):
        with patch("cqc_lem.utilities.observability.posthog"):
            from fastapi.testclient import TestClient
            from cqc_lem.api.main import app

            client = TestClient(app)
            response = client.get("/posts/")

            assert response.status_code == 422


@pytest.mark.integration
class TestUpdatePostEndpoint:
    def test_update_post_returns_200(self):
        with patch("cqc_lem.utilities.observability.posthog"), \
             patch("cqc_lem.utilities.db.update_db_post") as mock_update, \
             patch("cqc_lem.utilities.db.get_user_id") as mock_user:
            from fastapi.testclient import TestClient
            from cqc_lem.api.main import app

            mock_update.return_value = True
            mock_user.return_value = 1

            client = TestClient(app)
            response = client.post("/update_post/?post_id=1", json={
                "email": "test@example.com",
                "content": "Updated content",
                "scheduled_datetime": "2025-06-01T12:00:00",
                "post_type": "text",
                "status": "approved",
            })

            assert response.status_code == 200
