"""`trial_lapsed` — the one predicate for "the free trial ended with no paid plan" (issue #2380)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

_READ = "cqc_lem.utilities.trial_access.get_user_subscription_info"
_NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)


def _lapsed(info) -> bool:
    from cqc_lem.utilities.trial_access import trial_lapsed
    with patch(_READ, return_value=info) as read:
        result = trial_lapsed(7, now=_NOW)
    read.assert_called_once_with(7)
    return result


class TestTrialLapsed:
    def test_trial_whose_end_has_passed_is_lapsed(self):
        assert _lapsed({"subscription_status": "trial",
                        "trial_ends_at": datetime(2026, 10, 11, 12, 0, 0)}) is True

    def test_trial_ending_exactly_now_is_lapsed(self):
        assert _lapsed({"subscription_status": "trial",
                        "trial_ends_at": _NOW.replace(tzinfo=None)}) is True

    def test_trial_still_running_is_not_lapsed(self):
        assert _lapsed({"subscription_status": "trial",
                        "trial_ends_at": (_NOW + timedelta(minutes=1)).replace(tzinfo=None)}) is False

    def test_aware_end_date_is_compared_in_utc(self):
        # 13:00 at UTC+2 is 11:00 UTC — an hour BEFORE now, so lapsed.
        plus_two = timezone(timedelta(hours=2))
        assert _lapsed({"subscription_status": "trial",
                        "trial_ends_at": datetime(2026, 10, 12, 13, 0, 0, tzinfo=plus_two)}) is True

    @pytest.mark.parametrize("status", ["active", "past_due"])
    def test_paid_subscription_is_never_lapsed_whatever_the_old_trial_date(self, status):
        assert _lapsed({"subscription_status": status,
                        "trial_ends_at": datetime(2026, 1, 1)}) is False

    @pytest.mark.parametrize("status", ["inactive", "cancelled", None])
    def test_unpaid_status_with_a_passed_trial_is_lapsed(self, status):
        assert _lapsed({"subscription_status": status,
                        "trial_ends_at": datetime(2026, 1, 1)}) is True

    def test_trial_with_no_end_date_is_not_lapsed(self):
        assert _lapsed({"subscription_status": "trial", "trial_ends_at": None}) is False

    @pytest.mark.parametrize("info", [None, {}])
    def test_unreadable_subscription_fails_open(self, info):
        assert _lapsed(info) is False

    def test_defaults_to_the_current_time(self):
        from cqc_lem.utilities.trial_access import trial_lapsed
        with patch(_READ, return_value={"subscription_status": "trial",
                                        "trial_ends_at": datetime(2000, 1, 1)}):
            assert trial_lapsed(7) is True
