from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import requests

from cqc_lem.utilities.env_constants import LI_CLIENT_ID, LI_CLIENT_SECRET
from cqc_lem.utilities.logger import myprint

LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
EXPIRY_WARNING_DAYS = 30


def get_token_expiry(token_info: dict) -> Optional[datetime]:
    created_at = token_info.get('access_token_created_at')
    expires_in = token_info.get('access_token_expires_in')
    if not created_at or not expires_in:
        return None
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(seconds=int(expires_in))


def is_token_expired(token_info: dict) -> bool:
    expiry = get_token_expiry(token_info)
    if expiry is None:
        return True
    return expiry <= datetime.now(timezone.utc)


def is_token_expiring_soon(token_info: dict, days: int = EXPIRY_WARNING_DAYS) -> bool:
    expiry = get_token_expiry(token_info)
    if expiry is None:
        return True
    return expiry <= datetime.now(timezone.utc) + timedelta(days=days)


def attempt_token_refresh(user_id: int) -> Tuple[bool, Optional[str]]:
    # Import here to avoid circular imports at module load
    from cqc_lem.utilities.db import get_user_token_info, update_user_access_token

    token_info = get_user_token_info(user_id)
    if not token_info:
        return False, None

    refresh_token = token_info.get('refresh_token')
    if not refresh_token:
        myprint(f"No refresh_token for user_id {user_id} — cannot auto-refresh")
        return False, None

    refresh_created = token_info.get('refresh_token_created_at')
    refresh_expires_in = token_info.get('refresh_token_expires_in')
    if refresh_created and refresh_expires_in:
        if refresh_created.tzinfo is None:
            refresh_created = refresh_created.replace(tzinfo=timezone.utc)
        refresh_expiry = refresh_created + timedelta(seconds=int(refresh_expires_in))
        if refresh_expiry <= datetime.now(timezone.utc):
            myprint(f"refresh_token expired for user_id {user_id}")
            return False, None

    try:
        resp = requests.post(
            LINKEDIN_TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': LI_CLIENT_ID,
                'client_secret': LI_CLIENT_SECRET,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        new_access_token = data.get('access_token')
        expires_in = data.get('expires_in')
        new_refresh_token = data.get('refresh_token')
        new_refresh_expires_in = data.get('refresh_token_expires_in')

        if not new_access_token:
            myprint(f"Token refresh response missing access_token for user_id {user_id}")
            return False, None

        update_user_access_token(
            user_id,
            new_access_token,
            expires_in,
            refresh_token=new_refresh_token,
            refresh_token_expires_in=new_refresh_expires_in,
        )
        myprint(f"Token refreshed for user_id {user_id}")
        return True, new_access_token

    except requests.RequestException as e:
        myprint(f"Token refresh request failed for user_id {user_id}: {e}")
        return False, None
