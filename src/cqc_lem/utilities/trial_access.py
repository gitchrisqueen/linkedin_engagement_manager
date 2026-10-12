"""Whether a user's free trial has ended without a paid subscription (issue #2380).

The ONE predicate the content top-up and the publish path read before spending on, or posting for,
a user. Engagement lanes need nothing from here: they fan out over `get_active_user_ids()`, whose
SQL already drops a `trial` row whose `trial_ends_at` has passed. Content generation and publishing
did not — the generation beat walks every user with a planned slot, and the publish beat dispatched
`post_to_linkedin` for inactive users on purpose — so both read this instead.

Lapsed means BOTH:

* `subscription_status` is not a paid one (`active` / `past_due`); and
* `trial_ends_at` is set and is now or in the past.

So a paying user is never lapsed whatever their old trial date says, and a `trial` row with no end
date (pre-trial accounts) is not lapsed either. Fails OPEN: an unreadable subscription (the read
already logs its own ERROR) is not evidence the trial ended, so it never stops a post.
"""

from datetime import datetime, timezone
from typing import Optional

from cqc_lem.utilities.db import get_user_subscription_info

# A past-due subscription is still a subscription: Stripe's dunning window decides that one, not the
# trial clock.
PAID_SUBSCRIPTION_STATUSES = ("active", "past_due")


def _as_utc(dt: datetime) -> datetime:
    """`dt` as an aware UTC datetime; a naive value (MySQL DATETIME) is taken to already be UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def trial_lapsed(user_id: int, now: Optional[datetime] = None) -> bool:
    """True when the user's free trial has ended and they hold no paid subscription.

    Args:
        user_id: The user to check.
        now: The instant to compare against; defaults to the current UTC time.

    Returns:
        True only when the subscription row was read, its status is not a paid one, and its
        `trial_ends_at` is at or before `now`. False for every other case, including an
        unreadable row.
    """
    info = get_user_subscription_info(user_id)
    if not info:
        return False
    if str(info.get("subscription_status") or "") in PAID_SUBSCRIPTION_STATUSES:
        return False
    ends_at = info.get("trial_ends_at")
    if not isinstance(ends_at, datetime):
        return False
    current = _as_utc(now) if now is not None else datetime.now(timezone.utc)
    return _as_utc(ends_at) <= current
