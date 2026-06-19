from unittest.mock import patch, MagicMock

import pytest


class TestAutoCreateWeeklyContent:
    """Tests for auto_create_weekly_content — verifies None/empty guards and content-None skip."""

    @patch('cqc_lem.app.run_content_plan.get_planned_posts_for_next_week', return_value=None)
    @patch('cqc_lem.app.run_content_plan.get_planned_posts_for_current_week', return_value=None)
    def test_does_not_crash_when_planned_posts_is_none(self, mock_current, mock_next):
        from cqc_lem.app.run_content_plan import auto_create_weekly_content
        # Should not raise TypeError: 'NoneType' is not iterable
        auto_create_weekly_content(user_id=1)

    @patch('cqc_lem.app.run_content_plan.get_planned_posts_for_current_week', return_value=[])
    def test_does_not_crash_when_planned_posts_is_empty(self, mock_current):
        from cqc_lem.app.run_content_plan import auto_create_weekly_content
        auto_create_weekly_content(user_id=1)

    @patch('cqc_lem.app.run_content_plan.update_db_post_status')
    @patch('cqc_lem.app.run_content_plan.update_db_post_content')
    @patch('cqc_lem.app.run_content_plan.create_content', return_value=(None, None))
    @patch('cqc_lem.app.run_content_plan.get_planned_posts_for_current_week')
    def test_skips_post_when_content_is_none(
        self, mock_current, mock_create, mock_update_content, mock_update_status
    ):
        from cqc_lem.app.run_content_plan import auto_create_weekly_content
        mock_current.return_value = [
            {'user_id': 1, 'id': 42, 'post_type': 'text', 'buyer_stage': 'awareness'}
        ]
        auto_create_weekly_content(user_id=1)
        mock_update_content.assert_not_called()
        mock_update_status.assert_not_called()

    @patch('cqc_lem.app.run_content_plan.get_user_preferences', return_value={'auto_schedule_posts': 0})
    @patch('cqc_lem.app.run_content_plan.update_db_post_status')
    @patch('cqc_lem.app.run_content_plan.update_db_post_content')
    @patch('cqc_lem.app.run_content_plan.create_content', return_value=('Great post content', None))
    @patch('cqc_lem.app.run_content_plan.get_planned_posts_for_current_week')
    def test_updates_db_when_content_is_valid(
        self, mock_current, mock_create, mock_update_content, mock_update_status, mock_prefs
    ):
        from cqc_lem.app.run_content_plan import auto_create_weekly_content
        mock_current.return_value = [
            {'user_id': 1, 'id': 42, 'post_type': 'text', 'buyer_stage': 'awareness'}
        ]
        auto_create_weekly_content(user_id=1)
        mock_update_content.assert_called_once_with(42, 'Great post content')
        mock_update_status.assert_called_once()

    @patch('cqc_lem.app.run_content_plan.get_user_preferences', return_value={'auto_schedule_posts': 0})
    @patch('cqc_lem.app.run_content_plan.update_db_post_status')
    @patch('cqc_lem.app.run_content_plan.update_db_post_content')
    @patch('cqc_lem.app.run_content_plan.create_content', return_value=('Auto-off content', None))
    @patch('cqc_lem.app.run_content_plan.get_planned_posts_for_current_week')
    def test_status_is_pending_when_auto_schedule_off(
        self, mock_current, mock_create, mock_update_content, mock_update_status, mock_prefs
    ):
        from cqc_lem.app.run_content_plan import auto_create_weekly_content
        from cqc_lem.utilities.db import PostStatus
        mock_current.return_value = [
            {'user_id': 1, 'id': 55, 'post_type': 'text', 'buyer_stage': 'awareness'}
        ]
        auto_create_weekly_content(user_id=1)
        mock_update_status.assert_called_once_with(55, PostStatus.PENDING)

    @patch('cqc_lem.app.run_content_plan.get_user_preferences', return_value={'auto_schedule_posts': 1})
    @patch('cqc_lem.app.run_content_plan.update_db_post_status')
    @patch('cqc_lem.app.run_content_plan.update_db_post_content')
    @patch('cqc_lem.app.run_content_plan.create_content', return_value=('Auto-on content', None))
    @patch('cqc_lem.app.run_content_plan.get_planned_posts_for_current_week')
    def test_status_is_approved_when_auto_schedule_on(
        self, mock_current, mock_create, mock_update_content, mock_update_status, mock_prefs
    ):
        from cqc_lem.app.run_content_plan import auto_create_weekly_content
        from cqc_lem.utilities.db import PostStatus
        mock_current.return_value = [
            {'user_id': 2, 'id': 77, 'post_type': 'text', 'buyer_stage': 'decision'}
        ]
        auto_create_weekly_content(user_id=2)
        mock_update_status.assert_called_once_with(77, PostStatus.APPROVED)
