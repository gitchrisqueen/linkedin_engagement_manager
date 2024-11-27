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
ShareMediaCategory = Annotated[str, StringConstraints(pattern=r'^(NONE|ARTICLE|IMAGE)$')]
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


def download_media(media_path):
    response = requests.get(media_path)
    content = response.content
    # Get the file exntension from the media path
    extension = get_file_extension_from_filepath(media_path)
    # Store to local tmp path with uuid name
    tmp_path = f"/tmp/{uuid.uuid4()}{extension}"
    with open(tmp_path, "wb") as f:
        f.write(content)

    print(f"Downloaded media to: {tmp_path}")

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
    asset = upload_response.json()['value']['asset']

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
    """Stub function to determine the type of media (image or video)."""

    # Get the file extension and determine the media type
    basename = os.path.basename(media_path)
    file_name, file_extension = os.path.splitext(basename)

    mime_type = get_file_mime_type(file_extension)

    # Simple logic based on file extension, could be replaced with actual media inspection logic
    if 'image' in media_path:
        return 'IMAGE'
    elif 'video' in media_path:
        return 'VIDEO'
    else:
        raise ValueError("Unsupported media type")


def share_on_linkedin(user_id: int, content: str,
                      media_path: Optional[str] = None,
                      article_url: Optional[str] = None
                      ):
    restli_client = RestliClient()
    restli_client.session.hooks["response"].append(lambda r: r.raise_for_status())

    linked_sub_id = get_user_linked_sub_id(user_id)
    access_token = get_user_access_token(user_id)

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
        if media_type.lower() in ['video','image' ]:
            share_media_category = 'IMAGE'
        elif media_type.lower() == 'article':
            share_media_category = 'ARTICLE'
        else:
            share_media_category = 'NONE'
        media_objects = [
            ShareMedia(
                status="READY",
                media=media_urn
            ).model_dump()
        ]
    if article_url:
        # TODO: Implement and test this
        share_media_category = 'ARTICLE'
        pass

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
    myprint(f"Post Create Response:")
    for key, value in posts_create_response.entity.items():
        myprint(f"{key}: {value}")

    urn = posts_create_response.entity_id
    myprint(f"Shared on LinkedIn via API call: https://www.linkedin.com/feed/update/{urn}")

    return urn


if __name__ == '__main__':
    # Example usage
    media_path = '/app/src/cqc_lem/assets/videos/runwayml/0bcc2063-aa61-4ee5-b672-49f2d4614373.mp4'
    #media_path = 'https://cqc-lem-api.ngrok-free.dev/assets?file_name=videos/runwayml/71b68785-2b7e-48c6-aadd-822014a18b1d.mp4'
    user_id = 60
    content = "Video Post"
    share_result = share_on_linkedin(user_id, content, media_path)
    #content = "Regular Post"
    # share_result = share_on_linkedin(user_id, content)
    #content = "Image Post"
    #media_path = '/app/src/cqc_lem/assets/images/replicate/8JAFZaCQtV4VJFhuX1qNOJd1kwFre7gjfuzGdj7UreQ72mpnA/out-0.webp'
    #share_result = share_on_linkedin(user_id, content, media_path)
