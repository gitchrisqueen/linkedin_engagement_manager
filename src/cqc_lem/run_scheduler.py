import os
import shutil
from datetime import timedelta, datetime

from celery_once import QueueOnce

from cqc_lem import assets_dir
from cqc_lem.my_celery import app as shared_task
# from celery import shared_task
from cqc_lem.run_automation import automate_commenting, automate_profile_viewer_engagement, \
    automate_appreciation_dms_for_user, clean_stale_invites, update_stale_profile, post_to_linkedin, \
    automate_invites_to_company_page_for_user
from cqc_lem.utilities.date import add_local_tz_to_datetime
from cqc_lem.utilities.db import get_ready_to_post_posts, update_db_post_status, get_active_user_ids, PostStatus
from cqc_lem.utilities.env_constants import SELENIUM_KEEP_VIDEOS_X_DAYS
from cqc_lem.utilities.logger import myprint


@shared_task.task
def test_error_tracing():
    """Generates a traceable error to test the jaeger tracing configs"""
    myprint("Starting test_error_tracing")
    raise ValueError("This is a test error")


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, }, reject_on_worker_lost=True)
def auto_check_scheduled_posts(self):
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
                                     )

        base_kwargs = {'user_id': user_id, 'loop_for_duration': 60 * 15}

        # Start the pre-post commenting task 15 minutes before scheduled post (loop for 15 minutes)
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
        automate_appreciation_dms_for_user.apply_async(kwargs=kwargs, retry=True,
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
        # update_stale_profile(user_id)
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
def auto_invite_to_company_pages():
    """Start invite process for each active user who has a linked in company page"""

    # Get all active users and loop through them
    users = get_active_user_ids()

    for user_id in users:
        myprint(f"Starting Company Page Invites for user: {user_id}")


        automate_invites_to_company_page_for_user.apply_async(kwargs={'user_id': user_id},
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

    # Organize the videos by name and timestamp
    moved_videos = organize_videos_by_name_and_timestamp()

    return f"Deleted {delete_count} folders | Moved {moved_videos} videos"


def organize_videos_by_name_and_timestamp():
    selenium_folder = os.path.join(assets_dir, 'selenium')

    # Keep track of videos moved
    moved_videos = 0

    # Create a map to store unique names
    unique_name_map = {}

    # Iterate through each folder in the selenium folder
    for folder in os.listdir(selenium_folder):
        # Skip Folders that start with "CQC_LEM"
        if folder.startswith("CQC_LEM"):
            continue

        folder_path = os.path.join(selenium_folder, folder)
        if os.path.isdir(folder_path):
            # Iterate through each file in the folder
            for file in os.listdir(folder_path):
                if file.endswith('.mp4'):
                    file_path = os.path.join(folder_path, file)
                    file_name = os.path.splitext(file)[0]
                    file_timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y_%m_%d_%H_%M_%S')

                    # Create a unique name map entry if it doesn't exist
                    if file_name not in unique_name_map:
                        unique_name_map[file_name] = []

                    # Add the file path and timestamp to the unique name map
                    unique_name_map[file_name].append((file_path, file_timestamp))

    # Create folders for each unique name and move the files
    for name, files in unique_name_map.items():
        name_folder = os.path.join(selenium_folder, name)
        os.makedirs(name_folder, exist_ok=True)

        for file_path, file_timestamp in files:
            new_file_name = f"{file_timestamp}.mp4"
            new_file_path = os.path.join(name_folder, new_file_name)
            shutil.move(file_path, new_file_path)
            print(f"Moved {file_path} to {new_file_path}")
            # Delete the folder belonging to the file_path
            parent_folder = os.path.dirname(file_path)
            shutil.rmtree(parent_folder)
            print(f"Deleted {parent_folder}")
            moved_videos += 1

    return moved_videos


if __name__ == "__main__":
    print("Process finished")
