import os
import time
from datetime import datetime
from typing import BinaryIO, Union
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from linkedin_api.clients.auth.client import AuthClient
from linkedin_api.clients.restli.client import RestliClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, computed_field

from cqc_lem import assets_dir
from cqc_lem.app.run_content_plan import auto_create_weekly_content
from cqc_lem.utilities.db import insert_post, get_post_by_email, get_user_id, update_db_post, \
    add_user_with_access_token, PostType, PostStatus
from cqc_lem.utilities.env_constants import CODE_TRACING
from cqc_lem.utilities.jaeger_tracer_helper import get_jaeger_tracer
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.mime_type_helper import get_file_mime_type
from cqc_lem.utilities.utils import get_file_extension_from_filepath

app = FastAPI()


if CODE_TRACING:
    tracer = get_jaeger_tracer("api", __name__)
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

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
        # Add Timezone to scheduled_datetime
        time.tzset()
        return self.scheduled_datetime.isoformat()


@app.post("/schedule_post/", responses={
    200: {"description": "Post scheduled successfully"},
    **{k: v for k, v in error_responses.items() if k in [403, 404]}
})
def schedule_post(post: PostRequest) -> ResponseModel:
    """Endpoint to schedule a post."""

    user_id = get_user_id(post.email)

    if not user_id:
        raise HTTPException(status_code=403, detail="User not found")

    if insert_post(post.email, post.content, post.scheduled_time, post.post_type):
        return ResponseModel(status_code=200, detail="Post scheduled successfully")
    else:
        raise HTTPException(status_code=404, detail="Could not schedule post")


# app endpoint to create user weekly content using their user_id
@app.post("/create_weekly_content/", responses={
    200: {"description": "Weekly content created successfully"},
    **{k: v for k, v in error_responses.items() if k in [ 400]}
})
def create_weekly_content(user_id: int) -> ResponseModel:
    """Endpoint to create weekly content for a user."""
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    kwargs = {'user_id': user_id}
    # Call the function to create the weekly content
    auto_create_weekly_content.apply_async(kwargs=kwargs, retry=True,
                                    retry_policy={
                                        'max_retries': 1,
                                    })


    return ResponseModel(status_code=200, detail="Weekly content created successfully")



@app.get('/user_id/', responses={
    200: {"description": "User ID retrieved successfully"},
    **{k: v for k, v in error_responses.items() if k in [400, 403]}
})
def get_user_id_from_email(email: str) -> ResponseModel:
    """Endpoint to get user id by email."""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_id = get_user_id(email)

    if not user_id:
        raise HTTPException(status_code=403, detail="User not found")

    return ResponseModel(status_code=200, detail=user_id)


@app.get("/posts/", responses={
    200: {"description": "Post scheduled successfully"},
    **{k: v for k, v in error_responses.items() if k in [400, 404]}
})
def get_posts(email: str) -> ResponseModel:
    """Endpoint to get posts by email."""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    posts = get_post_by_email(email)
    if not posts:
        raise HTTPException(status_code=404, detail="No posts found for the given email")

    # Convert posts to a list of dictionaries
    posts_list = [{"post_id": post["id"], "content": post["content"], "video_url": post["video_url"],
                   "scheduled_time": post["scheduled_time"],
                   "post_type": post["post_type"], "status": post['status']} for post in posts]

    return ResponseModel(status_code=200, detail=posts_list)


@app.post("/update_post/", responses={
    200: {"description": "Post updated successfully"},
    **{k: v for k, v in error_responses.items() if k in [405]}

})
def update_post(post_id: int, post: PostRequest) -> ResponseModel:
    """Endpoint to update a post."""

    print(f"Received Post Request: {post}")

    if update_db_post(post.content, post.video_url, post.scheduled_time, post.post_type, post_id, post.status):
        return ResponseModel(status_code=200, detail="Post updated successful")
    else:
        raise HTTPException(status_code=405, detail="Post could not be updated")


@app.get("/auth/linkedin/callback", response_model=None)
def linkedin_callback(code: str, state: str = None) -> Union[ResponseModel, RedirectResponse]:
    """ Handle LinkedIn OAuth callback and retrieve user details"""

    # Verify the state parame matches the state from teh environment variable
    if state is not None and state != os.getenv("LI_STATE_SALT"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    else:
        # Get needed environment variables
        client_id = os.getenv("LI_CLIENT_ID")
        client_secret = os.getenv("LI_CLIENT_SECRET")
        redirect_url = os.getenv("LI_REDIRECT_URL")
        resource_path = os.getenv("LI_USERINFO_RESOURCE")

        #  Exchange code for access token
        client = AuthClient(client_id, client_secret, redirect_url)
        access_token_response = client.exchange_auth_code_for_access_token(code)

        myprint("Access token Response from api call")
        for key, value in access_token_response.__dict__.items():
            myprint(f"{key}: {value}")

        # Get the user email using access token

        restli_client = RestliClient()

        response = restli_client.get(
            resource_path=resource_path,
            access_token=access_token_response.access_token,
            # query_params={"fields": "id,firstName:(localized),lastName, emailAddress"},
        )

        myprint(f"Response from {resource_path} api call:")
        for key, value in response.__dict__.items():
            myprint(f"{key}: {value}")

        # Update the database with user email and access token
        add_user_with_access_token(response.entity['email'],
                                   response.entity['sub'],
                                   access_token_response.access_token,
                                   access_token_response.expires_in,
                                   access_token_response.refresh_token,
                                   access_token_response.refresh_token_expires_in)

        # Redirect the user to the main Streamlit app from env variable
        streamlit_url = os.environ.get('NGROK_CUSTOM_DOMAIN')
        return RedirectResponse(
            url=f"https://{streamlit_url}")  # TODO: Figure out better redirect. Should we just close the window


@app.get("/assets", response_model=None, responses={
    200: {"description": "Asset returned successfully"},
    206: {"description": "Asset returned successfully via stream"},
    **{k: v for k, v in error_responses.items() if k in [400, 404]}
}
         )
def get_assets(file_name: str, content_type: Optional[str] = None,
               request: Optional[Any] = None) -> Union[ResponseModel, FileResponse, StreamingResponse]:
    """Endpoint to get video asset by file name."""
    if not file_name:
        raise HTTPException(status_code=400, detail="A File Name is required")

    # Check to see if file exists in the assets directory
    file_path = os.path.join(assets_dir, file_name)

    print(f"File Path: {file_path}")

    print(f"Content Type: {content_type}")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Get the file extension form the file_path
    file_extension = get_file_extension_from_filepath(file_path)

    # Get the mime type for the file
    mim_type = get_file_mime_type(file_extension)

    if request:
        return range_requests_response(
            request, file_path=file_path, content_type=mim_type
        )
    else:
        return FileResponse(status_code=200, path=file_path, media_type=mim_type, content_disposition_type=content_type)


def send_bytes_range_requests(
        file_obj: BinaryIO, start: int, end: int, chunk_size: int = 10_000
):
    """Send a file in chunks using Range Requests specification RFC7233

    `start` and `end` parameters are inclusive due to specification
    """
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
)->StreamingResponse:
    """Returns StreamingResponse using Range Requests of a given file"""

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
