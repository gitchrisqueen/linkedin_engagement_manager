"""Trial-facing emails promise no automated engagement (issue #2375).

The trial covers posting through approval and engagement is suggestions the user acts on. Every
email a trial account can receive is rendered here with the email transport mocked, and its subject
and HTML are checked against `promises_automated_engagement`. The paid wording is rendered through
the same path and must still trip the check, so a detector that matches nothing fails this file.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from cqc_lem.utilities import onboarding
from cqc_lem.utilities.db import OnboardingStep
from cqc_lem.utilities.email import (
    send_connect_linkedin_email,
    send_linkedin_token_expiring_email,
    send_onboarding_nudge_email,
)
from cqc_lem.utilities.trial_copy import (
    automated_engagement_phrases,
    is_trial_subscription,
    promises_automated_engagement,
)

pytestmark = pytest.mark.unit

_DISPATCH = "cqc_lem.utilities.email._dispatch_email"
NOW = datetime(2026, 10, 12, 12, 0, 0)


def _sent(send, *args, **kwargs) -> str:
    """Subject + HTML of one email, rendered with the transport mocked. Nothing is sent."""
    with patch(_DISPATCH, return_value=True) as dispatch:
        assert send(*args, **kwargs) is True
    _to, subject, html = dispatch.call_args[0][:3]
    return f"{subject}\n{html}"


def _all_nudges() -> list:
    """Every onboarding nudge definition, read off the module so a new one is covered by default."""
    return [*onboarding._STEP_NUDGES, onboarding._STORY_BANK_NUDGE, onboarding._TRIAL_NUDGE]


def _render_nudge(nudge: dict) -> str:
    return _sent(send_onboarding_nudge_email, "u@example.com", subject=nudge["subject"],
                 headline=nudge["headline"], body=nudge["body"], cta_label=nudge["cta_label"],
                 cta_path=nudge["cta_path"])


class TestDetector:
    @pytest.mark.parametrize("text", [
        "post, comment, and engage on your behalf",
        "posting, commenting and messaging on your behalf have stopped",
        "Set how many comments and DMs a day",
        "we send connection invites for you",
        "we reply to every comment",
        "keep automation running",
        "who's worth engaging",
    ])
    def test_flags_automated_engagement(self, text):
        assert promises_automated_engagement(text), text

    @pytest.mark.parametrize("text", [
        "LinkedIn Engagement Manager needs your LinkedIn connected",
        "every drafted post and engagement suggestion yours",
        "we could not renew it automatically",
        "your approved posts can't publish",
        "",
    ])
    def test_lets_trial_scope_wording_through(self, text):
        assert automated_engagement_phrases(text) == []


class TestIsTrialSubscription:
    @pytest.mark.parametrize("sub,expected", [
        ({"subscription_status": "trial"}, True),
        ({"subscription_status": " TRIAL "}, True),
        ({"subscription_status": "active"}, False),
        ({"subscription_status": "past_due"}, False),
        ({"subscription_status": None}, True),
        ({}, True),
        (None, True),
    ])
    def test_unreadable_counts_as_trial(self, sub, expected):
        assert is_trial_subscription(sub) is expected


class TestOnboardingNudges:
    def test_every_nudge_is_clean_for_a_trial_account(self):
        for nudge in _all_nudges():
            rendered = _render_nudge(onboarding._for_audience(nudge, trial=True))
            assert automated_engagement_phrases(rendered) == [], nudge["key"]

    def test_the_paid_wording_still_trips_the_check(self):
        # Proves the loop above renders real copy through a detector that bites.
        flagged = [n["key"] for n in _all_nudges()
                   if promises_automated_engagement(_render_nudge(onboarding._for_audience(n, False)))]
        assert flagged == [onboarding.NUDGE_CONNECT, onboarding.NUDGE_VOICE]

    def test_trial_copy_is_pinned(self):
        connect = onboarding._for_audience(onboarding._STEP_NUDGES[0], trial=True)
        voice = onboarding._for_audience(onboarding._STEP_NUDGES[1], trial=True)
        assert connect["subject"] == "Connect LinkedIn so your approved posts can publish"
        assert connect["body"] == (
            "Your account is ready, but LinkedIn isn't connected yet — so your approved posts "
            "can't publish. It takes about a minute from your account page.")
        assert voice["body"] == (
            "LinkedIn is connected. Next: pick your tone and the topics you want to be known "
            "for — that's what keeps every drafted post and engagement suggestion yours.")
        trial_ending = onboarding._for_audience(onboarding._TRIAL_NUDGE, trial=True)
        assert trial_ending["body"] == (
            "You haven't seen LEM actually run yet. Approve a drafted post and your first post "
            "can go live before the trial is up.")

    def test_select_nudge_hands_a_trial_account_the_trial_copy(self):
        steps = {step: False for step in OnboardingStep}
        nudge = onboarding.select_nudge(steps, started_at=NOW - timedelta(hours=25), now=NOW,
                                        trial=True)
        assert nudge["key"] == onboarding.NUDGE_CONNECT
        assert nudge["trial"] is True
        assert not promises_automated_engagement(nudge["subject"] + " " + nudge["body"])

    def test_select_nudge_keeps_the_paid_copy_for_a_paid_account(self):
        steps = {step: False for step in OnboardingStep}
        nudge = onboarding.select_nudge(steps, started_at=NOW - timedelta(hours=25), now=NOW)
        assert nudge["trial"] is False
        assert nudge["subject"] == "Connect LinkedIn to switch your automation on"

    @pytest.mark.parametrize("status,expected", [("trial", True), ("active", False), (None, True)])
    def test_next_nudge_reads_the_trial_flag_off_the_subscription(self, status, expected):
        state = {"started_at": NOW - timedelta(days=30)}
        with patch.object(onboarding, "get_onboarding_nudges_sent", return_value={}), \
             patch.object(onboarding, "get_user_subscription_info",
                          return_value={"subscription_status": status}), \
             patch.object(onboarding, "count_story_bank_entries", return_value=0):
            nudge = onboarding.next_nudge_for_user(7, state)
        assert nudge["key"] == onboarding.NUDGE_CONNECT
        assert nudge["trial"] is expected


class TestNudgeRewriteGuard:
    def _send(self, nudge: dict, rewrite: str):
        with patch("cqc_lem.utilities.ai.ai_helper.generate_onboarding_nudge_copy",
                   return_value=rewrite), \
             patch("cqc_lem.utilities.notifications.notify_onboarding_nudge",
                   return_value=True) as notify, \
             patch.object(onboarding, "record_onboarding_nudge"):
            assert onboarding.send_onboarding_nudge(7, nudge) is True
        return notify.call_args[0][1]["body"]

    def test_a_rewrite_promising_engagement_falls_back_for_a_trial_account(self):
        nudge = onboarding._for_audience(onboarding._STEP_NUDGES[0], trial=True)
        body = self._send(nudge, "Connect now and LEM starts commenting for you.")
        assert body == nudge["body"]

    def test_a_clean_rewrite_is_kept_for_a_trial_account(self):
        nudge = onboarding._for_audience(onboarding._STEP_NUDGES[0], trial=True)
        assert self._send(nudge, "Connect LinkedIn to publish.") == "Connect LinkedIn to publish."

    def test_a_paid_account_keeps_its_rewrite(self):
        nudge = onboarding._for_audience(onboarding._STEP_NUDGES[0], trial=False)
        rewrite = "Connect now so LEM can post and comment for you."
        assert self._send(nudge, rewrite) == rewrite


class TestConnectLinkedInEmail:
    def test_trial_wording_is_clean(self):
        rendered = _sent(send_connect_linkedin_email, "u@example.com", trial=True)
        assert automated_engagement_phrases(rendered) == []
        assert "connect your LinkedIn so your approved posts can publish" in rendered

    def test_paid_wording_is_unchanged(self):
        rendered = _sent(send_connect_linkedin_email, "u@example.com")
        assert "connect your LinkedIn to keep automation running" in rendered
        assert "comment, and engage on your behalf" in rendered

    @pytest.mark.parametrize("status,expected", [("trial", True), ("active", False), (None, True)])
    def test_notify_picks_the_wording_off_the_subscription(self, status, expected, monkeypatch):
        from cqc_lem.utilities import notifications
        monkeypatch.setenv("LINKEDIN_SESSION_EMAIL_THROTTLE_DAYS", "7")
        with patch.object(notifications, "get_linkedin_session_email_sent_at", return_value=None), \
             patch.object(notifications, "get_user_email", return_value="u@e.com"), \
             patch.object(notifications, "get_user_subscription_info",
                          return_value={"subscription_status": status}), \
             patch.object(notifications, "send_connect_linkedin_email", return_value=True) as send, \
             patch.object(notifications, "set_linkedin_session_email_sent_at"):
            assert notifications.notify_linkedin_session(7) is True
        send.assert_called_once_with("u@e.com", trial=expected)


class TestTokenExpiringEmail:
    @pytest.mark.parametrize("days", [None, 0, -1, 5])
    def test_trial_wording_is_clean(self, days):
        rendered = _sent(send_linkedin_token_expiring_email, "u@example.com", days, None,
                         trial=True)
        assert automated_engagement_phrases(rendered) == []

    def test_trial_expired_says_posting_stopped(self):
        rendered = _sent(send_linkedin_token_expiring_email, "u@example.com", 0, trial=True)
        assert "It has already expired, so posting on your behalf has stopped." in rendered

    def test_paid_expired_wording_is_unchanged(self):
        rendered = _sent(send_linkedin_token_expiring_email, "u@example.com", 0)
        assert "posting, commenting and messaging on your behalf have" in rendered

    @pytest.mark.parametrize("status,expected", [("trial", True), ("active", False)])
    def test_notify_picks_the_wording_off_the_subscription(self, status, expected, monkeypatch):
        from cqc_lem.utilities import notifications
        monkeypatch.setenv("LINKEDIN_TOKEN_EMAIL_THROTTLE_DAYS", "0")
        with patch.object(notifications, "get_user_email", return_value="u@e.com"), \
             patch.object(notifications, "get_user_subscription_info",
                          return_value={"subscription_status": status}), \
             patch("cqc_lem.utilities.email.send_linkedin_token_expiring_email",
                   return_value=True) as send:
            assert notifications.notify_linkedin_token_expiring(7, 0) is True
        assert send.call_args.kwargs == {"trial": expected}
