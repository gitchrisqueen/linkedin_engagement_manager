import random
from datetime import datetime, timedelta

from cqc_lem.my_celery import app as shared_task
from cqc_lem.utilities.ai.ai_helper import get_video_content_from_ai
from cqc_lem.utilities.db import get_post_type_counts, insert_planned_post, update_db_post_content, \
    get_planned_posts_for_current_week, get_last_planned_post_date_for_user, get_user_password_pair_by_id
from cqc_lem.utilities.linked_in_helper import get_my_profile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import get_driver_wait_pair
from cqc_lem.utilities.utils import get_best_posting_time


@shared_task.task
def generate_content(user_id: int):
    """
    Generate and plan content for the next 30 days based on current content representation in the database.
    Ensures a balanced distribution of post types (carousel, text, video) and buyer journey stages.
    """

    # 1. Review existing content in the database
    # Query the database to count the current representation of each post_type in the 'posts' table
    # Example: SELECT COUNT(*) FROM posts WHERE post_type = 'carousel'
    current_counts = get_post_type_counts(user_id)

    # Calculate the total posts and percentages of each type
    total_posts = sum(current_counts.values())
    percentages = {post_type: (count / total_posts) * 100 for post_type, count in current_counts.items()}

    # Log the current representation for debugging
    #myprint(f"Current Content Percentages: {percentages}")

    # 2. Determine the target distribution of post types for the next 30 days
    # Based on the percentages, calculate how many posts of each type are needed to balance the content

    # Determine how many days are in this month
    days_in_month = datetime.now().replace(day=1).replace(month=datetime.now().month+1, day=1) - datetime.now().replace(day=1)
    days_in_month = days_in_month.days

    #myprint(f"Days in Month: {days_in_month}")

    # Determine the start date as the day after the last scheduled post in planning status
    last_planned_date = get_last_planned_post_date_for_user(user_id)

    #myprint(f"Last Planned Date: {last_planned_date}")

    if last_planned_date:
        start_date = last_planned_date + timedelta(days=1) # Start with the next day
    else:
        start_date = datetime.now() + timedelta(days=1) # Start with the next day

    #myprint(f"Start Date: {start_date}")

    # Determine how many days are left in this month
    days_left_in_month = days_in_month - start_date.day

    #myprint(f"Days Left in Month after Start Date: {days_left_in_month}")

    # 4. Create content for each post type and buyer journey stage
    # Example logic: randomly select a post type and buyer journey stage for each post
    target_posts = days_left_in_month + 1   # Total posts till the end of the month

    #myprint(f"Target Posts: {target_posts}")

    needed_posts = {post_type: target_posts // 3 for post_type in ['carousel', 'text', 'video']}

    #myprint(f"Needed Posts: {needed_posts}")

    # Ensure all post types are present in current_counts and percentages
    for post_type in ['carousel', 'text', 'video']:
        if post_type not in percentages:
            percentages[post_type] = 0.0

    #myprint(f"Updated Content Percentages: {percentages}" )

    # Loop until the total needed posts equals the target posts
    while sum(needed_posts.values()) != target_posts:
        max_key = get_max_key(percentages)
        min_key = get_min_key(percentages)

        # Adjust the counts
        if sum(needed_posts.values()) < target_posts:
            needed_posts[min_key] += 1
        else:
            needed_posts[max_key] -= 1

        # Recalculate percentages
        total_posts = sum(needed_posts.values())
        for post_type in percentages:
            percentages[post_type] = (needed_posts[post_type] / total_posts) * 100

    # Output the final needed_posts and percentages
    #myprint(f"Final Needed Posts: {needed_posts}")
    #myprint(f"Final Percentages: {percentages}")

    # 3. Plan content across the buyer journey stages
    # Define buyer journey stages: Awareness, Consideration, Decision
    journey_stages = ["awareness", "consideration", "decision"]
    daily_plan = []

    # Shuffle the journey stages to ensure a random order
    random.shuffle(journey_stages)

    # Create a list of post types based on needed_posts
    post_types = []
    for post_type, count in needed_posts.items():
        post_types.extend([post_type] * count)

    # Shuffle the post types to ensure a random order
    random.shuffle(post_types)

    # Generate content evenly across buyer journey stages and post types
    for day in range(target_posts):  # Plan for end of this month
        # Choose a post type from the shuffled list
        post_type = post_types.pop()

        # Choose a buyer journey stage in a round-robin fashion
        stage = journey_stages[day % len(journey_stages)]

        # Call the helper function to create content for this post type and buyer journey stage
        create_content(post_type, stage)

        # Add this post to the daily plan
        post_date = start_date + timedelta(days=day)

        # Get the best time for the selected date
        post_time = get_best_posting_time(post_date.date())

        # Combine the selected date and time into a single datetime object
        scheduled_datetime = datetime.combine(post_date, post_time)

        daily_plan.append({
            "scheduled_datetime": scheduled_datetime,
            "post_type": post_type,
            "stage": stage
        })

        # Update the needed_posts count for the selected post type
        needed_posts[post_type] -= 1

    # Log the final content plan for the next 30 days
    #myprint(f"Generated content plan: {daily_plan}")
    myprint(f"Generated content plan")

    # 4. Save the daily plan to the database for tracking and scheduling
    save_content_plan(user_id, daily_plan)

# Function to find the key with the highest value in a dictionary
def get_max_key(d):
    return max(d, key=d.get)

# Function to find the key with the lowest value in a dictionary
def get_min_key(d):
    return min(d, key=d.get)

def create_content(user_id: int, post_type: str, stage: str):
    """Create content based on the specified post type and buyer journey stage."""

    user_email, user_password = get_user_password_pair_by_id(user_id)
    driver, wait = get_driver_wait_pair(session_name='Create Content')
    my_profile = get_my_profile(driver, wait, user_email, user_password)

    if post_type == "video":
        content = get_video_content_from_ai(my_profile, stage)
    elif post_type == "carousel":
        content = f"Content created for {post_type} in the {stage} stage. However, this is unfinished"
    else:
        content = f"Content created for {post_type} in the {stage} stage. However, this is unfinished"

    return content


def save_content_plan(user_id: int, daily_plan: list[dict]):
    """Save the planned content schedule to the database."""
    # Insert the 'daily_plan' into a database table for future reference and scheduling
    for plan in daily_plan:
        insert_planned_post(user_id, plan['scheduled_datetime'], plan['post_type'], plan['stage'])


@shared_task.task
def create_weekly_content():
    """Creates content for the week from the planed content in the database"""

    # Get the planned content for the current week
    planned_posts = get_planned_posts_for_current_week()

    for post in planned_posts:
        user_id = post['user_id']
        post_id = post['id']
        post_type = post['post_type']
        stage = post['buyer_stage']

        # For each content create it
        content = create_content(user_id, post_type, stage)

        # Update the database with the created content
        myprint(f"Updating post content for post_id: {post_id}")
        update_db_post_content(post_id, content)


if __name__ == '__main__':
    myprint("Generating content plan for 30 days")
    generate_content(1)
    myprint("Creating weekly content")
    create_weekly_content()
    myprint("Process finished")
