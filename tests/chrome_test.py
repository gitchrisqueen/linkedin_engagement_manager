import time
from datetime import datetime, timedelta

from cqc_lem.utilities.db import add_user, get_user_password_pair_by_id, get_ready_to_post_posts, \
    remove_linked_in_profile_by_email
from cqc_lem.utilities.env_constants import LI_USER, LI_PASSWORD
from cqc_lem.utilities.linked_in_helper import login_to_linkedin, get_my_profile
from cqc_lem.utilities.selenium_util import get_docker_driver, clear_sessions, get_driver_wait_pair


def test_multiple_sessions():
    print("Running test")

    # Clear all sessions
    print("clearing Sessions")
    clear_sessions()

    # Get docker chrome instance
    driver = get_docker_driver(False)  # Non-headless

    driver.get("https://christopherqueenconsulting.com")

    # Get the driver title
    print("Window Title:", driver.title)

    driver2 = get_docker_driver()  # Headless

    driver2.get("https://www.linkedin.com/")

    # Get the driver title
    print("Window Title:", driver2.title)

    time.sleep(5 * 60)

    driver.get_cookies()

    # Close the browser
    driver.quit()
    driver2.quit()


def test_linked_login_over_multiple_sessions():
    print("Running Linked In Login Test")

    # Add User to DB
    add_user(LI_USER, LI_PASSWORD)

    # Clear all sessions
    print("clearing Sessions")
    clear_sessions()

    # Get docker chrome instance
    driver, wait = get_driver_wait_pair(False)

    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)
    print("Logged Into LinkedIn")

    # Get another docker chrome instance
    driver2, wait2 = get_driver_wait_pair(False)

    login_to_linkedin(driver2, wait2, LI_USER, LI_PASSWORD)
    print("Logged Into LinkedIn 2nd TIme")

    # Navigate driver 2 to google.com
    driver2.get("https://www.google.com")  # TODO: Why does this change all sessions instead of just one ???
    print("Navigated to: https://www.google.com")

    #time.sleep(5 * 60) # 5 minutes
    time.sleep(1 * 60) # 1 minute

    # Close the browser # NOTE: Hast to be closed in revers order they were opened
    driver2.quit()
    driver.quit()


def test_get_user_password_pair():
    user_email, user_password = get_user_password_pair_by_id(1)
    # print the results to the console
    print(f"Email: {user_email} | Password: {user_password}")


def test_get_ready_to_post_posts():
    get_ready_to_post_posts()
    # Get time for 15 minutes after now
    now = datetime.now()
    pre_post_time = now + timedelta(days=2)
    get_ready_to_post_posts(pre_post_time)


def test_get_my_profile():
    user_email, user_password = get_user_password_pair_by_id(1)
    driver, wait = get_driver_wait_pair(False)

    # Remove old profiles
    remove_linked_in_profile_by_email(user_email)

    # Keep track of current time for benchmark
    start_time = time.time()
    get_my_profile(driver, wait, user_email, user_password)
    # Track time 1 after this function is done
    end_time = time.time()
    print(f"1st Time to get profile: {end_time - start_time}")
    get_my_profile(driver, wait, user_email, user_password)
    # Track time 2 after this function is done
    end_time2 = time.time()
    print(f"2nd Time to get profile: {end_time2 - end_time}")


if __name__ == "__main__":
    # test_multiple_sessions()

    test_linked_login_over_multiple_sessions()# TODO: Get this working

    # test_get_user_password_pair()
    # test_get_ready_to_post_posts()
    # test_get_my_profile()
