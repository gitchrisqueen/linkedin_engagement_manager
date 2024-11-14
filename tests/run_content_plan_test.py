from cqc_lem.run_content_plan import create_content, generate_content, create_weekly_content
from cqc_lem.run_scheduler import post_to_linkedin
from cqc_lem.utilities.db import get_user_password_pair_by_id
from cqc_lem.utilities.linked_in_helper import get_my_profile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import clear_sessions, get_driver_wait_pair


def test_create_content():
    buyers_stages = [
        'awareness',
        #'consideration',
        #'decision'
    ]

    post_types = [
        'text',
        #'video',
        #'carousel'
    ]

    for stage in buyers_stages:
        for post_type in post_types:
            myprint(f"""Creating Content for {post_type} post in {stage} stage.""")
            content = create_content(1, post_type, stage)
            myprint(f"""Content for {post_type} post in {stage} stage:\n\n{content}""")

def test_user_profile_load_from_db():
    user_email, user_password = get_user_password_pair_by_id(1)
    driver, wait = get_driver_wait_pair(session_name='Testing Linked User Profile Load to From DB')
    myprint(f"User Email: {user_email} | Loading Profile 1st Time")
    get_my_profile(driver, wait, user_email, user_password)
    myprint(f"User Email: {user_email} | Loading Profile 2nd Time | Should definitely be faster coming from DB")
    get_my_profile(driver, wait, user_email, user_password)
    driver.quit()


def test_content_plan_and_create():
    generate_content()
    create_weekly_content()

def test_post_to_linkedin():
    post_to_linkedin(60,1)


if __name__ == "__main__":
    # Clear selenium sessions
    #clear_sessions()

    #test_user_profile_load_from_db()
    #test_create_content()
    #test_content_plan_and_create()

    test_post_to_linkedin()