import json
import os
import uuid
from typing import List, Optional, Annotated, Dict

import requests
from linkedin_api.clients.restli.client import RestliClient
from pydantic import BaseModel, Field
from pydantic.types import StringConstraints

from cqc_lem.utilities.db import get_user_linked_sub_id, get_user_access_token
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.mime_type_helper import get_file_mime_type
from cqc_lem.utilities.utils import get_file_extension_from_filepath

# Define annotations for constrained strings
ReadyStatus = Annotated[str, StringConstraints(pattern=r'^(READY)$')]
ShareMediaCategory = Annotated[str, StringConstraints(pattern=r'^(NONE|ARTICLE|IMAGE|VIDEO)$')]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class ShareMedia(BaseModel):
    status: ReadyStatus = "READY"
    description: Optional[Dict[str, str]] = Field(default_factory=lambda: {"text": ""})
    media: Optional[str] = None  # DigitalMediaAsset URN
    originalUrl: Optional[str] = Field(default_factory=lambda: "")
    title: Optional[Dict[str, str]] = Field(default_factory=lambda: {"text": ""})


class ShareContent(BaseModel):
    shareCommentary: Dict[str, NonEmptyString]
    shareMediaCategory: ShareMediaCategory
    media: Optional[List[ShareMedia]] = None


def download_media(media_path: str) -> str:
    response = requests.get(media_path, timeout=30)
    response.raise_for_status()
    content = response.content
    extension = get_file_extension_from_filepath(media_path)
    tmp_path = f"/tmp/{uuid.uuid4()}{extension}"
    with open(tmp_path, "wb") as f:
        f.write(content)
    myprint(f"Downloaded media to: {tmp_path}")
    return tmp_path


def upload_media(access_token, owner_sub_id: str, media_path, media_type: str = "image"):
    API_URL = 'https://api.linkedin.com/v2'

    is_tmp_path = False

    # If media_path is a URL, download the content
    if media_path.startswith('http'):
        media_path = download_media(media_path)
        is_tmp_path = True

    with open(media_path, 'rb') as media_file:
        media_content = media_file.read()

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/octet-stream'
    }
    upload_response = requests.post(
        f'{API_URL}/assets?action=registerUpload',
        headers=headers,
        data=json.dumps({
            "registerUploadRequest": {
                "recipes": [f"urn:li:digitalmediaRecipe:feedshare-{str(media_type).lower()}"],
                "owner": f"urn:li:person:{owner_sub_id}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        })
    )

    #print(f"Upload Response: {upload_response.json()}")

    upload_url = upload_response.json()['value']['uploadMechanism'][
        'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
    returned_headers = upload_response.json()['value']['uploadMechanism'][
        'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['headers']
    asset = upload_response.json()['value']['asset']
    mediaArtifact = upload_response.json()['value']['mediaArtifact']
    myprint(f"Asset: {asset} | Upload URL: {upload_url} | Headers: {returned_headers} | Media Artifact: {mediaArtifact}")

    # Upload the media file
    upload_response = requests.put(upload_url, headers=headers, data=media_content)

    # Delete the temp file
    if is_tmp_path:
        os.remove(media_path)

    if upload_response.status_code == 201:
        return asset
    else:
        raise Exception("Media upload failed")


def determine_media_type(media_path: str) -> str:
    _, ext = os.path.splitext(os.path.basename(media_path))
    mime = get_file_mime_type(ext)
    if "image" in mime:
        return "IMAGE"
    elif "video" in mime:
        return "VIDEO"
    else:
        raise ValueError(f"Unsupported media type for extension '{ext}': {mime}")


def share_on_linkedin(user_id: int, content: str,
                      media_path: Optional[str] = None,
                      article_url: Optional[str] = None
                      ):
    restli_client = RestliClient()
    restli_client.session.hooks["response"].append(lambda r: r.raise_for_status())

    linked_sub_id = get_user_linked_sub_id(user_id)
    access_token = get_user_access_token(user_id)

    if not linked_sub_id or not access_token:
        myprint(f"No LinkedIn credentials found for user {user_id} — cannot post")
        return None

    media_objects = []
    share_media_category = "NONE"

    if media_path:
        media_type = determine_media_type(media_path)
        myprint(f"Detected Media Type: {media_type}")
        media_urn = upload_media(access_token,
                                 linked_sub_id,
                                 media_path,
                                 media_type)  # Assuming upload_media returns the URN of the uploaded media
        myprint(f"Media Uploaded to LinkedIn: {media_urn}")
        if media_type.lower() in ['image' ]:
            share_media_category = 'IMAGE'
        elif media_type.lower() in ['video' ]:
            share_media_category = 'VIDEO'
        elif media_type.lower() == 'article':
            share_media_category = 'ARTICLE'
        else:
            share_media_category = 'NONE'
        myprint(f"Set share_media_category: {share_media_category}")

        media_objects = [
            ShareMedia(
                status="READY",
                media=media_urn
            ).model_dump()
        ]
    if article_url:
        share_media_category = 'ARTICLE'
        media_objects = [
            ShareMedia(
                status="READY",
                originalUrl=article_url,
            ).model_dump()
        ]

    share_content = ShareContent(
        shareCommentary={"text": content},
        shareMediaCategory=share_media_category,
        media=media_objects
    ).model_dump()

    posts_create_response = restli_client.create(
        # resource_path="/posts",
        resource_path="/ugcPosts",
        entity={
            "author": f"urn:li:person:{linked_sub_id}",
            "lifecycleState": "PUBLISHED",
            # "visibility": "PUBLIC",
            # "distribution": {
            #    "feedDistribution": "MAIN_FEED",
            #    "targetEntities": [],
            #    "thirdPartyDistributionChannels": [],
            # },
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    **share_content
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }

        },
        # version_string=os.getenv("LI_API_VERSION"),
        access_token=access_token,
    )

    # For each key in posts_create_response print it out
    #myprint(f"Post Create Response:")
    #for key, value in posts_create_response.entity.items():
    #    myprint(f"{key}: {value}")

    urn = posts_create_response.entity_id
    myprint(f"Shared on LinkedIn via API call: https://www.linkedin.com/feed/update/{urn}")

    return urn


def _is_local_image_path(value: str) -> bool:
    """Return True if value looks like a local file path rather than a Pexels search query."""
    return bool(value) and (value.startswith("/") or os.path.isfile(value))


def _is_image_url(value: str) -> bool:
    """Return True if value is an HTTP/HTTPS URL (download handled by upload_media)."""
    return bool(value) and value.startswith("http")


def share_carousel_on_linkedin(user_id: int, content: str, slide_texts: list[str]) -> Optional[str]:
    """Post a multi-image carousel to LinkedIn.

    slide_texts entries can be:
    - An absolute file path to a pre-generated PNG slide image (created by create_carousel_slide_images)
    - A plain text search query (legacy) — a Pexels image is fetched for it

    All images are uploaded individually and included as a multi-image ugcPost.
    """
    import os
    from cqc_lem.utilities.carousel_creator import get_pexels_image_path

    restli_client = RestliClient()
    restli_client.session.hooks["response"].append(lambda r: r.raise_for_status())

    linked_sub_id = get_user_linked_sub_id(user_id)
    access_token = get_user_access_token(user_id)

    if not linked_sub_id or not access_token:
        myprint(f"No LinkedIn credentials found for user {user_id} — cannot post carousel")
        return None

    file_dir = os.path.dirname(os.path.abspath(__file__))
    default_image_path = os.path.join(file_dir, "..", "carousel_creator", "images", "image.png")

    media_urns = []
    for slide in slide_texts:
        if _is_local_image_path(slide) or _is_image_url(slide):
            # Local file path or URL — upload_media handles both (URLs are downloaded first)
            image_path = slide
        else:
            image_path = get_pexels_image_path(slide, default_image_path)
        myprint(f"Carousel slide image: {image_path}")
        urn = upload_media(access_token, linked_sub_id, image_path, "IMAGE")
        if urn:
            media_urns.append(urn)

    if not media_urns:
        myprint("No images uploaded for carousel — falling back to text-only post")
        return share_on_linkedin(user_id, content)

    media_objects = [ShareMedia(status="READY", media=urn).model_dump() for urn in media_urns]

    share_content = ShareContent(
        shareCommentary={"text": content},
        shareMediaCategory="IMAGE",
        media=media_objects,
    ).model_dump()

    posts_create_response = restli_client.create(
        resource_path="/ugcPosts",
        entity={
            "author": f"urn:li:person:{linked_sub_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    **share_content
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        },
        access_token=access_token,
    )

    urn = posts_create_response.entity_id
    myprint(f"Carousel shared on LinkedIn: https://www.linkedin.com/feed/update/{urn}")
    return urn

