import os
import random
import shutil

from cqc_lem import assets_dir
from cqc_lem.run_content_plan import create_content, auto_generate_content, auto_create_weekly_content
from cqc_lem.run_automation import post_to_linkedin
from cqc_lem.utilities.ai.ai_helper import get_industry_trend_analysis_based_on_user_profile, get_thought_leadership_post_from_ai
from cqc_lem.utilities.db import get_user_password_pair_by_id
from cqc_lem.utilities.env_constants import API_BASE_URL
from cqc_lem.utilities.linkedin.helper import get_my_profile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import clear_sessions, get_driver_wait_pair
from cqc_lem.utilities.utils import create_folder_if_not_exists, save_video_url_to_dir


def test_create_content():
    clear_sessions()

    buyers_stages = [
        'awareness',
        #'consideration',
        #'decision'
    ]

    post_types = [
        #'text',
        'video',
        #'carousel'
    ]

    for stage in buyers_stages:
        for post_type in post_types:
            myprint(f"""Creating Content for {post_type} post in {stage} stage.""")
            content, video_url = create_content(60, post_type, stage)
            myprint(f"""Content for {post_type} post in {stage} stage:\n\n{content}""")

            # Copy the video from url to our assets/video folder and store it to the database for later retrieval via api call
            if video_url:
                # Define and create assets_dir / videos
                videos_dir = os.path.join(assets_dir, 'videos','runwayml')
                create_folder_if_not_exists(videos_dir)
                video_file_path = save_video_url_to_dir(video_url, videos_dir)
                myprint(f"Video from url: {video_url} | Saved to: {video_file_path}")
                # Get the file name from the video file path
                video_file_name = os.path.basename(video_file_path)

                # The video url is our api prefix + 'assets/videos' +  video_file_name
                api_video_url = f"{API_BASE_URL}/assets?file_name=videos/runwayml/{video_file_name}"
                myprint(f"Video URL: {api_video_url}")

def test_user_profile_load_from_db():
    user_email, user_password = get_user_password_pair_by_id(1)
    driver, wait = get_driver_wait_pair(session_name='Testing Linked User Profile Load to From DB')
    myprint(f"User Email: {user_email} | Loading Profile 1st Time")
    get_my_profile(driver, wait, user_email, user_password)
    myprint(f"User Email: {user_email} | Loading Profile 2nd Time | Should definitely be faster coming from DB")
    get_my_profile(driver, wait, user_email, user_password)
    driver.quit()


def test_content_plan_and_create():
    auto_generate_content()
    auto_create_weekly_content()

def test_post_to_linkedin():
    clear_sessions()
    post_to_linkedin(60,11)


def test_industry_of_user():
    clear_sessions()
    user_email, user_password = get_user_password_pair_by_id(60)
    driver, wait = get_driver_wait_pair(session_name='Testing Industry of User')
    my_profile = get_my_profile(driver, wait, user_email, user_password)
    trend_analysis = get_industry_trend_analysis_based_on_user_profile(my_profile)

    print(f"{trend_analysis}")


def test_thought_leadership_post_from_ai():
    buyers_stages = [
        'awareness',
        'consideration',
        'decision'
    ]

    clear_sessions()
    user_email, user_password = get_user_password_pair_by_id(60)
    driver, wait = get_driver_wait_pair(session_name='Testing Industry of User')
    my_profile = get_my_profile(driver, wait, user_email, user_password)

    # choose a random stage
    stage = random.choice(buyers_stages)
    post = get_thought_leadership_post_from_ai(my_profile,stage)
    print(f"Buyer Stage: {stage}\n\nPost: {post}")


def test_move_files():
    video_file_path = "/app/src/cqc_lem/assets/result/test/testing.mp4"

    # Move the video file path to the assets/gradio dir
    gradio_dir = os.path.join(assets_dir, "gradio")
    print(f"Gradio Dir: {gradio_dir}")
    create_folder_if_not_exists(gradio_dir)
    video_file_name = os.path.basename(video_file_path)
    # Get the parent folder name of the video file
    video_parent_dir = os.path.basename(os.path.dirname(video_file_path))
    print(f"Video Parent Folder: {video_parent_dir}")
    # Create dest folder
    file_dest_folder = os.path.join(gradio_dir, video_parent_dir)
    create_folder_if_not_exists(file_dest_folder)
    # Create final file destination
    video_file_dest = os.path.join(file_dest_folder, video_file_name)
    print(f"Video File Dest: {video_file_dest}")

    # Move the video file to the gradio dir
    shutil.move(video_file_path, video_file_dest)



if __name__ == "__main__":
    # Clear selenium sessions
    #clear_sessions()
    #test_user_profile_load_from_db()

    #test_move_files()

    #test_create_content()

    #test_content_plan_and_create()
    test_post_to_linkedin()

    #test_industry_of_user()

    #test_thought_leadership_post_from_ai()
