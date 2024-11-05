from datetime import timedelta

from cqc_lem.my_celery import app as shared_task
# from celery import shared_task
from cqc_lem.run_automation import automate_commenting, automate_profile_viewer_dms, \
    automate_appreciation_dms, automate_reply_commenting
from cqc_lem.utilities.db import get_ready_to_post_posts, get_user_password_pairs, get_post_content, \
    update_db_post_status, get_user_password_pair_by_id
from cqc_lem.utilities.logger import myprint


@shared_task.task
def check_scheduled_posts():
    """Checks if there are any posts to publish."""

    posts = get_ready_to_post_posts()

    for post in posts:
        post_id, scheduled_time, user_id= post

        myprint(f"Ready to Post ID: {post_id}")

        base_kwargs = {'user_id': user_id, 'loop_for_duration': 60 * 15}

        # Start the pre-post commenting task (loop for 15 minutes
        automate_commenting.delay(
            kwargs=base_kwargs)

        # 10 minutes before the scheduled_time
        pre_post_dm_time = scheduled_time - timedelta(minutes=10)

        # Schedule the pre-post profile viewer dm task (loop for 10 minutes)
        base_kwargs['loop_for_duration'] = 60 * 10
        automate_profile_viewer_dms.apply_async(kwargs=base_kwargs, eta=pre_post_dm_time)

        # Schedule the post to be posted
        base_kwargs['post_id'] = post_id
        post_to_linkedin.apply_async(kwargs=base_kwargs, eta=scheduled_time)

        # Answer comments for 30 minutes
        base_kwargs['loop_for_duration'] = 60 * 30
        automate_reply_commenting.apply_async(kwargs=base_kwargs, eta=scheduled_time)


@shared_task.task
def start_appreciate_dms():
    # For each user schedule appreciate DMS
    users = get_user_password_pairs()

    for user in users:
        user_email, user_password = user

        # Send appreciation DM for 5 minutes
        automate_appreciation_dms.delay(  # TODO: Should this be spaced out over some interval if user amounts grow
            kwargs={
                'user_email': user_email,
                'user_password': user_password,
                'loop_for_duration': 60 * 5
            }
        )


@shared_task.task
def post_to_linkedin(user_id: int, post_id, **kwargs):
    # Get the post content
    content = get_post_content(post_id)
    myprint(f"Posting to LinkedIn: {content}")

    # TODO: Write code to login an publish post to linkedin
    user_email, user_password = get_user_password_pair_by_id(user_id)
    myprint(f"Posting to as user: {user_email}")


    # Update DB with status=posted
    update_db_post_status(post_id, 'posted')


if __name__ == "__main__":
    print("Process finished")
