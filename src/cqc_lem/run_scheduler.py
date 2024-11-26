import os
from datetime import timedelta

from linkedin_api.clients.restli.client import RestliClient

from cqc_lem.my_celery import app as shared_task
# from celery import shared_task
from cqc_lem.run_automation import automate_commenting, automate_profile_viewer_engagement, \
    send_appreciation_dms_for_user, automate_reply_commenting
from cqc_lem.utilities.date import add_local_tz_to_datetime
from cqc_lem.utilities.db import get_ready_to_post_posts, get_post_content, \
    update_db_post_status, get_user_password_pair_by_id, get_user_linked_sub_id, get_user_access_token, \
    get_active_user_ids, insert_new_log, LogActionType, LogResultType, get_post_video_url
from cqc_lem.utilities.logger import myprint


@shared_task.task
def test_error_tracing():
    """Generates a traceable error to test the jaeger tracing configs"""
    myprint("Starting test_error_tracing")
    raise ValueError("This is a test error")


@shared_task.task
def auto_check_scheduled_posts():
    """Checks if there are any posts to publish."""

    # Get post that should have run between yesterday and in the next 20 minutes
    posts = get_ready_to_post_posts()

    for post in posts:
        post_id, scheduled_time, user_id = post

        scheduled_time = add_local_tz_to_datetime(scheduled_time)  # Must add timezone info to this

        myprint(f"Ready to Post ID: {post_id}")

        base_kwargs = {'user_id': user_id}

        # Start the pre-post commenting task now (loop for 15 minutes)
        base_kwargs['loop_for_duration'] = 60 * 15
        automate_commenting.apply_async(kwargs=base_kwargs, eta=scheduled_time - timedelta(minutes=15))

        # Schedule the pre-post profile viewer dm task 10 minutes before scheduled post (loop for 10 minutes)
        base_kwargs['loop_for_duration'] = 60 * 10
        automate_profile_viewer_engagement.apply_async(kwargs=base_kwargs, eta=scheduled_time - timedelta(minutes=10))

        # Schedule the post to be posted
        post_kwargs = {'user_id': user_id, 'post_id': post_id}
        post_to_linkedin.apply_async(kwargs=post_kwargs,
                                     eta=scheduled_time,
                                     retry=True,
                                     retry_policy={
                                         'max_retries': 3,
                                         'interval_start': 60,
                                         'interval_step': 30

                                     }
                                     )

        # Update the DB with post status = scheduled so it won't get processed again
        update_db_post_status(post_id, 'scheduled')

    if len(posts) == 0:
        return f"No Post to Schedule"
    else:
        return f"Started Process for {len(posts)} post(s)"


@shared_task.task
def automate_appreciate_dms():
    # For each user schedule appreciate DMS
    users = get_active_user_ids()

    for user_id in users:
        # Send appreciation DM for 5 minutes
        kwargs = {
            'user_id': user_id,
            'loop_for_duration': 60 * 5
        }

        # No need to worry as this task is rate limited to 2 per minute
        send_appreciation_dms_for_user.apply_async(kwargs=kwargs, retry=True,
                                                   retry_policy={
                                                       'max_retries': 3,
                                                       'interval_start': 60,
                                                       'interval_step': 30
                                                   })
    if len(users) == 0:
        return f"No Active Users"
    else:
        return f"Started Process for {len(users)} user(s)"


@shared_task.task(rate_limit='2/m')
def post_to_linkedin(user_id: int, post_id: int, **kwargs):
    """Posts to LinkedIn using the LinkedIn API - https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin#creating-a-share-on-linkedin"""

    # Login and publish post to LinkedIn
    user_email, user_password = get_user_password_pair_by_id(user_id)
    myprint(f"Posting to LinkedIn as user: {user_email}")

    # Get the post content
    content = get_post_content(post_id)
    myprint(f"Posting to LinkedIn: {content}")

    # Get the post video url
    video_url = get_post_video_url(post_id)



    restli_client = RestliClient()
    restli_client.session.hooks["response"].append(lambda r: r.raise_for_status())

    linked_sub_id = get_user_linked_sub_id(user_id)

    access_token = get_user_access_token(user_id)

    if video_url:
        myprint(f"Video URL: {video_url}")
        # Send a POST request to the assets API, with the action query parameter to registerUpload.
        restli_client.p

        # A successful response will contain an uploadUrl and asset that you will need to save for the next steps.

        # Using the uploadUrl returned from Step 1, upload your image or video to LinkedIn. To upload your image or video, send a POST request to the uploadUrl with your image or video included as a binary file. The example below uses cURL to upload an image file.

    posts_create_response = restli_client.create(
        resource_path="/posts",
        entity={
            "author": f"urn:li:person:{linked_sub_id}",
            "lifecycleState": "PUBLISHED",
            "visibility": "PUBLIC",
            "commentary": content,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
        },
        version_string=os.getenv("LI_API_VERSION"),
        access_token=access_token,
    )

    myprint("Post Create Response from api call")
    for key, value in posts_create_response.__dict__.items():
        myprint(f"{key}: {value}")

    if posts_create_response.entity_id:
        post_url = f"https://www.linkedin.com/feed/update/{posts_create_response.entity_id}/"
        myprint(f"Successfully created post using /posts API endpoint: {post_url}")

        # Update DB with status=posted
        update_db_post_status(post_id, 'posted')

        # Schedule Answer comments for 30 minutes now that this has been posted
        base_kwargs = {
            'user_id': user_id,
            'post_id': post_id,
            'loop_for_duration': 60 * 30
        }
        automate_reply_commenting.apply_async(kwargs=base_kwargs)


        # Update DB with status=success in the logs table and the post url
        insert_new_log(user_id=user_id, action_type=LogActionType.POST, result=LogResultType.SUCCESS, post_id=post_id,
                       post_url=post_url,
                       message="Successfully created post using /posts API endpoint. Results: " + str(
                           posts_create_response))

        return f"Post successfully created"

    else:
        myprint(f"Failed to create post using /posts API endpoint")
        # Update DB with status=failed in the logs table
        insert_new_log(user_id=user_id, action_type=LogActionType.POST, result=LogResultType.FAILURE, post_id=post_id,
                       message="Failed to create post using /posts API endpoint. Result: " + str(posts_create_response))

        return f"Failed to create post using /posts API endpoint"


if __name__ == "__main__":
    print("Process finished")
