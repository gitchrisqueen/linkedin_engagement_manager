import time
from cqc_lem.app.my_celery import app as shared_task
from cqc_lem.utilities.db import get_user_password_pair_by_id, remove_linked_in_profile_by_email
from cqc_lem.utilities.linkedin.helper import get_my_profile
from cqc_lem.utilities.selenium_util import get_driver_wait_pair


@shared_task.task
def test_task(seconds):
    time.sleep(seconds)
    return f"Slept for {seconds} seconds"


@shared_task.task
def test_get_my_profile(user_id:int):
    user_email, user_password = get_user_password_pair_by_id(user_id)
    driver, wait = get_driver_wait_pair(headless=True,session_name="AWS Test Get My Profile")

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
