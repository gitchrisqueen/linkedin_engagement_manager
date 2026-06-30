"""Throttled LinkedIn-session notifications (connect / re-validate).

Used by the login flow (auto-detects a stale session) and by a scheduled task
(emails users with no validated session). Throttled to at most once per
LINKEDIN_SESSION_EMAIL_THROTTLE_DAYS so users aren't spammed every automation cycle.
"""

import os
from datetime import datetime, timedelta

from cqc_lem.utilities.db import (
    get_user_email,
    get_linkedin_session_email_sent_at,
    set_linkedin_session_email_sent_at,
)
from cqc_lem.utilities.email import (
    send_connect_linkedin_email,
    send_session_revalidation_email,
)
from cqc_lem.utilities.logger import myprint


def notify_linkedin_session(user_id: int, revalidation: bool = False) -> bool:
    """Email the user to connect (revalidation=False) or reconnect (True) their LinkedIn
    session. Throttled per LINKEDIN_SESSION_EMAIL_THROTTLE_DAYS (default 7). Returns True
    only if an email was actually sent."""
    throttle_days = int(os.getenv("LINKEDIN_SESSION_EMAIL_THROTTLE_DAYS", "7"))
    last = get_linkedin_session_email_sent_at(user_id)
    if last and throttle_days > 0:
        try:
            if datetime.now() - last < timedelta(days=throttle_days):
                return False
        except TypeError:
            pass  # unexpected type — fall through and send

    email = get_user_email(user_id)
    if not email:
        return False

    sent = (send_session_revalidation_email(email) if revalidation
            else send_connect_linkedin_email(email))
    if sent:
        set_linkedin_session_email_sent_at(user_id)
        myprint(f"Sent LinkedIn session {'re-validation' if revalidation else 'connect'} "
                f"email to user_id {user_id}")
    return sent
