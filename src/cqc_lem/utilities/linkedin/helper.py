import time
from typing import Optional

from cqc_lem.utilities.ai.ai_helper import get_industries_of_profile_from_ai
from cqc_lem.utilities.db import get_cookies, store_cookies, get_linked_in_profile_by_email, add_linkedin_profile, \
    get_linked_in_profile_by_url, get_linked_in_profile_by_user_id
from cqc_lem.utilities.linkedin.profile import LinkedInProfile
from cqc_lem.utilities.linkedin.scrapper import returnProfileInfo
from cqc_lem.utilities.logger import myprint, log_warning, log_error
from cqc_lem.utilities.selenium_util import load_cookies, click_element_wait_retry, get_element_wait_retry, getText
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def login_to_linkedin(driver: WebDriver, wait: WebDriverWait, user_email: str, user_password: str):
    linked_url = "https://www.linkedin.com"
    feed_url = "https://www.linkedin.com/feed/"
    login_url = "https://www.linkedin.com/login"

    _CHALLENGE_PATHS = ('/checkpoint/', '/authwall', '/uas/login', '/challenge/')
    # LinkedIn can land on /home, /feed, /mynetwork, etc. when logged in
    _LOGGED_IN_PATHS = ('/feed', '/home', '/mynetwork', '/jobs', '/messaging',
                        '/notifications', '/in/', '/search')

    def _is_challenge_url(url: str) -> bool:
        return any(p in url for p in _CHALLENGE_PATHS)

    def _is_logged_in(url: str) -> bool:
        return any(p in url for p in _LOGGED_IN_PATHS)

    # Load base domain first so cookies can be set against the right origin
    driver.get(linked_url)

    cookies = get_cookies(linked_url, user_email)

    if cookies:
        myprint("Found previous cookies. Loading them now!")
        load_cookies(driver, cookies)
        # Navigate directly to the feed — if cookies are valid LinkedIn serves it;
        # if invalid/expired it redirects to a login or challenge page
        driver.get(feed_url)
    else:
        myprint("No previous cookies found.")

    # Wait for the redirect / page load to settle
    time.sleep(2)

    if _is_challenge_url(driver.current_url):
        log_error(
            "LinkedIn security challenge detected after loading cookies — login blocked",
            action_type="login",
            error_message=f"Redirected to: {driver.current_url}",
        )
        raise RuntimeError(f"LinkedIn security challenge at {driver.current_url}")

    if _is_logged_in(driver.current_url):
        myprint(f"Already logged in! (current URL: {driver.current_url})")
        store_cookies(user_email, driver.get_cookies())
        myprint("Cookies stored to DB!")
        return

    # Cookies missing or expired — do a full credential login
    myprint(f"Logging in to LinkedIn as: {user_email}")

    # Go directly to the login page instead of clicking a "Sign in" link
    driver.get(login_url)
    time.sleep(1)

    if _is_challenge_url(driver.current_url):
        log_error(
            "LinkedIn security challenge detected on login page — login blocked",
            action_type="login",
            error_message=f"Redirected to: {driver.current_url}",
        )
        raise RuntimeError(f"LinkedIn security challenge at {driver.current_url}")

    username_field = get_element_wait_retry(driver, wait, 'username', "Finding Username Field", By.ID)
    password_field = get_element_wait_retry(driver, wait, 'password', "Finding Password Field", By.ID)

    username_field.send_keys(user_email)
    password_field.send_keys(user_password)
    click_element_wait_retry(driver, wait, '//*[@type="submit"]', "Finding Login Button", use_action_chain=True)

    wait.until(EC.title_contains("Feed"), "Waiting for Feed to load after login")

    if _is_logged_in(driver.current_url):
        myprint("Login successful!")
        store_cookies(user_email, driver.get_cookies())
        myprint("Cookies stored to DB!")
    else:
        myprint("Login failed. Check your credentials.")


def get_my_profile(driver, wait, user_email: str, user_password: str, user_id: Optional[int] = None) -> LinkedInProfile:
    profile = None

    # Prefer user_id-based cache key; fall back to email for backward compat.
    if user_id is not None:
        profile_json = get_linked_in_profile_by_user_id(user_id)
    else:
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
            if add_linkedin_profile(profile, user_id=user_id):
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


def get_linkedin_profile_from_url(driver, wait, profile_url, is_main_user=False, force_save=False):
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
