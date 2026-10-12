"""A free trial that ends without a paid plan stops generation and publishing (issue #2380).

Each test drives the REAL `trial_lapsed` predicate and mocks only the subscription read beneath it,
so what is proven is the wiring from `users.trial_ends_at` to the gate, not a stubbed boolean.
"""

from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

_READ = "cqc_lem.utilities.trial_access.get_user_subscription_info"
_RCP = "cqc_lem.app.run_content_plan"
_SCHED = "cqc_lem.app.run_scheduler"
_POSTING = "cqc_lem.app.engagement.posting"


def _ended() -> dict:
    return {"subscription_status": "trial",
            "trial_ends_at": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)}


def _running() -> dict:
    return {"subscription_status": "trial",
            "trial_ends_at": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)}


# --- generation ------------------------------------------------------------------------------

def _run_top_up(subscription: dict) -> dict:
    """Run the requested buffer top-up for user 1 with every DB/AI seam mocked."""
    from cqc_lem.app.run_content_plan import auto_create_weekly_content

    targets = {
        "ai_generation_paused": {"return_value": False},
        "acquire_run_lock": {"return_value": "tok"},
        "release_run_lock": {},
        "count_ready_posts_within_buffer": {"return_value": 0},
        "get_planned_posts_within_buffer": {"return_value": [
            {"user_id": 1, "id": 11, "post_type": "text", "buyer_stage": "awareness"}]},
        "get_next_planned_posts_after_buffer": {"return_value": []},
        "get_next_planned_post_date": {"return_value": None},
        "create_content": {"return_value": ("Post text", None)},
        "update_db_post_content": {},
        "update_db_post_status": {},
        "get_user_preferences": {"return_value": {"auto_schedule_posts": True}},
        "_post_missing_required_asset": {"return_value": False},
        "get_post_authenticity_score": {"return_value": None},
        "_score_and_persist_dwell": {},
        "mark_in_progress": {},
        "mark_finished": {},
        "mark_empty": {},
        "record_post_generated": {},
        "record_post_failed": {},
        "notify_content_generation_ready": {},
    }
    with ExitStack() as stack:
        mocks = {name: stack.enter_context(patch(f"{_RCP}.{name}", **kw))
                 for name, kw in targets.items()}
        stack.enter_context(patch(_READ, return_value=subscription))
        auto_create_weekly_content(user_id=1)
    return mocks


class TestGenerationStopsAtTrialEnd:
    def test_ended_trial_generates_nothing_and_says_why(self):
        from cqc_lem.utilities.content_generation_status import ContentGenerationEmptyReason
        mocks = _run_top_up(_ended())

        mocks["create_content"].assert_not_called()
        mocks["acquire_run_lock"].assert_not_called()
        mocks["mark_in_progress"].assert_not_called()
        # The Generate button's queued record is closed out with the reason, not left polling.
        assert mocks["mark_empty"].call_args.args[:2] == (1, ContentGenerationEmptyReason.TRIAL_ENDED)

    def test_running_trial_still_generates(self):
        mocks = _run_top_up(_running())

        mocks["create_content"].assert_called_once()
        mocks["mark_empty"].assert_not_called()

    def test_paid_user_with_an_old_trial_date_still_generates(self):
        mocks = _run_top_up({"subscription_status": "active", "trial_ends_at": datetime(2026, 1, 1)})

        mocks["create_content"].assert_called_once()


# --- publishing: the scheduler ----------------------------------------------------------------

def _run_scheduler_scan(subscription: dict) -> dict:
    """One `auto_check_scheduled_posts` scan over a single approved post for user 7."""
    from cqc_lem.app.run_scheduler import auto_check_scheduled_posts

    scheduled = datetime.now(timezone.utc) + timedelta(minutes=10)
    post_task = MagicMock()
    targets = {
        "get_ready_to_post_posts": {"return_value": [(42, scheduled, 7)]},
        "get_active_user_ids": {"return_value": []},
        "get_orphaned_scheduled_posts": {"return_value": []},
        "get_posts_missing_their_seed_comment": {"return_value": []},
        "get_ready_occasion_posts": {"return_value": []},
        "get_orphaned_occasion_claims": {"return_value": []},
        "update_db_post_status": {},
        "record_pre_post_skipped": {},
        "post_to_linkedin": {"new": post_task},
    }
    with ExitStack() as stack:
        mocks = {name: stack.enter_context(patch(f"{_SCHED}.{name}", **kw))
                 for name, kw in targets.items()}
        stack.enter_context(patch(_READ, return_value=subscription))
        auto_check_scheduled_posts.run()
    mocks["post_to_linkedin"] = post_task
    return mocks


class TestSchedulerStopsDispatchingAtTrialEnd:
    def test_ended_trial_post_is_not_dispatched_and_stays_approved(self):
        mocks = _run_scheduler_scan(_ended())

        mocks["post_to_linkedin"].apply_async.assert_not_called()
        # Not claimed as SCHEDULED, so it is still APPROVED for a scan after the user upgrades.
        mocks["update_db_post_status"].assert_not_called()

    def test_running_trial_post_is_dispatched(self):
        from cqc_lem.utilities.db import PostStatus
        mocks = _run_scheduler_scan(_running())

        mocks["post_to_linkedin"].apply_async.assert_called_once()
        assert mocks["post_to_linkedin"].apply_async.call_args.kwargs["kwargs"] == {
            "user_id": 7, "post_id": 42}
        mocks["update_db_post_status"].assert_called_once_with(42, PostStatus.SCHEDULED)


# --- publishing: the single choke point -------------------------------------------------------

def _run_publish(subscription: dict) -> tuple:
    """`post_to_linkedin` for user 1, post 5, with every LinkedIn/DB seam mocked."""
    from cqc_lem.app.engagement.posting import post_to_linkedin
    from cqc_lem.utilities.db import PostType

    targets = {
        "get_post_status": {"return_value": "scheduled"},
        "get_post_manual_publish": {"return_value": False},
        "get_user_password_pair_by_id": {"return_value": ("u@example.com", "pw")},
        "get_post_content": {"return_value": "A draft with nothing special in it."},
        "get_engagement_preferences": {"return_value": {}},
        "get_post_type": {"return_value": PostType.TEXT},
        "share_on_linkedin": {"return_value": "urn:li:ugcPost:1"},
        "insert_new_log": {},
        "update_db_post_status": {},
        "update_db_post_content": {},
        "update_db_post_first_comment_link": {},
        "sweep_reply_comments": {},
        "auto_seed_comment_on_post": {},
        "auto_second_wave_comment": {},
    }
    with ExitStack() as stack:
        mocks = {name: stack.enter_context(patch(f"{_POSTING}.{name}", **kw))
                 for name, kw in targets.items()}
        stack.enter_context(patch(_READ, return_value=subscription))
        result = post_to_linkedin.run(1, 5)
    return result, mocks


class TestPostToLinkedInRefusesAfterTrialEnd:
    def test_post_queued_before_the_trial_ended_does_not_publish(self):
        """An eta'd post (or an orphan re-queue) that runs after the trial ended is refused."""
        from cqc_lem.utilities.db import PostStatus
        result, mocks = _run_publish(_ended())

        assert "free trial ended" in result
        mocks["share_on_linkedin"].assert_not_called()
        mocks["get_user_password_pair_by_id"].assert_not_called()
        # Back on the queue as a RE-QUEUE (no approver), never as a fresh approval.
        mocks["update_db_post_status"].assert_called_once_with(5, PostStatus.APPROVED)

    def test_running_trial_still_publishes(self):
        result, mocks = _run_publish(_running())

        assert "free trial ended" not in str(result)
        mocks["share_on_linkedin"].assert_called_once()


class TestOccasionNativePublishRefusesAfterTrialEnd:
    def test_ended_trial_occasion_draft_is_not_claimed_or_published(self):
        """The native composer is a publish path too: nothing claimed, the draft stays APPROVED."""
        from cqc_lem.app.engagement.posting import auto_publish_occasion_post

        with patch(f"{_POSTING}.flag_enabled", return_value=True), \
             patch(_READ, return_value=_ended()), \
             patch(f"{_POSTING}.get_post_status") as status, \
             patch(f"{_POSTING}.update_db_post_status") as write, \
             patch(f"{_POSTING}.acquire_run_lock") as lock:
            result = auto_publish_occasion_post.run(1, 5)

        assert "free trial ended" in result
        status.assert_not_called()
        write.assert_not_called()
        lock.assert_not_called()


# --- newsletters: generation and publishing ---------------------------------------------------

_DB = "cqc_lem.utilities.db"
_NOW_NAIVE = datetime(2026, 10, 12, 12, 0)


class TestNewsletterStopsAtTrialEnd:
    def test_ended_trial_generates_no_newsletter_draft(self):
        from cqc_lem.app import run_scheduler as rs
        with patch(_READ, return_value=_ended()), \
             patch(f"{_DB}.get_newsletter_settings") as settings, \
             patch("cqc_lem.utilities.ai.ai_helper.generate_newsletter_edition") as generate:
            generated = rs._topup_newsletter_drafts_for_user(1, _NOW_NAIVE)

        assert generated == 0
        settings.assert_not_called()
        generate.assert_not_called()

    def test_running_trial_reaches_the_newsletter_queue(self):
        from cqc_lem.app import run_scheduler as rs
        with patch(_READ, return_value=_running()), \
             patch(f"{_DB}.get_newsletter_settings", return_value={"max_queued_drafts": 1}) as settings, \
             patch(f"{_DB}.count_pending_newsletter_editions", return_value=1):
            # The queue is already full, so it answers 0 — but only after reading the settings.
            generated = rs._topup_newsletter_drafts_for_user(1, _NOW_NAIVE)

        assert generated == 0
        settings.assert_called_once_with(1)

    def _publish(self, subscription: dict) -> tuple:
        from cqc_lem.app import run_scheduler as rs
        dispatch = MagicMock()
        due = [{"id": 9, "status": "approved", "scheduled_for": datetime(2026, 10, 12, 8, 0)}]
        with patch(_READ, return_value=subscription), \
             patch(f"{_DB}.get_pending_newsletter_editions", return_value=due), \
             patch(f"{_DB}.get_newsletter_settings", return_value={}):
            n = rs._publish_next_due_edition_for_user(1, _NOW_NAIVE, dispatch)
        return n, dispatch

    def test_ended_trial_publishes_no_newsletter_edition(self):
        n, dispatch = self._publish(_ended())
        assert n == 0
        dispatch.assert_not_called()

    def test_running_trial_publishes_its_approved_edition(self):
        n, dispatch = self._publish(_running())
        assert n == 1
        dispatch.assert_called_once_with(9)
