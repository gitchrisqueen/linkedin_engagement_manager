import json
import os
import time
from datetime import datetime, timezone
from enum import IntEnum
from typing import Dict, List, Union
from typing import Optional, Any
from urllib.parse import urlparse, urlunparse

from cqc_lem import assets_dir
from cqc_lem.app.aws_test_celery_task import test_get_my_profile
from cqc_lem.app.run_automation import automate_invites_to_company_page_for_user, automate_reply_commenting
from celery import chain as celery_chain
from cqc_lem.app.run_content_plan import auto_create_weekly_content, plan_content_for_user
from cqc_lem.utilities.db import (
    insert_post, get_post_by_email, get_user_id, update_db_post, get_post_user_id,
    add_user_with_access_token, update_user, PostType, PostStatus, get_posts,
    get_recent_logs, bulk_update_posts, soft_delete_posts,
    create_pin_for_email, verify_pin_for_email, delete_pin_for_email,
    create_session, get_session_user_id, delete_session,
    add_user_by_email, get_user_email, get_user_token_info,
    get_user_subscription_info, get_user_preferences, update_user_preferences,
    update_subscription_from_stripe, update_user_linkedin_token,
    get_users_with_stripe_subscriptions,
    update_user_linkedin_password,
    get_user_blog_url, get_user_sitemap_url,
    get_user_by_stripe_customer_id, get_avatar_credit_ledger_entry_by_session,
    get_avatar_credit_balance, add_avatar_credits,
    deduct_avatar_credit, insert_avatar_training,
    update_avatar_training_status, set_active_avatar,
    get_avatar_trainings, get_active_avatar,
    get_user_timezone, update_user_timezone,
    replace_video_url_base, get_post_type, get_post_buyer_stage,
    update_db_post_carousel_slides,
)
from cqc_lem.utilities.email import generate_pin, hash_pin, send_pin_email
from cqc_lem.utilities.linkedin.token_refresh import (
    get_token_expiry, is_token_expired, is_token_expiring_soon, attempt_token_refresh,
)
from cqc_lem.utilities.env_constants import LI_CLIENT_ID, LI_CLIENT_SECRET, LI_REDIRECT_URL, LI_STATE_SALT, ADMIN_SECRET
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.mime_type_helper import get_file_mime_type
from cqc_lem.utilities.observability import track_api_call
from cqc_lem.utilities.utils import get_file_extension_from_filepath
from fastapi import FastAPI, HTTPException, Request, status, APIRouter, Header
from fastapi import File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from linkedin_api.clients.auth.client import AuthClient
from linkedin_api.clients.restli.client import RestliClient
from linkedin_api.common.errors import ResponseFormattingError
from pydantic import BaseModel, computed_field

app = FastAPI()

# All API routes live under /api so the React client's baseURL: '/api' works
router = APIRouter(prefix="/api")


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    start = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        track_api_call(
            route=request.url.path,
            method=request.method,
            status_code=status_code,
            latency_ms=int((time.time() - start) * 1000),
        )


_ui_dist = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")

error_responses = {
    400: {"description": "Bad Request"},
    401: {"description": "Unauthorized"},
    403: {"description": "Forbidden"},
    404: {"description": "Not Found"},
    405: {"description": "Method Not Allowed"},
    422: {"description": "Unprocessable Entity"}
}


class ResponseModel(BaseModel):
    status_code: int
    detail: Any


def _parse_slides(raw) -> Optional[List[str]]:
    if not raw:
        return None
    if isinstance(raw, list):
        return raw
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


class PostRequest(BaseModel):
    content: str
    video_url: Optional[str] = None
    post_type: Optional[PostType] = PostType.TEXT
    scheduled_datetime: datetime
    email: Optional[str] = None
    status: Optional[PostStatus] = PostStatus.PENDING
    carousel_slides: Optional[List[str]] = None
    use_avatar: Optional[bool] = False


class AvatarCreditCheckoutRequest(BaseModel):
    session_token: str
    package: str
    success_url: str
    cancel_url: str


class AvatarActivateRequest(BaseModel):
    session_token: str

    @property
    def post_json(self):
        json = self.model_dump()
        json['scheduled_datetime'] = self.scheduled_time
        return json

    @computed_field
    @property
    def scheduled_time(self) -> str:
        return self.scheduled_datetime.isoformat()


class BulkUpdateRequest(BaseModel):
    post_ids: List[int]
    status: Optional[PostStatus] = None
    scheduled_datetime: Optional[datetime] = None


class BulkDeleteRequest(BaseModel):
    post_ids: List[int]


class UserSettingsRequest(BaseModel):
    email: str
    new_email: Optional[str] = None
    blog_url: Optional[str] = None
    sitemap_url: Optional[str] = None


class AuthInitRequest(BaseModel):
    email: str


class AuthVerifyRequest(BaseModel):
    email: str
    pin: str


class LogoutRequest(BaseModel):
    session_token: str


class CheckoutSessionRequest(BaseModel):
    session_token: str
    tier: str
    success_url: str
    cancel_url: str


class PortalSessionRequest(BaseModel):
    session_token: str
    return_url: str


class UserPreferencesRequest(BaseModel):
    session_token: str
    last_login_inactivate_delay: Optional[int] = 90
    auto_schedule_posts: bool = False


class LinkedInPasswordRequest(BaseModel):
    session_token: str
    linkedin_password: str


class TimezoneRequest(BaseModel):
    session_token: str
    timezone: str


class AdminFixVideoUrlsRequest(BaseModel):
    old_base: str
    new_base: str
    user_id: Optional[int] = None


class AdminRegenerateCarouselRequest(BaseModel):
    post_id: int
    user_id: int


class FutureForwardValues(IntEnum):
    Zero = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@router.get("/dashboard/stats/", responses={
    200: {"description": "Dashboard stats returned"},
    **{k: v for k, v in error_responses.items() if k in [400, 403]}
})
def get_dashboard_stats(email: str) -> ResponseModel:
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_id = get_user_id(email)
    if not user_id:
        raise HTTPException(status_code=403, detail="User not found")

    posts, _ = get_posts(user_id)
    now = datetime.now(timezone.utc)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = week_start.replace(day=week_start.day - week_start.weekday())

    scheduled_this_week = sum(
        1 for p in posts
        if p.get("status") in (PostStatus.APPROVED, PostStatus.PENDING)
        and p.get("scheduled_time") and p["scheduled_time"] >= week_start
    )
    pending_review = sum(1 for p in posts if p.get("status") == PostStatus.PENDING)
    posted_total = sum(1 for p in posts if p.get("status") == PostStatus.POSTED)

    stats: Dict[str, int] = {
        "scheduled_this_week": scheduled_this_week,
        "pending_review": pending_review,
        "posted_total": posted_total,
    }
    return ResponseModel(status_code=200, detail=stats)


@router.get("/activity/", responses={
    200: {"description": "Recent activity log returned"},
    **{k: v for k, v in error_responses.items() if k in [400, 403]}
})
def get_activity(email: str, limit: int = 20) -> ResponseModel:
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_id = get_user_id(email)
    if not user_id:
        raise HTTPException(status_code=403, detail="User not found")

    logs = get_recent_logs(user_id, limit=limit)
    serialized = [
        {
            "id": row["id"],
            "action_type": row["action_type"],
            "result": row["result"],
            "post_id": row["post_id"],
            "post_url": row["post_url"],
            "message": row["message"],
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        }
        for row in logs
    ]
    return ResponseModel(status_code=200, detail=serialized)


@router.put("/user/", responses={
    200: {"description": "User settings updated"},
    **{k: v for k, v in error_responses.items() if k in [400, 403, 404]}
})
def update_user_endpoint(settings: UserSettingsRequest) -> ResponseModel:
    if not settings.email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_id = get_user_id(settings.email)
    if not user_id:
        raise HTTPException(status_code=403, detail="User not found")

    if not any([settings.new_email, settings.blog_url, settings.sitemap_url]):
        return ResponseModel(status_code=200, detail="User settings unchanged")

    updated = update_user(user_id, email=settings.new_email, blog_url=settings.blog_url, sitemap_url=settings.sitemap_url)
    if not updated:
        raise HTTPException(status_code=404, detail="Update failed")
    return ResponseModel(status_code=200, detail="User updated successfully")


@router.post("/automate_reply_commenting", responses={
    200: {"description": "Post reply automation scheduled successfully"},
    **{k: v for k, v in error_responses.items() if k in [403, 404]}
})
def automate_reply_commenting_for_post_id(post_id: int, loop_for_duration: int = 60 * 60,
                                          future_forward: FutureForwardValues = Query(
                                              default=0,
                                              description="Forward index (0-5) to use for future calls",
                                              examples=[0, 1, 2, 3, 4, 5]
                                          )):
    user_id = get_post_user_id(post_id)
    if not user_id:
        raise HTTPException(status_code=403, detail="User Id for Post not found")

    try:
        base_kwargs = {
            'user_id': user_id,
            'post_id': post_id,
            'loop_for_duration': loop_for_duration,
            'future_forward': future_forward
        }
        automate_reply_commenting.apply_async(kwargs=base_kwargs)
        return ResponseModel(status_code=200, detail="Post automation reply successfully scheduled")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not schedule automation for post. Error: {e}")


@router.post("/schedule_post/", responses={
    200: {"description": "Post scheduled successfully"},
    **{k: v for k, v in error_responses.items() if k in [403, 404]}
})
def schedule_post(post: PostRequest) -> ResponseModel:
    user_id = get_user_id(post.email)
    if not user_id:
        raise HTTPException(status_code=403, detail="User not found")

    if insert_post(post.email, post.content, post.scheduled_datetime, post.post_type,
                   video_url=post.video_url, carousel_slides=post.carousel_slides):
        return ResponseModel(status_code=200, detail="Post scheduled successfully")
    else:
        raise HTTPException(status_code=404, detail="Could not schedule post")


@router.post("/create_weekly_content/", responses={
    200: {"description": "Weekly content created successfully"},
    **{k: v for k, v in error_responses.items() if k in [400]}
})
def create_weekly_content(user_id: int) -> ResponseModel:
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Chain: plan posts for the rest of the month first, then fill content for this week.
    # This ensures the user always has PLANNING rows before content generation runs.
    celery_chain(
        plan_content_for_user.si(user_id=user_id),
        auto_create_weekly_content.si(user_id=user_id),
    ).apply_async()
    return ResponseModel(status_code=200, detail="Weekly content created successfully")


@router.post("/invite_to_li_company_page/", responses={
    200: {"description": "Invite Users to LinkedIn Company Page"},
    **{k: v for k, v in error_responses.items() if k in [400]}
})
def invite_to_li_company_page(user_id: int) -> ResponseModel:
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    automate_invites_to_company_page_for_user.apply_async(
        kwargs={'user_id': user_id}, retry=True,
        retry_policy={'max_retries': 3, 'interval_start': 60, 'interval_step': 30}
    )
    return ResponseModel(status_code=200, detail="Process to invite to LinkedIn Company Page Started")


@router.post("/aws_test_get_my_profile/", responses={
    200: {"description": "Test Get My Profile on AWS"},
    **{k: v for k, v in error_responses.items() if k in [400]}
})
def aws_test_get_my_profile(user_id: int) -> ResponseModel:
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    test_get_my_profile.apply_async(kwargs={'user_id': user_id}, retry=True,
                                    retry_policy={'max_retries': 1})
    return ResponseModel(status_code=200, detail="Test Get My Profile on AWS Message Sent to Celery Queue")


@router.get('/user_id/', responses={
    200: {"description": "User ID retrieved successfully"},
    **{k: v for k, v in error_responses.items() if k in [400, 403]}
})
def get_user_id_from_email(email: str) -> ResponseModel:
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_id = get_user_id(email)
    if not user_id:
        raise HTTPException(status_code=403, detail="User not found")

    return ResponseModel(status_code=200, detail=user_id)


@router.get("/posts/", responses={
    200: {"description": "Posts retrieved successfully"},
    **{k: v for k, v in error_responses.items() if k in [400, 404]}
})
def get_posts_for_email(
    email: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    sort_order: str = Query(default='asc', pattern='^(asc|desc)$'),
    status_filter: Optional[str] = Query(default=None),
) -> ResponseModel:
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    offset = (page - 1) * page_size
    posts, total = get_post_by_email(
        email, limit=page_size, offset=offset,
        sort_order=sort_order, status_filter=status_filter
    )

    posts_list = [
        {
            "post_id": post["id"],
            "content": post["content"],
            "video_url": post["video_url"],
            "scheduled_time": post["scheduled_time"],
            "post_type": post["post_type"],
            "status": post["status"],
            "carousel_slides": _parse_slides(post.get("carousel_slides")),
        }
        for post in posts
    ]
    return ResponseModel(status_code=200, detail={
        "posts": posts_list,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/posts/bulk_update/", responses={
    200: {"description": "Posts updated successfully"},
    **{k: v for k, v in error_responses.items() if k in [400, 405]}
})
def bulk_update_posts_endpoint(request: BulkUpdateRequest) -> ResponseModel:
    if not request.post_ids:
        raise HTTPException(status_code=400, detail="post_ids is required")

    if bulk_update_posts(request.post_ids, status=request.status, scheduled_time=request.scheduled_datetime):
        return ResponseModel(status_code=200, detail="Posts updated successfully")
    else:
        raise HTTPException(status_code=405, detail="Posts could not be updated")


@router.delete("/posts/", responses={
    200: {"description": "Posts deleted (soft) successfully"},
    **{k: v for k, v in error_responses.items() if k in [400, 405]}
})
def delete_posts_endpoint(request: BulkDeleteRequest) -> ResponseModel:
    if not request.post_ids:
        raise HTTPException(status_code=400, detail="post_ids is required")

    if soft_delete_posts(request.post_ids):
        return ResponseModel(status_code=200, detail="Posts deleted successfully")
    else:
        raise HTTPException(status_code=405, detail="Posts could not be deleted")


@router.post("/update_post/", responses={
    200: {"description": "Post updated successfully"},
    **{k: v for k, v in error_responses.items() if k in [405]}
})
def update_post(post_id: int, post: PostRequest) -> ResponseModel:
    myprint(f"Received Post Request: {post}")

    if update_db_post(post.content, post.video_url, post.scheduled_datetime, post.post_type, post_id, post.status):
        return ResponseModel(status_code=200, detail="Post updated successful")
    else:
        raise HTTPException(status_code=405, detail="Post could not be updated")


def _find_asset_file(root: str, rel_path: str) -> str | None:
    """Resolve rel_path within root using OS directory entries.

    Each returned path comes from os.scandir() (server-controlled), so it is
    never derived from user-supplied input.  Traversal components (.. / .) and
    separator characters are rejected before any filesystem access.
    """
    parts = [p for p in rel_path.replace("\\", "/").split("/") if p]
    if not parts:
        return None
    for part in parts:
        if part in (".", "..") or os.sep in part:
            return None
    current = root
    for i, part in enumerate(parts):
        try:
            matched = next((e for e in os.scandir(current) if e.name == part), None)
        except OSError:
            return None
        if matched is None:
            return None
        is_last = i == len(parts) - 1
        if is_last:
            return matched.path if matched.is_file() else None
        if not matched.is_dir():
            return None
        current = matched.path   # descend into subdirectory
    return None


@router.get("/assets", response_model=None, responses={
    200: {"description": "Asset returned successfully"},
    206: {"description": "Asset returned successfully via stream"},
    **{k: v for k, v in error_responses.items() if k in [400, 404]}
})
def get_assets(file_name: str, content_type: Optional[str] = None,
               request: Optional[Any] = None) -> Union[ResponseModel, FileResponse, StreamingResponse]:
    if not file_name:
        raise HTTPException(status_code=400, detail="A File Name is required")

    # Resolve the file via a filesystem scan of the trusted assets_dir (CWE-22).
    # _find_asset_file returns OS-provided paths, never paths constructed from
    # user input, so the taint chain from file_name is broken entirely.
    file_path = _find_asset_file(assets_dir, file_name)
    if file_path is None:
        raise HTTPException(status_code=404, detail="File not found")

    myprint(f"File Path: {file_path}")
    myprint(f"Content Type: {content_type}")

    file_extension = get_file_extension_from_filepath(file_path)
    mim_type = get_file_mime_type(file_extension)

    if request:
        return range_requests_response(request, file_path=file_path, content_type=mim_type)
    else:
        return FileResponse(status_code=200, path=file_path, media_type=mim_type, content_disposition_type=content_type)


# LinkedIn OAuth initiation — builds the authorization URL and redirects user to LinkedIn
@router.post("/auth/email/init")
def auth_email_init(request: AuthInitRequest) -> ResponseModel:
    email = request.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_exists = bool(get_user_id(email))
    pin = generate_pin()
    pin_hash = hash_pin(pin, email)

    # Check bypass first so we skip DB + email entirely when no provider is configured
    _, bypassed = send_pin_email(email, pin, is_new_user=not user_exists, probe_only=True)
    if bypassed:
        # No email provider configured — create user + session immediately, skip PIN step
        user_id = get_user_id(email)
        is_new_user = user_id is None
        if is_new_user:
            user_id = add_user_by_email(email)
            if not user_id:
                raise HTTPException(status_code=500, detail="Could not create user record")
        session_token = create_session(user_id)
        if not session_token:
            raise HTTPException(status_code=500, detail="Could not create session")
        return ResponseModel(status_code=200, detail={
            "bypass": True,
            "session_token": session_token,
            "email": email,
            "is_new_user": is_new_user,
        })

    # Write PIN to DB BEFORE sending email — if send fails we can delete the row;
    # the reverse order would leave users with an unverifiable PIN in their inbox.
    if not create_pin_for_email(email, pin_hash):
        raise HTTPException(status_code=500, detail="Could not create PIN")

    sent, _ = send_pin_email(email, pin, is_new_user=not user_exists)
    if not sent:
        # Clean up the PIN row so the user can retry without waiting for expiry
        delete_pin_for_email(email)
        raise HTTPException(status_code=500, detail="Could not send PIN email — check email provider settings")

    return ResponseModel(status_code=200, detail={"bypass": False, "user_exists": user_exists, "message": "PIN sent to email"})


@router.post("/auth/email/verify")
def auth_email_verify(request: AuthVerifyRequest) -> ResponseModel:
    email = request.email.strip().lower()
    pin = request.pin.strip()
    if not email or not pin:
        raise HTTPException(status_code=400, detail="Email and PIN are required")

    pin_hash = hash_pin(pin, email)
    if not verify_pin_for_email(email, pin_hash):
        raise HTTPException(status_code=401, detail="Invalid or expired PIN")

    user_id = get_user_id(email)
    is_new_user = user_id is None
    if is_new_user:
        user_id = add_user_by_email(email)
        if not user_id:
            raise HTTPException(status_code=500, detail="Could not create user record")

    session_token = create_session(user_id)
    if not session_token:
        raise HTTPException(status_code=500, detail="Could not create session")

    return ResponseModel(
        status_code=200,
        detail={"session_token": session_token, "email": email, "is_new_user": is_new_user},
    )


@router.post("/auth/logout")
def auth_logout(request: LogoutRequest) -> ResponseModel:
    delete_session(request.session_token)
    return ResponseModel(status_code=200, detail="Logged out")


@router.get("/auth/session")
def auth_check_session(session_token: str) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    email = get_user_email(user_id)
    return ResponseModel(status_code=200, detail={"user_id": user_id, "email": email})


@router.get("/user/token_status")
def get_user_token_status(session_token: str) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    token_info = get_user_token_info(user_id)
    if not token_info or not token_info.get('access_token'):
        return ResponseModel(status_code=200, detail={
            "token_expiry_date": None,
            "is_expiring_soon": True,
            "is_expired": True,
            "refresh_attempted": False,
            "refresh_succeeded": False,
        })

    expiring_soon = is_token_expiring_soon(token_info)
    expired = is_token_expired(token_info)
    refresh_attempted = False
    refresh_succeeded = False

    if expiring_soon and token_info.get('refresh_token'):
        refresh_attempted = True
        refresh_succeeded, _ = attempt_token_refresh(user_id)
        if refresh_succeeded:
            token_info = get_user_token_info(user_id)
            expiring_soon = is_token_expiring_soon(token_info)
            expired = is_token_expired(token_info)

    expiry = get_token_expiry(token_info)
    return ResponseModel(status_code=200, detail={
        "token_expiry_date": expiry.isoformat() if expiry else None,
        "is_expiring_soon": expiring_soon,
        "is_expired": expired,
        "refresh_attempted": refresh_attempted,
        "refresh_succeeded": refresh_succeeded,
    })


@app.get("/auth/linkedin/", response_model=None, include_in_schema=False)
@router.get("/auth/linkedin/", response_model=None, include_in_schema=False)
def linkedin_auth_init(email: str = None, session_token: str = None) -> RedirectResponse:
    client = AuthClient(LI_CLIENT_ID, LI_CLIENT_SECRET, LI_REDIRECT_URL)
    # Embed the session_token in state so the callback can find the right user,
    # even when the LinkedIn account email differs from the login email.
    state = f"{LI_STATE_SALT}:{session_token}" if session_token else LI_STATE_SALT
    auth_url = client.generate_member_auth_url(
        state=state,
        scopes=["openid", "profile", "email", "w_member_social"]
    )
    return RedirectResponse(url=auth_url)


# LinkedIn OAuth callback lives outside /api since LinkedIn redirects here
@app.get("/auth/linkedin/callback", response_model=None)
def linkedin_callback(code: str, state: str = None) -> Union[ResponseModel, RedirectResponse]:
    from urllib.parse import urlencode

    def _account_redirect(params: dict) -> RedirectResponse:
        parsed_url = urlparse(LI_REDIRECT_URL)
        base_host = f"{parsed_url.scheme}://{parsed_url.netloc.split(':')[0]}"
        if os.environ.get('NGROK_CUSTOM_DOMAIN'):
            base_host = "https://" + os.environ.get('NGROK_CUSTOM_DOMAIN')
        return RedirectResponse(url=f"{base_host}/account?{urlencode(params)}")

    # State format: "{LI_STATE_SALT}:{session_token}" or just "{LI_STATE_SALT}"
    session_token_from_state: Optional[str] = None
    if state is not None:
        if ':' in state:
            salt_part, session_token_from_state = state.split(':', 1)
            if salt_part != LI_STATE_SALT:
                raise HTTPException(status_code=400, detail="Invalid state parameter")
        elif state != LI_STATE_SALT:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

    client = AuthClient(LI_CLIENT_ID, LI_CLIENT_SECRET, LI_REDIRECT_URL)
    try:
        access_token_response = client.exchange_auth_code_for_access_token(code)
    except (ResponseFormattingError, Exception) as exc:
        myprint(f"LinkedIn token exchange failed: {exc}")
        return _account_redirect({'li_error': 'token_exchange_failed'})

    myprint("Access token Response from api call")
    for key, value in access_token_response.__dict__.items():
        myprint(f"{key}: {value}")

    if not access_token_response.access_token:
        myprint("LinkedIn token exchange returned no access_token")
        return _account_redirect({'li_error': 'no_access_token'})

    try:
        restli_client = RestliClient()
        response = restli_client.get(
            resource_path='/userinfo',
            access_token=access_token_response.access_token,
        )
        myprint("Response from /userinfo api call:")
        for key, value in response.__dict__.items():
            myprint(f"{key}: {value}")
    except Exception as exc:
        myprint(f"LinkedIn /userinfo call failed: {exc}")
        return _account_redirect({'li_error': 'userinfo_failed'})

    user_email = response.entity.get('email', '')
    linked_sub_id = response.entity.get('sub', '')

    # Prefer updating the logged-in user's record directly (handles the case where
    # the LinkedIn account email differs from the app login email).
    user_id = get_session_user_id(session_token_from_state) if session_token_from_state else None
    if user_id:
        myprint(f"Updating LinkedIn token for session user_id={user_id}")
        update_user_linkedin_token(
            user_id,
            linked_sub_id,
            access_token_response.access_token,
            access_token_response.expires_in,
            access_token_response.refresh_token,
            access_token_response.refresh_token_expires_in,
            linkedin_email=user_email or None,
        )
    else:
        if not user_email:
            myprint("LinkedIn /userinfo returned no email and no valid session")
            return _account_redirect({'li_error': 'no_email'})
        myprint(f"No session in state — upserting by LinkedIn email {user_email}")
        add_user_with_access_token(
            user_email,
            linked_sub_id,
            access_token_response.access_token,
            access_token_response.expires_in,
            access_token_response.refresh_token,
            access_token_response.refresh_token_expires_in,
        )

    return _account_redirect({'email': user_email, 'li_connected': '1'})


@router.get("/user/settings")
def get_user_settings(session_token: str) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    subscription = get_user_subscription_info(user_id)
    preferences = get_user_preferences(user_id)
    blog_url = get_user_blog_url(user_id)
    sitemap_url = get_user_sitemap_url(user_id)

    def _iso(dt):
        return dt.isoformat() if dt else None

    return ResponseModel(status_code=200, detail={
        "subscription": {
            "status": subscription.get("subscription_status") if subscription else None,
            "tier": subscription.get("subscription_tier") if subscription else None,
            "trial_started_at": _iso(subscription.get("trial_started_at")) if subscription else None,
            "trial_ends_at": _iso(subscription.get("trial_ends_at")) if subscription else None,
            "stripe_customer_id": subscription.get("stripe_customer_id") if subscription else None,
        } if subscription else None,
        "preferences": {
            "last_login_inactivate_delay": preferences.get("last_login_inactivate_delay") if preferences else 90,
            "auto_schedule_posts": bool(preferences.get("auto_schedule_posts")) if preferences else False,
        } if preferences else None,
        "blog_url": blog_url,
        "sitemap_url": sitemap_url,
    })


@router.put("/user/settings")
def update_user_settings_endpoint(request: UserPreferencesRequest) -> ResponseModel:
    user_id = get_session_user_id(request.session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    updated = update_user_preferences(
        user_id,
        inactivate_delay=request.last_login_inactivate_delay,
        auto_schedule_posts=request.auto_schedule_posts,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Could not update preferences")
    return ResponseModel(status_code=200, detail="Preferences updated")


@router.put("/user/linkedin-password")
def update_linkedin_password(request: LinkedInPasswordRequest) -> ResponseModel:
    """Store the user's LinkedIn password for Selenium-driven automation tasks.
    The value is stored as-is because Selenium must type it into the browser.
    It is never returned in any response payload.
    """
    user_id = get_session_user_id(request.session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if not request.linkedin_password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    saved = update_user_linkedin_password(user_id, request.linkedin_password)
    if not saved:
        raise HTTPException(status_code=500, detail="Could not save LinkedIn password")
    return ResponseModel(status_code=200, detail="LinkedIn password saved")


@router.get("/user/timezone")
def get_user_timezone_endpoint(session_token: str) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return ResponseModel(status_code=200, detail={"timezone": get_user_timezone(user_id)})


@router.put("/user/timezone")
def update_user_timezone_endpoint(request: TimezoneRequest) -> ResponseModel:
    from zoneinfo import available_timezones, ZoneInfoNotFoundError
    user_id = get_session_user_id(request.session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if request.timezone not in available_timezones():
        raise HTTPException(status_code=422, detail=f"Unknown timezone: {request.timezone!r}")
    saved = update_user_timezone(user_id, request.timezone)
    if not saved:
        raise HTTPException(status_code=500, detail="Could not update timezone")
    return ResponseModel(status_code=200, detail="Timezone updated")


@router.post("/billing/create-checkout-session")
def billing_create_checkout_session(request: CheckoutSessionRequest) -> ResponseModel:
    user_id = get_session_user_id(request.session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    subscription = get_user_subscription_info(user_id)
    stripe_customer_id = subscription.get("stripe_customer_id") if subscription else None
    if not stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer record — contact support")

    from cqc_lem.utilities.stripe_util import create_checkout_session, upgrade_subscription

    # If the user already has an active subscription, modify it in-place rather than
    # creating a new Checkout session — which would register a second subscription.
    existing_sub_id = subscription.get("stripe_subscription_id") if subscription else None
    existing_status = subscription.get("subscription_status") if subscription else None
    if existing_sub_id and existing_status in ("active", "trial"):
        upgraded = upgrade_subscription(existing_sub_id, request.tier)
        if upgraded:
            # No redirect needed — Stripe webhook will fire subscription.updated and sync DB
            return ResponseModel(status_code=200, detail={"checkout_url": None, "upgraded": True})
        myprint(
            f"In-place upgrade failed for sub={existing_sub_id}; falling back to checkout session"
        )

    url = create_checkout_session(
        stripe_customer_id,
        request.tier,
        request.success_url,
        request.cancel_url,
    )
    if not url:
        raise HTTPException(status_code=500, detail="Could not create Stripe checkout session")
    return ResponseModel(status_code=200, detail={"checkout_url": url, "upgraded": False})


@router.post("/billing/create-portal-session")
def billing_create_portal_session(request: PortalSessionRequest) -> ResponseModel:
    user_id = get_session_user_id(request.session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    subscription = get_user_subscription_info(user_id)
    stripe_customer_id = subscription.get("stripe_customer_id") if subscription else None
    if not stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer record — contact support")

    from cqc_lem.utilities.stripe_util import create_portal_session
    url = create_portal_session(stripe_customer_id, request.return_url)
    if not url:
        raise HTTPException(status_code=500, detail="Could not create Stripe portal session")
    return ResponseModel(status_code=200, detail={"portal_url": url})


@router.post("/billing/webhook")
async def billing_webhook(request: Request) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    from cqc_lem.utilities.stripe_util import (
        validate_webhook, get_subscription_tier_from_price, stripe_status_to_db,
    )
    event = validate_webhook(payload, sig_header)
    if event is None:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    myprint(f"Stripe webhook received: {event_type}")

    # --- Subscription lifecycle events ---
    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        stripe_customer_id = data.get("customer")
        stripe_subscription_id = data.get("id")
        if not stripe_customer_id:
            myprint(f"Webhook {event_type} missing customer field — skipping")
            return {"received": True}
        sub_status = data.get("status", "")
        db_status = stripe_status_to_db(sub_status)

        # Determine tier from the first line item's price
        price_id = None
        items = data.get("items", {}).get("data", [])
        if items:
            price_id = items[0].get("price", {}).get("id")
        tier = get_subscription_tier_from_price(price_id) if price_id else None

        # Period end (Unix timestamp → datetime)
        period_end_ts = data.get("current_period_end")
        period_end = (
            datetime.fromtimestamp(period_end_ts, tz=timezone.utc) if period_end_ts else None
        )

        myprint(
            f"Subscription {stripe_subscription_id}: stripe_status={sub_status} "
            f"→ db_status={db_status}, tier={tier}, period_end={period_end}"
        )
        update_subscription_from_stripe(
            stripe_customer_id, db_status, tier, stripe_subscription_id, period_end
        )

    elif event_type == "customer.subscription.deleted":
        stripe_customer_id = data.get("customer")
        stripe_subscription_id = data.get("id")
        if not stripe_customer_id:
            myprint(f"Webhook {event_type} missing customer field — skipping")
            return {"received": True}
        myprint(f"Subscription {stripe_subscription_id} deleted for customer {stripe_customer_id}")
        # tier=None preserves the historical tier in the DB
        update_subscription_from_stripe(
            stripe_customer_id, "cancelled", None, stripe_subscription_id
        )

    # --- Invoice / payment events (fired on every billing cycle renewal) ---
    elif event_type == "invoice.payment_succeeded":
        stripe_customer_id = data.get("customer")
        stripe_subscription_id = data.get("subscription")
        if not stripe_customer_id:
            myprint(f"Webhook {event_type} missing customer field — skipping")
            return {"received": True}
        if stripe_subscription_id:
            myprint(
                f"Invoice payment succeeded for customer={stripe_customer_id}, "
                f"subscription={stripe_subscription_id} — marking active"
            )
            # Re-fetch the subscription to get the current tier and period end
            from cqc_lem.utilities.stripe_util import fetch_subscription
            sub = fetch_subscription(stripe_subscription_id)
            if sub:
                price_id = None
                items = sub.get("items", {}).get("data", [])
                if items:
                    price_id = items[0].get("price", {}).get("id")
                tier = get_subscription_tier_from_price(price_id) if price_id else None
                period_end_ts = sub.get("current_period_end")
                period_end = datetime.fromtimestamp(period_end_ts, tz=timezone.utc) if period_end_ts else None
                update_subscription_from_stripe(
                    stripe_customer_id, "active", tier, stripe_subscription_id, period_end
                )

    elif event_type == "invoice.payment_failed":
        stripe_customer_id = data.get("customer")
        stripe_subscription_id = data.get("subscription")
        if not stripe_customer_id:
            myprint(f"Webhook {event_type} missing customer field — skipping")
            return {"received": True}
        if stripe_subscription_id:
            myprint(
                f"Invoice payment FAILED for customer={stripe_customer_id}, "
                f"subscription={stripe_subscription_id} — marking past_due"
            )
            # tier=None preserves existing tier; status → past_due
            update_subscription_from_stripe(
                stripe_customer_id, "past_due", None, stripe_subscription_id
            )

    elif event_type == "checkout.session.completed":
        meta = data.get("metadata", {})
        if meta.get("type") == "avatar_credits":
            # Only credit on confirmed card payment — async methods (e.g. bank transfer)
            # may fire this event before funds clear.
            if data.get("payment_status") != "paid":
                myprint(
                    f"checkout.session.completed: payment_status={data.get('payment_status')} "
                    f"— not yet paid, skipping credit grant"
                )
                return {"received": True}

            stripe_customer_id = data.get("customer")
            stripe_session_id = data.get("id")
            credits = int(meta.get("credits", 0))
            package = meta.get("package", "unknown")

            if not stripe_customer_id or credits <= 0:
                myprint(f"Avatar credits webhook: missing customer or zero credits — skipping")
                return {"received": True}

            # Idempotency: Stripe may retry — skip if credits already granted for this session.
            if get_avatar_credit_ledger_entry_by_session(stripe_session_id):
                myprint(f"Avatar credits already granted for session={stripe_session_id} — skipping duplicate")
                return {"received": True}

            user_row = get_user_by_stripe_customer_id(stripe_customer_id)
            if user_row:
                add_avatar_credits(
                    user_row["id"],
                    credits,
                    f"purchase_{package}",
                    stripe_session_id,
                )
                myprint(
                    f"Added {credits} avatar credit(s) for user_id={user_row['id']} "
                    f"via session={stripe_session_id}"
                )
            else:
                myprint(f"Avatar credits webhook: no user found for customer={stripe_customer_id}")

    elif event_type == "charge.refunded":
        payment_intent_id = data.get("payment_intent")
        stripe_customer_id = data.get("customer")
        amount = data.get("amount", 0)
        amount_refunded = data.get("amount_refunded", 0)

        if not payment_intent_id or not stripe_customer_id:
            myprint("charge.refunded: missing payment_intent or customer — skipping")
            return {"received": True}

        # Only deduct credits for a full refund — partial refunds don't map cleanly to credits.
        if amount_refunded < amount:
            myprint(
                f"charge.refunded: partial refund ({amount_refunded}/{amount} cents) "
                f"for customer={stripe_customer_id} — no credit adjustment"
            )
            return {"received": True}

        # Find the checkout session that generated this charge to check its metadata.
        from cqc_lem.utilities.stripe_util import get_checkout_session_by_payment_intent
        session = get_checkout_session_by_payment_intent(payment_intent_id)
        if not session:
            myprint(f"charge.refunded: no checkout session found for payment_intent={payment_intent_id}")
            return {"received": True}

        session_meta = session.get("metadata", {})
        if session_meta.get("type") != "avatar_credits":
            myprint(f"charge.refunded: not an avatar credits charge — ignoring")
            return {"received": True}

        stripe_session_id = session.get("id")
        original_entry = get_avatar_credit_ledger_entry_by_session(stripe_session_id)
        if not original_entry:
            myprint(f"charge.refunded: no credit ledger entry found for session={stripe_session_id} — nothing to deduct")
            return {"received": True}

        # Guard against double-refund: check if a refund entry already exists for this session.
        user_row = get_user_by_stripe_customer_id(stripe_customer_id)
        if not user_row:
            myprint(f"charge.refunded: no user found for customer={stripe_customer_id}")
            return {"received": True}

        credits_to_deduct = original_entry["delta"]
        add_avatar_credits(
            user_row["id"],
            -credits_to_deduct,
            f"refund_{stripe_session_id}",
            stripe_session_id=None,
        )
        myprint(
            f"Deducted {credits_to_deduct} avatar credit(s) for user_id={user_row['id']} "
            f"due to full refund of session={stripe_session_id}"
        )

    else:
        myprint(f"Stripe webhook event ignored: {event_type}")

    return {"received": True}


# ---------------------------------------------------------------------------
# Avatar endpoints
# ---------------------------------------------------------------------------

@router.get("/avatar/credits", responses={
    200: {"description": "Credit balance and active avatar returned"},
    **{k: v for k, v in error_responses.items() if k in [401]}
})
def get_avatar_credits_endpoint(session_token: str) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    balance = get_avatar_credit_balance(user_id)
    active = get_active_avatar(user_id)
    return ResponseModel(status_code=200, detail={"balance": balance, "active_avatar": active})


@router.post("/avatar/credits/checkout", responses={
    200: {"description": "Stripe checkout URL returned"},
    **{k: v for k, v in error_responses.items() if k in [400, 401]}
})
def avatar_credits_checkout(request: AvatarCreditCheckoutRequest) -> ResponseModel:
    user_id = get_session_user_id(request.session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    subscription = get_user_subscription_info(user_id)
    stripe_customer_id = subscription.get("stripe_customer_id") if subscription else None
    if not stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer record — contact support")

    from cqc_lem.utilities.stripe_util import create_avatar_credits_checkout, AVATAR_CREDIT_PACKAGES
    if request.package not in AVATAR_CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail=f"Unknown package '{request.package}'")

    url = create_avatar_credits_checkout(
        stripe_customer_id, request.package, request.success_url, request.cancel_url
    )
    if not url:
        raise HTTPException(status_code=500, detail="Could not create Stripe checkout session")
    return ResponseModel(status_code=200, detail={"checkout_url": url})


@router.post("/avatar/training", responses={
    200: {"description": "Training started"},
    **{k: v for k, v in error_responses.items() if k in [400, 401, 402]}
})
async def start_avatar_training_endpoint(
    session_token: str = Form(...),
    trigger_word: str = Form(...),
    photos: UploadFile = File(...),
) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    balance = get_avatar_credit_balance(user_id)
    if balance < 1:
        raise HTTPException(status_code=402, detail="Insufficient avatar credits. Purchase credits to train a new avatar.")

    zip_bytes = await photos.read()
    if not zip_bytes:
        raise HTTPException(status_code=400, detail="No file data received")

    _MAX_ZIP_BYTES = 50 * 1024 * 1024  # 50 MB compressed
    _MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB uncompressed guard
    if len(zip_bytes) > _MAX_ZIP_BYTES:
        raise HTTPException(status_code=413, detail="ZIP file too large (max 50 MB)")
    import io
    import zipfile as _zipfile
    try:
        with _zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            total_uncompressed = sum(entry.file_size for entry in zf.infolist())
        if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
            raise HTTPException(status_code=413, detail="ZIP contents too large (max 200 MB uncompressed)")
    except _zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP")

    from cqc_lem.utilities.avatar.replicate_avatar import start_avatar_training
    try:
        training_id = start_avatar_training(user_id, zip_bytes, trigger_word)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not start training: {exc}")

    deduct_avatar_credit(user_id, training_id)
    db_id = insert_avatar_training(user_id, training_id, trigger_word)
    return ResponseModel(status_code=200, detail={"training_id": training_id, "db_id": db_id})


@router.get("/avatar/trainings", responses={
    200: {"description": "Avatar trainings listed"},
    **{k: v for k, v in error_responses.items() if k in [401]}
})
def list_avatar_trainings(session_token: str) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    trainings = get_avatar_trainings(user_id)
    return ResponseModel(status_code=200, detail=trainings)


@router.get("/avatar/training/{avatar_db_id}/status", responses={
    200: {"description": "Training status synced"},
    **{k: v for k, v in error_responses.items() if k in [401, 404]}
})
def sync_avatar_training_status(avatar_db_id: int, session_token: str) -> ResponseModel:
    user_id = get_session_user_id(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    trainings = get_avatar_trainings(user_id)
    match = next((t for t in trainings if t["id"] == avatar_db_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Training not found")

    if match["status"] in ("succeeded", "failed", "canceled"):
        return ResponseModel(status_code=200, detail=match)

    from cqc_lem.utilities.avatar.replicate_avatar import poll_training_status
    new_status, model_ref = poll_training_status(match["training_id"])
    update_avatar_training_status(match["training_id"], new_status, model_ref)
    match["status"] = new_status
    if model_ref:
        match["model_ref"] = model_ref
    return ResponseModel(status_code=200, detail=match)


@router.put("/avatar/training/{avatar_db_id}/activate", responses={
    200: {"description": "Avatar activated"},
    **{k: v for k, v in error_responses.items() if k in [400, 401, 404]}
})
def activate_avatar(avatar_db_id: int, request: AvatarActivateRequest) -> ResponseModel:
    user_id = get_session_user_id(request.session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    trainings = get_avatar_trainings(user_id)
    match = next((t for t in trainings if t["id"] == avatar_db_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Training not found")
    if match["status"] != "succeeded":
        raise HTTPException(status_code=400, detail="Only succeeded trainings can be activated")

    if set_active_avatar(user_id, avatar_db_id):
        return ResponseModel(status_code=200, detail="Avatar activated")
    raise HTTPException(status_code=500, detail="Could not activate avatar")


# ---------------------------------------------------------------------------
# Admin endpoints — require X-Admin-Secret header matching ADMIN_SECRET env var
# ---------------------------------------------------------------------------

def _require_admin(x_admin_secret: Optional[str] = Header(default=None)) -> None:
    if not ADMIN_SECRET or x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/admin/fix-video-urls", responses={
    200: {"description": "Video URLs updated"},
    403: {"description": "Forbidden"},
})
def admin_fix_video_urls(
    request: AdminFixVideoUrlsRequest,
    x_admin_secret: Optional[str] = Header(default=None),
) -> ResponseModel:
    _require_admin(x_admin_secret)
    updated = replace_video_url_base(request.old_base, request.new_base, request.user_id)
    myprint(f"admin/fix-video-urls: replaced {updated} row(s) — {request.old_base!r} → {request.new_base!r}")
    return ResponseModel(status_code=200, detail={"updated_rows": updated})


@router.post("/admin/regenerate-carousel", responses={
    200: {"description": "Carousel regenerated"},
    403: {"description": "Forbidden"},
    404: {"description": "Post not found or not a carousel"},
})
def admin_regenerate_carousel(
    request: AdminRegenerateCarouselRequest,
    x_admin_secret: Optional[str] = Header(default=None),
) -> ResponseModel:
    _require_admin(x_admin_secret)

    post_type = get_post_type(request.post_id)
    if post_type != PostType.CAROUSEL:
        raise HTTPException(status_code=404, detail="Post not found or not a carousel post")

    stage = get_post_buyer_stage(request.post_id) or "awareness"
    from cqc_lem.app.run_content_plan import create_carousel_content
    try:
        new_content = create_carousel_content(request.user_id, stage=stage, post_id=request.post_id)
        from cqc_lem.utilities.db import update_db_post_content
        update_db_post_content(request.post_id, new_content)
    except Exception as exc:
        myprint(f"admin/regenerate-carousel: failed for post_id={request.post_id} — {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    myprint(f"admin/regenerate-carousel: regenerated post_id={request.post_id}")
    return ResponseModel(status_code=200, detail={"post_id": request.post_id, "content_preview": new_content[:120]})


# Register the /api router
app.include_router(router)

# Backward-compat redirect: /assets?file_name=... → /api/assets?file_name=...
# Must be registered before the SPA StaticFiles mount so it takes priority.
@app.get("/assets", include_in_schema=False)
async def assets_compat_redirect(request: Request, file_name: Optional[str] = None):
    if file_name:
        return RedirectResponse(url=f"/api/assets?{request.url.query}", status_code=301)
    raise HTTPException(status_code=404)

# Serve the React SPA for all non-API routes (must come after include_router)
if os.path.isdir(_ui_dist):
    _spa_index = os.path.join(_ui_dist, "index.html")

    # Serve static assets (JS/CSS/icons) from the dist root
    app.mount("/assets", StaticFiles(directory=os.path.join(_ui_dist, "assets")), name="spa-assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    def serve_spa(full_path: str):
        with open(_spa_index) as fh:
            return HTMLResponse(content=fh.read())


def send_bytes_range_requests(
        file_path: str, start: int, end: int, chunk_size: int = 10_000
):
    with open(file_path, "rb") as f:
        f.seek(start)
        while (pos := f.tell()) <= end:
            read_size = min(chunk_size, end + 1 - pos)
            yield f.read(read_size)


def _get_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    def _invalid_range():
        return HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=f"Invalid request range (Range:{range_header!r})",
        )

    try:
        h = range_header.replace("bytes=", "").split("-")
        start = int(h[0]) if h[0] != "" else 0
        end = int(h[1]) if h[1] != "" else file_size - 1
    except ValueError:
        raise _invalid_range()

    if start > end or start < 0 or end > file_size - 1:
        raise _invalid_range()
    return start, end


def range_requests_response(
        request: Request, file_path: str, content_type: str
) -> StreamingResponse:
    file_size = os.stat(file_path).st_size
    range_header = request.headers.get("range")

    headers = {
        "content-type": content_type,
        "accept-ranges": "bytes",
        "content-encoding": "identity",
        "content-length": str(file_size),
        "access-control-expose-headers": (
            "content-type, accept-ranges, content-length, "
            "content-range, content-encoding"
        ),
    }
    start = 0
    end = file_size - 1
    status_code = status.HTTP_200_OK

    if range_header is not None:
        start, end = _get_range_header(range_header, file_size)
        size = end - start + 1
        headers["content-length"] = str(size)
        headers["content-range"] = f"bytes {start}-{end}/{file_size}"
        status_code = status.HTTP_206_PARTIAL_CONTENT

    return StreamingResponse(
        send_bytes_range_requests(file_path, start, end),
        headers=headers,
        status_code=status_code,
    )
