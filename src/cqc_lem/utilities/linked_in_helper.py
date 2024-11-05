import time

from selenium.webdriver.common.by import By

from cqc_lem.utilities.db import get_cookies, store_cookies
from cqc_lem.utilities.env_constants import LI_USER, LI_PASSWORD
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import load_cookies, click_element_wait_retry, get_element_wait_retry
from cqc_lem.utilities.utils import are_you_satisfied
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait


def login_to_linkedin(driver: WebDriver, wait: WebDriverWait, user_email: str, user_password: str):
    linked_url = "https://www.linkedin.com"

    # Check the Database if we have any stored cookies for the LinkedIn url.
    cookies = get_cookies(linked_url, user_email)

    driver.get(linked_url)

    # If we have cookies, try to load them into the driver
    if cookies:
        myprint("Found previous cookies. Loading them now!")
        load_cookies(driver, cookies)
        # Reload the page
        driver.get(linked_url)
    else:
        myprint("No previous cookies found.")

    # Wait for the login page to load
    time.sleep(2)

    if "feed" in driver.current_url:
        myprint("Already Logged in!")

        # update the cookies for this url in the database
        store_cookies(user_email, driver.get_cookies())
        myprint("Cookies stored to DB!")

    else:

        myprint(f"Logging in to LinkedIn as: {user_email} ")

        # click the Sign in button
        click_element_wait_retry(driver, wait, '//a[contains(text(),"Sign in")][1]', 'Clicking Sign In Button')

        # Wait for the login page to load
        # time.sleep(2)

        # Find the username and password input fields and log in
        username_field = get_element_wait_retry(driver, wait, 'username', "Finding Username Field", By.ID)
        password_field = get_element_wait_retry(driver, wait, 'password', "Finding Password Field", By.ID)

        # Fill in the form and submit
        username_field.send_keys(user_email)
        password_field.send_keys(user_password)
        click_element_wait_retry(driver, wait, '//*[@type="submit"]', "Finding Login Button", use_action_chain=True)

        # Wait for the home page to load
        # time.sleep(5)

        # Wait for title to change
        wait.until(EC.title_contains("Feed"), "Waiting for Title to change")

        # Check for successful login by looking for the search box
        if "feed" in driver.current_url:
            myprint("Login successful!")

            # update the cookies for this url in the database
            store_cookies(user_email, driver.get_cookies())
            myprint("Cookies stored to DB!")
        else:
            myprint("Login failed. Check your credentials.")
            #are_you_satisfied()
