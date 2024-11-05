import time

from cqc_lem.utilities.db import add_user, get_user_password_pair_by_id
from cqc_lem.utilities.env_constants import LI_USER, LI_PASSWORD
from cqc_lem.utilities.selenium_util import get_docker_driver, clear_sessions, get_driver_wait_pair
from cqc_lem.utilities.linked_in_helper import login_to_linkedin


def test_multiple_sessions():
    print("Running test")

    # Clear all sessions
    print("clearing Sessions")
    clear_sessions()

    # Get docker chrome instance
    driver = get_docker_driver(False) # Non-headless


    driver.get("https://christopherqueenconsulting.com")

    # Get the driver title
    print("Window Title:", driver.title)

    driver2 = get_docker_driver() # Headless

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

    login_to_linkedin(driver,wait, LI_USER, LI_PASSWORD)

    # Get another docker chrome instance
    driver2, wait2 = get_driver_wait_pair(False)

    login_to_linkedin(driver2, wait2, LI_USER, LI_PASSWORD)

    # Navigate driver 2 to google.com
    driver2.get("https://www.google.com") # TODO: Why does this change all sessions instead of just one ???

    time.sleep(5 * 60)

    # Close the browser
    driver.quit()
    driver2.quit()

def test_get_user_password_pair():
    user_email, user_password = get_user_password_pair_by_id(1)
    # print the results to the console
    print(f"Email: {user_email} | Password: {user_password}")

if __name__ == "__main__":
    #test_multiple_sessions()
    test_linked_login_over_multiple_sessions()# TODO: Get this working
    #test_get_user_password_pair()
