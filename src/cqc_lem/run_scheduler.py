import os
from datetime import timedelta

from linkedin_api.clients.restli.client import RestliClient

from cqc_lem.my_celery import app as shared_task
# from celery import shared_task
from cqc_lem.run_automation import automate_commenting, automate_profile_viewer_dms, \
    automate_appreciation_dms, automate_reply_commenting
from cqc_lem.utilities.db import get_ready_to_post_posts, get_user_password_pairs, get_post_content, \
    update_db_post_status, get_user_password_pair_by_id, get_user_linked_sub_id, get_user_access_token, \
    get_active_user_ids
from cqc_lem.utilities.logger import myprint


@shared_task.task
def check_scheduled_posts():
    """Checks if there are any posts to publish."""

    posts = get_ready_to_post_posts()

    for post in posts:
        post_id, scheduled_time, user_id = post

        myprint(f"Ready to Post ID: {post_id}")

        base_kwargs = {'user_id': user_id}


        # Schedule the pre-post profile viewer dm task 10 minutes before scheduled post (loop for 10 minutes)
        base_kwargs['loop_for_duration'] = 60 * 10
        automate_profile_viewer_dms.apply_async(kwargs=base_kwargs, eta=scheduled_time - timedelta(minutes=10))

        # Schedule the post to be posted
        post_kwargs = {'user_id': user_id, 'post_id': post_id}
        post_to_linkedin.apply_async(kwargs=post_kwargs, eta=scheduled_time)

        # Schedule Answer comments for 30 minutes (5 minutes after scheduled post time)
        base_kwargs['loop_for_duration'] = 60 * 30
        automate_reply_commenting.apply_async(kwargs=base_kwargs, eta=scheduled_time + timedelta(minutes=5))

        # Start the pre-post commenting task now (loop for 15 minutes)
        base_kwargs['loop_for_duration'] = 60 * 15
        automate_commenting.apply_async(kwargs=base_kwargs)


@shared_task.task
def start_appreciate_dms():
    # For each user schedule appreciate DMS
    users = get_active_user_ids()

    for user_id in users:

        # Send appreciation DM for 5 minutes
        kwargs = {
            'user_id': user_id,
            'loop_for_duration': 60 * 5
        }

        # TODO: Should this be spaced out over some interval if user numbers grow
        # time.sleep()

        automate_appreciation_dms.apply_async(kwargs=kwargs)


@shared_task.task
def post_to_linkedin(user_id: int, post_id, **kwargs):
    # TODO: Write code to login an publish post to linkedin
    user_email, user_password = get_user_password_pair_by_id(user_id)
    myprint(f"Posting to LinkedIn as user: {user_email}")

    # Get the post content
    content = get_post_content(post_id)
    myprint(f"Posting to LinkedIn: {content}")

    restli_client = RestliClient()
    restli_client.session.hooks["response"].append(lambda r: r.raise_for_status())

    linked_sub_id = get_user_linked_sub_id(user_id)

    access_token = get_user_access_token(user_id)

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
        myprint(f"Successfully created post using /posts: {posts_create_response.entity_id}")

        # Update DB with status=posted
        update_db_post_status(post_id, 'posted')
    else:
        myprint(f"Failed to create post using /posts")




if __name__ == "__main__":
    print("Process finished")
