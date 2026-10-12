"""A crashed Chrome tab ends a Selenium lane's run on ONE warning, never an immediate $exception.

Issues #2393 (`sweep_comment_followups`), #2402 (`automate_commenting`) and #2403
(`automate_appreciation_dms_for_user`) each filed `WebDriverException: tab crashed` through the
lane's run-level `log_error`. A dead renderer is an expected transient: the run ends, it warns once
(escalating only if it recurs), and nothing loops on the dead tab. The shared decision is
`selenium_util.log_lane_failure`, so the log patches bind THERE, where the helper reads them.
"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import WebDriverException

pytestmark = pytest.mark.unit

_FEED = "cqc_lem.app.engagement.feed"
_POST = "cqc_lem.app.engagement.posting"
_OUT = "cqc_lem.app.engagement.outreach"
_SU = "cqc_lem.utilities.selenium_util"


def _crash() -> WebDriverException:
    return WebDriverException("tab crashed\n  (Session info: chrome=153.0.8010.47)")


def _logs(es: ExitStack) -> dict:
    """Patch the helper's own log calls; returns the mocks keyed by level."""
    return {level: es.enter_context(patch(f"{_SU}.log_{level}"))
            for level in ("debug", "warning", "error")}


class TestSweepCommentFollowups:
    """#2393."""

    def _run(self, es: ExitStack, *, session=None, worker=None) -> str:
        from cqc_lem.app.engagement.posting import _run_comment_followups_sweep

        p = lambda name, **kw: es.enter_context(patch(f"{_POST}.{name}", **kw))  # noqa: E731
        p("get_recent_navigable_commented_posts",
          return_value=[{"post_key": "feedurn://urn:li:activity:1"},
                        {"post_key": "feedurn://urn:li:activity:2"},
                        {"post_key": "feedurn://urn:li:activity:3"}])
        p("acquire_run_lock", return_value="tok")
        self.release = p("release_run_lock")
        p("get_engagement_preferences", return_value={})
        p("count_followup_replies_today", return_value=0)
        p("get_or_create_profile_synthesis", return_value="voice")
        p("get_current_profile",
          **(session or {"return_value": (MagicMock(), MagicMock(), "e", MagicMock())}))
        self.quit = p("quit_gracefully")
        self.lane_error = p("log_error")
        self.lane_warning = p("log_warning")
        self.worker = p("_followup_on_post_comment_replies", **(worker or {}))
        return _run_comment_followups_sweep(1)

    def test_a_crash_mid_sweep_stops_on_one_warning(self):
        """The first post ships, the second crashes, the third is never tried on the dead tab."""
        with ExitStack() as es:
            logs = _logs(es)
            out = self._run(es, worker={"side_effect": [{"reacted": 1, "replied": 1}, _crash(),
                                                        {"reacted": 9, "replied": 9}]})
        assert self.worker.call_count == 2
        assert "browser tab crashed" in out and "replied 1" in out
        logs["warning"].assert_called_once()
        assert "sweep_comment_followups" in logs["warning"].call_args.args[0]
        logs["error"].assert_not_called()
        self.lane_error.assert_not_called()
        self.lane_warning.assert_not_called()  # no per-post "Follow-up: post failed" for the crash
        self.quit.assert_called_once()
        self.release.assert_called_once()

    def test_a_non_crash_per_post_fault_still_warns_and_continues(self):
        with ExitStack() as es:
            _logs(es)
            self._run(es, worker={"side_effect": [RuntimeError("boom"),
                                                  {"reacted": 0, "replied": 0},
                                                  {"reacted": 0, "replied": 0}]})
        assert self.worker.call_count == 3
        self.lane_warning.assert_called_once()

    def test_a_non_crash_run_fault_still_raises(self):
        """Anything else is unchanged: it fails the task and the Celery hook files it, once."""
        with ExitStack() as es, pytest.raises(RuntimeError):
            logs = _logs(es)
            es.enter_context(patch(f"{_POST}.get_or_create_profile_synthesis",
                                   side_effect=RuntimeError("boom")))
            from cqc_lem.app.engagement.posting import _run_comment_followups_sweep
            p = lambda name, **kw: es.enter_context(patch(f"{_POST}.{name}", **kw))  # noqa: E731
            p("get_recent_navigable_commented_posts",
              return_value=[{"post_key": "feedurn://urn:li:activity:1"}])
            p("acquire_run_lock", return_value="tok")
            p("release_run_lock")
            p("get_engagement_preferences", return_value={})
            p("count_followup_replies_today", return_value=0)
            p("get_current_profile", return_value=(MagicMock(), MagicMock(), "e", MagicMock()))
            p("quit_gracefully")
            _run_comment_followups_sweep(1)
        logs["error"].assert_not_called()

    def test_a_login_crash_is_debug_because_the_session_layer_warned(self):
        with ExitStack() as es:
            logs = _logs(es)
            out = self._run(es, session={"side_effect": _crash()})
        assert out.startswith("Failed to start follow-up sweep")
        logs["debug"].assert_called_once()
        logs["warning"].assert_not_called()
        logs["error"].assert_not_called()
        self.lane_error.assert_not_called()
        self.release.assert_called_once()

    def test_a_non_crash_login_fault_is_still_an_error(self):
        with ExitStack() as es:
            logs = _logs(es)
            self._run(es, session={"side_effect": RuntimeError("db down")})
        logs["error"].assert_called_once()
        assert logs["error"].call_args.args[0] == "Error starting follow-up sweep"


class TestAutomateCommenting:
    """#2402."""

    def _run(self, es: ExitStack, *, session=None, walk=None) -> str:
        from cqc_lem.app.engagement import feed as mod

        p = lambda name, **kw: es.enter_context(patch(f"{_FEED}.{name}", **kw))  # noqa: E731
        p("is_commenting_held", return_value=False)
        p("_comment_allowance_today", return_value=3)
        p("acquire_run_lock", return_value="tok")
        self.release = p("release_run_lock")
        p("get_current_profile",
          **(session or {"return_value": (MagicMock(), MagicMock(), "e", MagicMock())}))
        p("navigate_to_feed")
        p("comment_on_feed_inline", **(walk or {"return_value": 1}))
        self.quit = p("quit_gracefully")
        self.lane_error = p("log_error")
        self.requeue = es.enter_context(patch.object(mod.automate_commenting, "apply_async"))
        return mod.automate_commenting.run(user_id=1, loop_for_duration=900)

    def test_a_crash_mid_walk_warns_once_and_does_not_requeue(self):
        with ExitStack() as es:
            logs = _logs(es)
            out = self._run(es, walk={"side_effect": _crash()})
        assert "browser tab crashed" in out
        logs["warning"].assert_called_once()
        assert "automate_commenting" in logs["warning"].call_args.args[0]
        logs["error"].assert_not_called()
        self.lane_error.assert_not_called()
        self.requeue.assert_not_called()
        self.quit.assert_called_once()
        self.release.assert_called_once()

    def test_a_non_crash_walk_fault_is_still_an_error(self):
        with ExitStack() as es:
            logs = _logs(es)
            out = self._run(es, walk={"side_effect": RuntimeError("boom")})
        assert out.startswith("Error while automating commenting")
        logs["error"].assert_called_once()
        logs["warning"].assert_not_called()

    def test_a_login_crash_is_debug_because_the_session_layer_warned(self):
        with ExitStack() as es:
            logs = _logs(es)
            out = self._run(es, session={"side_effect": _crash()})
        assert out.startswith("Failed to start auto commenting")
        logs["debug"].assert_called_once()
        logs["warning"].assert_not_called()
        logs["error"].assert_not_called()
        self.release.assert_called_once()


class TestRosterWalkStopsOnCrash:
    """The roster pass ran first in #2402's lane; it must not warn once per target on a dead tab."""

    def test_the_first_crash_ends_the_walk(self):
        from cqc_lem.app.engagement import feed as mod
        from cqc_lem.domain.models import FeedRunContext

        driver = MagicMock()
        driver.get.side_effect = _crash()
        targets = [{"id": i, "profile_url": f"https://www.linkedin.com/in/p{i}", "name": f"P{i}",
                    "category": "peer", "max_comments_per_week": 2, "active": True,
                    "last_engaged_at": None, "comments_this_week": 0, "source": "user"}
                   for i in range(3)]
        ctx = FeedRunContext(driver=driver, wait=MagicMock(), my_profile=MagicMock(), user_id=1,
                             prefs={}, profile_synthesis="s", seen=set(), deadline_ts=None)
        with patch(f"{_FEED}.get_engagement_targets", return_value=targets), \
             patch(f"{_FEED}.log_warning") as warn, \
             pytest.raises(WebDriverException):
            mod.comment_on_roster_posts(ctx, 5)
        assert driver.get.call_count == 1
        warn.assert_not_called()


class TestAppreciationDms:
    """#2403 — this lane logs in directly, so nothing upstream has warned yet."""

    def _run(self, es: ExitStack, *, login=None, recs=None) -> dict:
        from cqc_lem.app.engagement.outreach import automate_appreciation_dms_for_user

        p = lambda name, **kw: es.enter_context(patch(f"{_OUT}.{name}", **kw))  # noqa: E731
        p("get_user_password_pair_by_id", return_value=("a@b.c", "pw"))
        p("get_driver_wait_pair", return_value=(MagicMock(), MagicMock()))
        p("login_to_linkedin", **(login or {}))
        self.quit = p("quit_gracefully")
        p("load_profile_for_user", return_value=MagicMock(profile_url=""))
        p("accept_connection_request", return_value={})
        p("_appreciation_dm_budget", return_value=5)
        p("_dispatch_appreciation_dms", return_value=0)
        self.recs = p("get_recent_recommendations", **(recs or {"return_value": {}}))
        self.mentions = p("get_recent_collaborators", return_value={})
        self.lane_error = p("log_error")
        return automate_appreciation_dms_for_user.run(user_id=1)

    def test_a_crash_mid_scan_warns_once_and_stops(self):
        with ExitStack() as es:
            logs = _logs(es)
            result = self._run(es, recs={"side_effect": _crash()})
        assert result["status"] == "error"
        assert "browser tab crashed" in result["message"]
        self.mentions.assert_not_called()
        logs["warning"].assert_called_once()
        assert "automate_appreciation_dms_for_user" in logs["warning"].call_args.args[0]
        logs["error"].assert_not_called()
        self.lane_error.assert_not_called()
        self.quit.assert_called_once()

    def test_a_login_crash_warns_here_because_nothing_upstream_did(self):
        with ExitStack() as es:
            logs = _logs(es)
            self._run(es, login={"side_effect": _crash()})
        logs["warning"].assert_called_once()
        logs["debug"].assert_not_called()
        logs["error"].assert_not_called()

    def test_a_non_crash_fault_is_still_an_error(self):
        with ExitStack() as es:
            logs = _logs(es)
            result = self._run(es, recs={"side_effect": RuntimeError("boom")})
        assert result["message"].startswith("Error while sending appreciation DMs")
        logs["error"].assert_called_once()
        logs["warning"].assert_not_called()
