from datetime import datetime, timedelta

from cqc_lem.my_celery import app as shared_task
# from celery import shared_task
from cqc_lem.run_automation import get_driver_wait_pair, automate_commenting, automate_profile_viewer_dms, \
    automate_appreciation_dms, automate_reply_commenting
from cqc_lem.utilities.db import get_db_connection
from cqc_lem.utilities.utils import myprint


@shared_task.task
def check_scheduled_posts():
    """Checks if there are any posts to publish."""
    now = datetime.now()

    # Get time for 15 minutes prior to now
    pre_post_time = now - timedelta(minutes=15)

    # Query the database for any pending posts that are scheduled to post now or earlier
    conn = get_db_connection()
    cursor = conn.cursor()
    # TODO: Need to get posts that have scheduled time in the next 15 minutes
    cursor.execute(
        "SELECT scheduled_time, content FROM posts WHERE status = 'approved' AND scheduled_time <= %s ORDER BY scheduled_time asc limit 1",
        (pre_post_time,))  # Get the first post that is scheduled to post now or earlier
    posts = cursor.fetchall()

    driver, wait = get_driver_wait_pair()

    for post in posts:
        scheduled_time, content = post
        # Start the pre-post commenting task
        automate_commenting.delay(driver, wait, 60 * 15)

        # 10 minutes before the scheduled_time
        pre_post_dm_time = scheduled_time - timedelta(minutes=10)

        # Schedule the pre-post profile viewer dm task
        automate_profile_viewer_dms.apply_async((driver, wait, 60 * 10), eta=pre_post_dm_time)

        # Schedule the post to be posted
        post_to_linkedin.apply_async((content), eta=scheduled_time)

        # Answer comments for 30 minutes
        automate_reply_commenting.apply_async((driver, wait, 60 * 30), eta=scheduled_time)

    driver.quit()

    cursor.close()
    conn.close()


@shared_task.task
def start_appreciate_dms():
    driver, wait = get_driver_wait_pair()

    # Send appreciations DM for 5 minutes
    automate_appreciation_dms.delay((driver, wait, 60 * 5))

    driver.quit()


@shared_task.task
def post_to_linkedin(content: str):
    myprint(f"Posting to LinkedIn: {content}")


def start_scheduler():
    # Check DB for current Schedule

    # Find out if schedules exist for next 30 days

    # Plan post content
    # 1 - Txt
    # 2 - Carousel
    # 3 - Video

    # Use best times to post for time planning
    """Monday: 2:00 PM
    Tuesday: 9:00 AM and 11:00 AM
    Wednesday: 12:00 PM
    Thursday: 5:00 PM
    Friday: 11:00 PM
    Saturday: 7:00 AM and 8:00 AM
    Sunday: 9:00 AM"""

    # Add Pre/post posting tasks around scheduled posts times

    pass


if __name__ == "__main__":
    print("Process finished")
