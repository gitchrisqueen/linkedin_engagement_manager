import os
import shutil
from datetime import timedelta, datetime

from cqc_lem import assets_dir
from cqc_lem.my_celery import app as shared_task
# from celery import shared_task
from cqc_lem.run_automation import automate_commenting, automate_profile_viewer_engagement, \
    send_appreciation_dms_for_user, clean_stale_invites, update_stale_profile, post_to_linkedin
from cqc_lem.utilities.date import add_local_tz_to_datetime
from cqc_lem.utilities.db import get_ready_to_post_posts, update_db_post_status, get_active_user_ids, PostStatus
from cqc_lem.utilities.env_constants import SELENIUM_KEEP_VIDEOS_X_DAYS
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

        # Update the DB with post status = scheduled so it won't get processed again
        update_db_post_status(post_id, PostStatus.SCHEDULED)
        myprint(f"Post ID: {post_id} Scheduled for: {scheduled_time}")

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

        base_kwargs = {'user_id': user_id}

        # Start the pre-post commenting task 15 minutes before scheduled post (loop for 15 minutes)
        base_kwargs['loop_for_duration'] = 60 * 15
        automate_commenting.apply_async(kwargs=base_kwargs, eta=scheduled_time - timedelta(minutes=15))

        # Schedule the pre-post profile viewer dm task 10 minutes before scheduled post (loop for 10 minutes)
        base_kwargs['loop_for_duration'] = 60 * 10
        automate_profile_viewer_engagement.apply_async(kwargs=base_kwargs, eta=scheduled_time - timedelta(minutes=10))





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
        myprint(f"Cleaning Stale Profiles for user: {user_id}")

        # Clean up stale profiles for this user
        #update_stale_profile(user_id)
        update_stale_profile.apply_async(kwargs={'user_id': user_id},
                                        retry=True,
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
def auto_clean_old_videos():
    """Cleans up old videos in the selenium folder"""

    days_to_keep = SELENIUM_KEEP_VIDEOS_X_DAYS
    myprint(f"Cleaning old videos older than {days_to_keep} days")
    expiration_date = datetime.now() - timedelta(days=days_to_keep)
    selenium_folder = os.path.join(assets_dir, 'selenium')
    delete_count = 0
    # Get all the folders in the selenium folder
    for folder in os.listdir(selenium_folder):
        folder_path = os.path.join(selenium_folder, folder)
        if os.path.isdir(folder_path) and datetime.fromtimestamp(os.path.getmtime(folder_path)) < expiration_date:
            myprint(f"Deleting folder: {folder_path}")
            shutil.rmtree(folder_path)
            delete_count += 1
    return f"Deleted {delete_count} folders"



if __name__ == "__main__":
    print("Process finished")
