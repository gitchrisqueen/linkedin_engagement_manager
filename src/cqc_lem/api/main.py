import os
import time
from datetime import datetime
from enum import IntEnum
from typing import BinaryIO, Dict, List, Union
from typing import Optional, Any
from urllib.parse import urlparse, urlunparse

from cqc_lem import assets_dir
from cqc_lem.app.aws_test_celery_task import test_get_my_profile
from cqc_lem.app.run_automation import automate_invites_to_company_page_for_user, automate_reply_commenting
from cqc_lem.app.run_content_plan import auto_create_weekly_content
from cqc_lem.utilities.db import (
    insert_post, get_post_by_email, get_user_id, update_db_post, get_post_user_id,
    add_user_with_access_token, update_user, PostType, PostStatus, get_posts,
    get_recent_logs,
)
from cqc_lem.utilities.env_constants import LI_CLIENT_ID, LI_CLIENT_SECRET, LI_REDIRECT_URL, LI_STATE_SALT
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.mime_type_helper import get_file_mime_type
from cqc_lem.utilities.observability import track_api_call
from cqc_lem.utilities.utils import get_file_extension_from_filepath
from fastapi import FastAPI, HTTPException, Request, status, APIRouter
from fastapi import Query
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from linkedin_api.clients.auth.client import AuthClient
from linkedin_api.clients.restli.client import RestliClient
from pydantic import BaseModel, computed_field

app = FastAPI()

# All API routes live under /api so the React client's baseURL: '/api' works
router = APIRouter(prefix="/api")


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    track_api_call(
        route=request.url.path,
        method=request.method,
        status_code=response.status_code,
        latency_ms=int((time.time() - start) * 1000),
    )
    return response


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


class PostRequest(BaseModel):
    content: str
    video_url: Optional[str] = None
    post_type: Optional[PostType] = PostType.TEXT
    scheduled_datetime: datetime
    email: Optional[str] = None
    status: Optional[PostStatus] = PostStatus.PENDING

    @property
    def post_json(self):
        json = self.model_dump()
        json['scheduled_datetime'] = self.scheduled_time
        return json

    @computed_field
    @property
    def scheduled_time(self) -> str:
        return self.scheduled_datetime.isoformat()


class UserSettingsRequest(BaseModel):
    email: str
    new_email: Optional[str] = None
    blog_url: Optional[str] = None
    sitemap_url: Optional[str] = None


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

    posts = get_posts(user_id) or []
    now = datetime.now()
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

    if insert_post(post.email, post.content, post.scheduled_datetime, post.post_type):
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

    kwargs = {'user_id': user_id}
    auto_create_weekly_content.apply_async(kwargs=kwargs, retry=True,
                                           retry_policy={'max_retries': 1})
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
def get_posts_for_email(email: str) -> ResponseModel:
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    posts = get_post_by_email(email)
    if not posts:
        raise HTTPException(status_code=404, detail="No posts found for the given email")

    posts_list = [
        {
            "post_id": post["id"],
            "content": post["content"],
            "video_url": post["video_url"],
            "scheduled_time": post["scheduled_time"],
            "post_type": post["post_type"],
            "status": post['status'],
        }
        for post in posts
    ]
    return ResponseModel(status_code=200, detail=posts_list)


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


@router.get("/assets", response_model=None, responses={
    200: {"description": "Asset returned successfully"},
    206: {"description": "Asset returned successfully via stream"},
    **{k: v for k, v in error_responses.items() if k in [400, 404]}
})
def get_assets(file_name: str, content_type: Optional[str] = None,
               request: Optional[Any] = None) -> Union[ResponseModel, FileResponse, StreamingResponse]:
    if not file_name:
        raise HTTPException(status_code=400, detail="A File Name is required")

    file_path = os.path.join(assets_dir, file_name)
    myprint(f"File Path: {file_path}")
    myprint(f"Content Type: {content_type}")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_extension = get_file_extension_from_filepath(file_path)
    mim_type = get_file_mime_type(file_extension)

    if request:
        return range_requests_response(request, file_path=file_path, content_type=mim_type)
    else:
        return FileResponse(status_code=200, path=file_path, media_type=mim_type, content_disposition_type=content_type)


# LinkedIn OAuth initiation — builds the authorization URL and redirects user to LinkedIn
@app.get("/auth/linkedin/", response_model=None, include_in_schema=False)
@router.get("/auth/linkedin/", response_model=None, include_in_schema=False)
def linkedin_auth_init(email: str = None) -> RedirectResponse:
    client = AuthClient(LI_CLIENT_ID, LI_CLIENT_SECRET, LI_REDIRECT_URL)
    auth_url = client.generate_member_auth_url(
        state=LI_STATE_SALT,
        scopes=["openid", "profile", "email", "w_member_social"]
    )
    return RedirectResponse(url=auth_url)


# LinkedIn OAuth callback lives outside /api since LinkedIn redirects here
@app.get("/auth/linkedin/callback", response_model=None)
def linkedin_callback(code: str, state: str = None) -> Union[ResponseModel, RedirectResponse]:
    if state is not None and state != LI_STATE_SALT:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    resource_path = '/userinfo'
    client = AuthClient(LI_CLIENT_ID, LI_CLIENT_SECRET, LI_REDIRECT_URL)
    access_token_response = client.exchange_auth_code_for_access_token(code)

    myprint("Access token Response from api call")
    for key, value in access_token_response.__dict__.items():
        myprint(f"{key}: {value}")

    restli_client = RestliClient()
    response = restli_client.get(
        resource_path=resource_path,
        access_token=access_token_response.access_token,
    )

    myprint(f"Response from {resource_path} api call:")
    for key, value in response.__dict__.items():
        myprint(f"{key}: {value}")

    add_user_with_access_token(
        response.entity['email'],
        response.entity['sub'],
        access_token_response.access_token,
        access_token_response.expires_in,
        access_token_response.refresh_token,
        access_token_response.refresh_token_expires_in,
    )

    # Redirect to React account page, passing the authenticated email so the
    # frontend can persist it to localStorage without requiring the user to re-type it.
    user_email = response.entity.get('email', '')
    from urllib.parse import quote, urlencode
    qs = urlencode({'email': user_email, 'li_connected': '1'}) if user_email else 'li_connected=1'

    parsed_url = urlparse(LI_REDIRECT_URL)
    base_host = f"{parsed_url.scheme}://{parsed_url.netloc.split(':')[0]}"

    if os.environ.get('NGROK_CUSTOM_DOMAIN'):
        base_host = "https://" + os.environ.get('NGROK_CUSTOM_DOMAIN')

    final_redirect_url = f"{base_host}/account?{qs}"

    return RedirectResponse(url=final_redirect_url)


# Register the /api router
app.include_router(router)

# Serve the React SPA for all non-API routes (must come after include_router)
if os.path.isdir(_ui_dist):
    _spa_index = os.path.join(_ui_dist, "index.html")

    # Serve static assets (JS/CSS/icons) from the dist root
    app.mount("/assets", StaticFiles(directory=os.path.join(_ui_dist, "assets")), name="spa-assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    def serve_spa(full_path: str):
        return HTMLResponse(content=open(_spa_index).read())


def send_bytes_range_requests(
        file_obj: BinaryIO, start: int, end: int, chunk_size: int = 10_000
):
    with file_obj as f:
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
        send_bytes_range_requests(open(file_path, mode="rb"), start, end),
        headers=headers,
        status_code=status_code,
    )
