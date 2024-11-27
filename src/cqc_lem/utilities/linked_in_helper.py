import time

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from cqc_lem.linked_in_profile import LinkedInProfile
from cqc_lem.utilities.ai.ai_helper import get_industries_of_profile_from_ai
from cqc_lem.utilities.db import get_cookies, store_cookies, get_linked_in_profile_by_email, add_linkedin_profile, \
    get_linked_in_profile_by_url
from cqc_lem.utilities.linked_in_scrapper import returnProfileInfo
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import load_cookies, click_element_wait_retry, get_element_wait_retry, getText


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
            # are_you_satisfied()


def get_my_profile(driver, wait, user_email: str, user_password: str) -> LinkedInProfile:
    profile = None

    # Check DB for serialized instance of profile
    profile_json = get_linked_in_profile_by_email(user_email)

    if profile_json is None:
        myprint(f"Previous Profile not found (or stale) in DB: {user_email}")
        login_to_linkedin(driver, wait, user_email, user_password)

        profile_url = "https://www.linkedin.com/in/"
        driver.get(profile_url)  # Need the page to redirect
        time.sleep(2)
        profile_url = driver.current_url  # Get the updated url

        profile_data = get_linkedin_profile_from_url(driver, wait, profile_url, True)

        if profile_data:

            profile = LinkedInProfile(**profile_data)
            # Add email and password to profile for later use
            profile.email = user_email
            profile.password = user_password

            # Add profile to DB for faster future retrieval
            if add_linkedin_profile(profile):
                myprint(f"Profile saved to DB: {profile.full_name}")
            else:
                myprint(f"Failed to save profile to DB: {profile.full_name}")
        else:
            myprint("Failed to get my profile data")
    else:
        # Ensure profile_json is a string
        profile_json_str = profile_json[0] if isinstance(profile_json, tuple) else profile_json
        # Create a LinkedInProfile object from json string data
        profile = LinkedInProfile.model_validate_json(profile_json_str)
        myprint(f"Profile Restored from DB: {profile.full_name}")

    return profile


def get_linkedin_profile_from_url(driver, wait, profile_url, is_main_user = False, force_save = False):
    # Get the profile from the DB if it exists
    profile_json = get_linked_in_profile_by_url(profile_url)

    if profile_json is None:

        # Set to empty dictionary
        profile_data = {}

        if profile_url != driver.current_url:
            # Open the profile URL
            driver.get(profile_url)
            time.sleep(2)

            # Check if current url changes (redirects)
            if profile_url != driver.current_url:

                # Use the current url as the profile url
                profile_url = driver.current_url

                # Get the profile using the new url
                return get_linkedin_profile_from_url(driver, wait, profile_url, is_main_user)



        # Get the company name
        company_element = get_element_wait_retry(driver, wait, '//button[contains(@aria-label,"Current company")]',
                                                 "Finding Company Name", element_always_expected=False)

        company_name = None
        if company_element:
            company_name = getText(company_element)

        profile_data = returnProfileInfo(driver, profile_url, company_name, is_main_user)


        if profile_data:
            profile = LinkedInProfile(**profile_data)
            # Use AI to determine industry of the profile
            industry = get_industries_of_profile_from_ai(profile, 1)
            profile.industry = industry

            # Save the profile to the DB
            if add_linkedin_profile(profile):
                myprint(f"Profile saved to DB: {profile.full_name}")

        # Use json to output to string
        # myprint(json.dumps(profile_data, indent=4))

    else:
        # Ensure profile_json is a string
        profile_json_str = profile_json[0] if isinstance(profile_json, tuple) else profile_json
        # Create a LinkedInProfile object from json string data
        profile = LinkedInProfile.model_validate_json(profile_json_str)
        profile_data = profile.model_dump()
        myprint(f"Profile Restored from DB: {profile.full_name}")

    return profile_data
