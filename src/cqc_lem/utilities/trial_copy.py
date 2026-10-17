"""What a trial account's emails may say about engagement (issue #2375).

The trial covers posting through approval; engagement is suggestions the user acts on. An email
that tells a trial account LEM will comment, message, reply or send invites for it promises
something the trial does not do. Emails shared with paid accounts keep their copy and switch to
the trial wording at the one function that builds them; this module answers the two questions
those builders need: is this account on the trial, and does this copy promise automated
engagement.
"""

import re
from collections.abc import Mapping
from typing import Any, Optional

TRIAL_SUBSCRIPTION_STATUS = "trial"

# Words that describe LEM engaging FOR the user. "engagement suggestion(s)" is the trial's own
# feature and "LinkedIn Engagement Manager" is the product's name, so both are let through.
# "automation" is matched as a word so "renew it automatically" (the OAuth token) does not trip it.
_AUTOMATED_ENGAGEMENT = re.compile(
    r"\bcomment\w*"
    r"|\bDMs?\b"
    r"|\bmessag\w*"
    r"|\binvit\w*"
    r"|\bconnection requests?\b"
    r"|\brepl(?:y|ies|ying)\b"
    r"|\bautomation\b"
    r"|(?<!LinkedIn )\bengag\w*\b(?!\s+suggestions?\b)",
    re.IGNORECASE,
)


def is_trial_subscription(subscription: Optional[Mapping[str, Any]]) -> bool:
    """Whether a `get_user_subscription_info` row should get the trial wording.

    An unreadable row (None or empty) counts as trial: the trial wording is still true for a paid
    account, it only leaves engagement out, while the paid wording promises a trial account
    something it does not get.

    Args:
        subscription: The user's subscription fields, or None when they could not be read.

    Returns:
        True when the account is on the trial or its status is unknown.
    """
    if not subscription:
        return True
    status = subscription.get("subscription_status")
    if status is None:
        return True
    return str(status).strip().lower() == TRIAL_SUBSCRIPTION_STATUS


def automated_engagement_phrases(text: str) -> list[str]:
    """The phrases in `text` that describe LEM engaging on the user's behalf.

    Args:
        text: Email subject, body or rendered HTML.

    Returns:
        Every matching phrase, in order; empty when the copy promises no automated engagement.
    """
    return [m.group(0) for m in _AUTOMATED_ENGAGEMENT.finditer(text or "")]


def promises_automated_engagement(text: str) -> bool:
    """Whether `text` mentions commenting, messaging, replies, invites or automated engagement.

    Args:
        text: Email subject, body or rendered HTML.

    Returns:
        True when trial-facing copy would promise something the trial does not do.
    """
    return bool(automated_engagement_phrases(text))
