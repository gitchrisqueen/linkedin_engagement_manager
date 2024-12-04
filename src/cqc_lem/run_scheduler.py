from datetime import timedelta

from cqc_lem.my_celery import app as shared_task
# from celery import shared_task
from cqc_lem.run_automation import automate_commenting, automate_profile_viewer_engagement, \
    send_appreciation_dms_for_user, automate_reply_commenting, clean_stale_invites, get_current_profile
from cqc_lem.utilities.date import add_local_tz_to_datetime
from cqc_lem.utilities.db import get_ready_to_post_posts, get_post_content, \
    update_db_post_status, get_user_password_pair_by_id, get_active_user_ids, insert_new_log, LogActionType, \
    LogResultType, get_post_video_url, PostStatus
from cqc_lem.utilities.linkedin.poster import share_on_linkedin
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
        update_db_post_status(post_id, PostStatus.SCHEDULED)

    if len(posts) == 0:
        return f"No Post to Schedule"
    else:
        return f"Started Process for {len(posts)} post(s)"


@shared_task.task
def auto_appreciate_dms():
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
        return f"Started Appreciate DM Process for {len(users)} user(s)"


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

    # Add the query param content_type to the url
    if video_url:
        myprint(f"Adding to Post | Video URL: {video_url}")

    urn = share_on_linkedin(user_id, content, video_url)

    if urn:
        post_url = f"https://www.linkedin.com/feed/update/{urn}/"
        myprint(f"Successfully created post using /posts API endpoint: {post_url}")

        # Update DB with status=posted
        update_db_post_status(post_id, PostStatus.POSTED)

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
                       message=f"Successfully created post using /posts API endpoint.")

        return f"Post successfully created"

    else:
        myprint(f"Failed to create post using /posts API endpoint")
        # Update DB with status=failed in the logs table
        insert_new_log(user_id=user_id, action_type=LogActionType.POST, result=LogResultType.FAILURE, post_id=post_id,
                       message="Failed to create post using /posts API endpoint.")

        return f"Failed to create post using /posts API endpoint"


@shared_task.task
def auto_clean_stale_invites():
    """Cleans up stale invites for each active user"""

    # Get all active users and loop through them
    users = get_active_user_ids()

    for user_id in users:
        # Clean up stale invites for this user
        kwargs = {'user_id': user_id}
        clean_stale_invites.apply_async(kwargs=kwargs, retry=True,
                                        retry_policy={
                                            'max_retries': 3,
                                            'interval_start': 60,
                                            'interval_step': 30
                                        })
    if len(users) == 0:
        return f"No Active Users"
    else:
        return f"Started Process for {len(users)} user(s)"


@shared_task.task
def auto_clean_stale_profiles():
    """Cleans up stale profiles for each active user"""

    # Get all active users and loop through them
    users = get_active_user_ids()

    for user_id in users:
        # Clean up stale profiles for this user
        get_current_profile.apply_async(kwargs={'user_id': user_id}, retry=True,
                                        retry_policy={
                                            'max_retries': 3,
                                            'interval_start': 60,
                                            'interval_step': 30
                                        })

    if len(users) == 0:
        return f"No Active Users"
    else:
        return f"Started Process for {len(users)} user(s)"


if __name__ == "__main__":
    print("Process finished")
