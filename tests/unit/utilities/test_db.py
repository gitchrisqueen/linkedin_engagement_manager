"""Unit tests for database utility functions."""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone


@pytest.mark.unit
class TestPostStatusEnum:
    def test_enum_values(self):
        from cqc_lem.utilities.db import PostStatus
        assert PostStatus.PLANNING == "planning"
        assert PostStatus.PENDING == "pending"
        assert PostStatus.APPROVED == "approved"
        assert PostStatus.REJECTED == "rejected"
        assert PostStatus.SCHEDULED == "scheduled"
        assert PostStatus.POSTED == "posted"

    def test_enum_is_string(self):
        from cqc_lem.utilities.db import PostStatus
        assert isinstance(PostStatus.PENDING.value, str)
        assert str(PostStatus.PENDING) == "pending"


@pytest.mark.unit
class TestPostTypeEnum:
    def test_enum_values(self):
        from cqc_lem.utilities.db import PostType
        assert PostType.TEXT == "text"
        assert PostType.CAROUSEL == "carousel"
        assert PostType.VIDEO == "video"


@pytest.mark.unit
class TestLogActionTypeEnum:
    def test_enum_values(self):
        from cqc_lem.utilities.db import LogActionType
        assert LogActionType.COMMENT == "comment"
        assert LogActionType.DM == "dm"
        assert LogActionType.POST == "post"
        assert LogActionType.ENGAGED == "engaged"


@pytest.mark.unit
class TestUpdateDbPostStatus:
    def test_executes_correct_sql(self, mock_database_connection):
        from cqc_lem.utilities.db import update_db_post_status, PostStatus

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].rowcount = 1

            result = update_db_post_status(19, PostStatus.APPROVED)

            assert result is True
            args = mock_database_connection["cursor"].execute.call_args[0]
            assert "UPDATE" in args[0].upper()
            assert PostStatus.APPROVED.value in args[1]
            assert 19 in args[1]
            mock_database_connection["connection"].commit.assert_called_once()

    def test_returns_false_on_db_error(self, mock_database_connection):
        from cqc_lem.utilities.db import update_db_post_status, PostStatus
        import mysql.connector

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].execute.side_effect = mysql.connector.Error("DB error")

            result = update_db_post_status(19, PostStatus.APPROVED)

            assert result is False


@pytest.mark.unit
class TestUpdateDbPostContent:
    def test_executes_update_with_content(self, mock_database_connection):
        from cqc_lem.utilities.db import update_db_post_content

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].rowcount = 1

            result = update_db_post_content(19, "New content here")

            assert result is True
            args = mock_database_connection["cursor"].execute.call_args[0]
            assert "New content here" in args[1]
            assert 19 in args[1]

    def test_returns_false_on_db_error(self, mock_database_connection):
        from cqc_lem.utilities.db import update_db_post_content
        import mysql.connector

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].execute.side_effect = mysql.connector.Error("err")

            assert update_db_post_content(19, "content") is False


@pytest.mark.unit
class TestUpdateDbPostVideoUrl:
    def test_executes_update_with_url(self, mock_database_connection):
        from cqc_lem.utilities.db import update_db_post_video_url

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].rowcount = 1

            result = update_db_post_video_url(19, "https://example.com/video.mp4")

            assert result is True
            args = mock_database_connection["cursor"].execute.call_args[0]
            assert "https://example.com/video.mp4" in args[1]
            assert 19 in args[1]


@pytest.mark.unit
class TestGetPosts:
    def test_returns_list_from_cursor(self, mock_database_connection):
        from cqc_lem.utilities.db import get_posts

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].fetchall.return_value = [
                (1, 60, "Test content", "pending", None, "2024-01-01 12:00:00", "text", None)
            ]
            mock_database_connection["cursor"].description = [
                ("id",), ("user_id",), ("content",), ("status",),
                ("video_url",), ("scheduled_time",), ("post_type",), ("media_url",)
            ]

            posts = get_posts(60)

            assert mock_database_connection["cursor"].execute.called
            assert isinstance(posts, list)

    def test_query_filters_by_user_id(self, mock_database_connection):
        from cqc_lem.utilities.db import get_posts

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].fetchall.return_value = []
            mock_database_connection["cursor"].description = []

            get_posts(42)

            execute_args = mock_database_connection["cursor"].execute.call_args[0]
            assert 42 in execute_args[1]


@pytest.mark.unit
class TestInsertPost:
    def test_inserts_post_and_returns_true(self, mock_database_connection):
        from cqc_lem.utilities.db import insert_post, PostType

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn, \
             patch("cqc_lem.utilities.db.get_user_id") as mock_get_user:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_get_user.return_value = 60
            mock_database_connection["cursor"].rowcount = 1

            result = insert_post(
                "test@example.com",
                "Test content",
                datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                PostType.TEXT,
            )

            assert result is True
            assert mock_database_connection["cursor"].execute.called
            mock_database_connection["connection"].commit.assert_called_once()

    def test_returns_false_when_user_not_found(self, mock_database_connection):
        from cqc_lem.utilities.db import insert_post, PostType

        with patch("cqc_lem.utilities.db.get_user_id") as mock_get_user:
            mock_get_user.return_value = None

            result = insert_post(
                "unknown@example.com",
                "content",
                datetime.now(tz=timezone.utc),
                PostType.TEXT,
            )

            assert result is False


@pytest.mark.unit
class TestGetUserId:
    def test_returns_user_id_for_known_email(self, mock_database_connection):
        from cqc_lem.utilities.db import get_user_id

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].fetchone.return_value = (42,)

            result = get_user_id("test@example.com")

            assert result == 42

    def test_returns_none_for_unknown_email(self, mock_database_connection):
        from cqc_lem.utilities.db import get_user_id

        with patch("cqc_lem.utilities.db.get_db_connection") as mock_conn:
            mock_conn.return_value = mock_database_connection["connection"]
            mock_database_connection["cursor"].fetchone.return_value = None

            result = get_user_id("nobody@example.com")

            assert result is None
