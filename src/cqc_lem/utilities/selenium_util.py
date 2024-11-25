import json
import random
import shutil
import time
from datetime import datetime, timedelta

import requests
import selenium
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common import JavascriptException, ElementNotInteractableException, StaleElementReferenceException, \
    TimeoutException, WebDriverException, NoSuchElementException, SessionNotCreatedException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from cqc_lem.utilities.env_constants import *
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.utils import create_folder_if_not_exists


def quit_gracefully(driver: WebDriver):
    try:
        driver.quit()
        myprint(f"Driver session closed.")
    except Exception as e:
        myprint(f"Error while quitting driver: {e}")
        pass


def get_available_session_driver_id(wait_for_available=True, wait_time=60, retry=3):
    # Query the Selenium Grid for available sessions
    url = f"http://{SELENIUM_HUB_HOST}:{SELENIUM_HUB_PORT}/status"
    response = requests.get(url)
    data = response.json()

    # Find an available session
    session_id = None
    for node in data['value']['nodes']:
        for slot in node['slots']:
            if slot['session'] is None:
                session_id = slot['id']['id']
                break
                # return session_id # No available sessions

            else:
                session = slot['session']
                # myprint(f"Session: {session}")
                session_id = session['sessionId']
                break
        if session_id:
            break

    if not session_id:
        if wait_for_available:
            if retry > 0:
                time.sleep(wait_time)
                return get_available_session_driver_id(wait_for_available, wait_time, retry - 1)
            else:
                raise TimeoutError("Timeout while waiting for available session")
        else:
            raise TimeoutError("No available session")

    return session_id


def get_docker_driver(headless=True, session_name: str = "ChromeTests"):
    options = getBaseOptions()
    # options.headless = headless
    if headless:
        options = add_headless_options(options)

    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')

    # Enable recording video
    options.set_capability('se:recordVideo', True)
    options.set_capability('se:timeZone', "America/New_York")
    options.set_capability('se:screenResolution', '1920x1080')
    options.set_capability('se:name', 'CQC_LEM (' + session_name + ')')

    # myprint(f"Options: {vars(options)}")

    driver = webdriver.Remote(
        command_executor=f'http://{SELENIUM_HUB_HOST}:{SELENIUM_HUB_PORT}',  # Works
        #command_executor=f'http://{SELENIUM_HUB_HOST}:4444',  # Works
        options=options
    )

    if not headless:
        driver.maximize_window()

    return driver


def add_headless_options(options: Options) -> Options:
    # options.add_argument("--headless=new") # <--- DOES NOT WORK
    # options.add_argument("--headless=chrome")  # <--- WORKING
    options.add_argument("--headless")  # <--- ???

    # Additional options while headless
    options.add_argument('--start-maximized')  # Working
    options.add_argument("--window-size=1920x1080")  # Working
    options.add_argument('--disable-popup-blocking')  # Working
    options.add_argument('--incognito')  # Working
    options.add_argument('--no-sandbox')  # Working
    options.add_argument('--enable-automation')  # Working
    options.add_argument('--disable-gpu')  # Working
    options.add_argument('--disable-extensions')  # Working
    options.add_argument('--disable-infobars')  # Working
    options.add_argument('--disable-browser-side-navigation')  # Working
    options.add_argument('--disable-dev-shm-usage')  # Working
    options.add_argument('--disable-features=VizDisplayCompositor')  # Working
    options.add_argument('--dns-prefetch-disable')  # Working
    options.add_argument("--force-device-scale-factor=1")  # Working

    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    return options


def getBaseOptions(base_download_directory: str = None):
    options = Options()
    # options.add_argument("--incognito") # May cause issues with tabs
    if base_download_directory is None:
        base_download_directory = os.getcwd()
    prefs = {"download.default_directory": base_download_directory + '/downloads',
             "download.prompt_for_download": False,
             "download.directory_upgrade": True,
             "plugins.always_open_pdf_externally": True}
    options.add_experimental_option("prefs", prefs)

    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Options to make us undetectable (Review https://amiunique.org/fingerprint from the browser to verify)
    options.add_argument("window-size=1920x1080")
    options.add_argument(
        # "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.91 Safari/537.36"
    )

    #options.set_capability("browserVersion", "100.0")  # This is needed for this version

    # options.page_load_strategy = 'eager'  # interactive
    # options.page_load_strategy = "normal"  # complete

    return options


def create_driver(headless: bool = HEADLESS_BROWSER, create_copy: bool = False, port: int = 9515):
    # Setup Selenium options (headless for Docker use)
    options = Options()
    if headless:
        options.add_argument('--headless')  # Run in headless mode for Docker
        display = Display(visible=False, size=(800, 800))
        display.start()

    driver_path = ChromeDriverManager().install()
    print(f"Chrome Driver Path: {driver_path}")

    service = Service(driver_path, port=port)

    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    debugging_port = int(9222 + (port - 9515))
    debugging_port = 9222  # Keep the same to see what happens
    myprint(f"Debugging port: {debugging_port}")
    options.add_argument('--remote-debugging-port=' + str(
        debugging_port))  # This is to avoid DevToolsActivePort file doesn't exist error
    options.add_experimental_option("detach", False)  # Change if you want to close when program ends

    # Options to make us undetectable (Review https://amiunique.org/fingerprint from the browser to verify)
    options.add_argument("window-size=1280,800")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")

    if not headless:

        # Create a sub_folder for the current user to use as the profile folder
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Define the local path relative to the current file
        profile_folder_path = os.path.join(current_dir, 'selenium_profiles')

        create_folder_if_not_exists(profile_folder_path)

        # If create_copy the copy the folder to a second folder using timestamp and random number
        if create_copy:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_number = random.randint(1000, 9999)
            profile_folder_path_copy = os.path.join(current_dir, 'selenium_profiles',
                                                    f"{LI_USER}_{timestamp}_{random_number}")

            def ignore_socket_files(dir, files):
                return [f for f in files if
                        os.path.islink(os.path.join(dir, f)) or os.path.ismount(os.path.join(dir, f))]

            if os.path.exists(profile_folder_path):
                shutil.copytree(profile_folder_path, profile_folder_path_copy, ignore_dangling_symlinks=True,
                                dirs_exist_ok=True, ignore=ignore_socket_files)
                myprint(f"Profile folder copied to: {profile_folder_path_copy}")
                profile_folder_path = profile_folder_path_copy
            else:
                myprint(f"Source directory does not exist: {profile_folder_path}")

        # Set up the Chrome driver options
        # Note: This will create a new profile for each run (not shared between runs)
        # options.add_argument("--user-data-dir=" + profile_folder_path)  # This is to keep the browser logged in between runs
        options.add_argument(
            "user-data-dir=" + str(profile_folder_path))  # This is to keep the browser logged in between runs
        options.add_argument("--profile-directory=" + LI_USER)

    # Set up the Chrome driver
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Remove navigator.webdriver Flag using JavaScript
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except JavascriptException as je:
        myprint(f"Error while removing navigator.webdriver flag: {je}")
        pass

    return driver


def click_element_wait_retry(driver: WebDriver, wait: WebDriverWait, find_by_value: str, wait_text: str,
                             find_by: str = By.XPATH,
                             max_try: int = MAX_WAIT_RETRY,
                             parent_element: WebElement = None,
                             use_action_chain=False,
                             element_always_expected=True) -> WebElement:
    # element = False
    try:
        # Wait for element
        element = get_element_wait_retry(driver, wait, find_by_value, wait_text, find_by, max_try, parent_element,
                                         element_always_expected)

        if element:
            # Wait for element to be clickable
            element = wait.until(EC.element_to_be_clickable(element))
            if use_action_chain:
                ActionChains(driver).move_to_element(element).click().perform()
                wait_for_ajax(driver)
            else:
                element.click()
        else:
            if element_always_expected:
                raise ElementNotInteractableException("Element not found or interactable")

    except ElementNotInteractableException as se:
        if max_try > 1:
            myprint(wait_text + " | Not Interactable | .....retrying")
            time.sleep(5)  # wait 5 seconds
            driver.implicitly_wait(5)  # wait on driver 5 seconds
            element = click_element_wait_retry(driver, wait, find_by_value, wait_text, find_by, max_try - 1,
                                               parent_element)
        else:

            if element_always_expected:
                # raise TimeoutException("Timeout while " + wait_text)
                myprint(f"Failed to find or interact with element: {wait_text} | Error: {se}")
                # return None
                raise se
            else:
                myprint(f"Failed to find or interact with element: {wait_text}")
                element = None

    except (StaleElementReferenceException, TimeoutException) as st:
        myprint(wait_text + " | Stale or Timed out | ")
        if element_always_expected:
            raise st
        else:
            element = None

    return element


def get_element_wait_retry(driver: WebDriver, wait: WebDriverWait, find_by_value: str, wait_text: str,
                           find_by: str = By.XPATH,
                           max_try: int = MAX_WAIT_RETRY,
                           parent_element: WebElement = None,
                           element_always_expected=True) -> WebElement:
    # element = False
    try:
        # Wait for element
        if parent_element:
            # Use the parent element to find the child element
            element = wait.until(
                lambda d: parent_element.find_element(find_by, find_by_value),
                wait_text)
        else:
            # Use the driver to find the element
            element = wait.until(
                lambda d: d.find_element(find_by, find_by_value),
                wait_text)

    except (StaleElementReferenceException, TimeoutException) as se:
        if max_try > 1:
            myprint(wait_text + " | Stale | .....retrying")
            time.sleep(5)  # wait 5 seconds
            driver.implicitly_wait(5)  # wait on driver 5 seconds
            element = get_element_wait_retry(driver, wait, find_by_value, wait_text, find_by, max_try - 1,
                                             parent_element, element_always_expected)
        else:
            # raise TimeoutException("Timeout while " + wait_text)
            if element_always_expected:
                raise se
            else:
                myprint(f"Failed to find element: {wait_text}")
                element = None

    return element


def get_elements_as_list_wait_stale(wait: WebDriverWait, find_by_value: str, wait_text: str,
                                    find_by: str = By.XPATH, max_retry=3) -> list[WebElement]:
    elements = []

    try:
        elements = wait.until(lambda d: d.find_elements(find_by, find_by_value), wait_text)
        # elements_list = list(map(lambda x: getText(x), elements))
    except (StaleElementReferenceException, TimeoutException) as se:
        myprint(wait_text + " | Stale | .....retrying")
        time.sleep(5)  # wait 5 seconds
        if max_retry > 1:
            elements = get_elements_as_list_wait_stale(wait, find_by_value, wait_text, find_by, max_retry - 1)
        else:
            # raise NoSuchElementException("Could not find element by %s with value: %s" % (find_by, find_by_value))
            raise se

    return elements


def wait_for_ajax(driver):
    wait = get_driver_wait(driver)
    try:
        wait.until(lambda d: d.execute_script('return jQuery.active') == 0)
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except Exception as e:
        pass


def getText(curElement: WebElement):
    """
    Get Selenium element text

    Args:
        curElement (WebElement): selenium web element
    Returns:
        str
    Raises:
    """
    # # for debug
    # elementHtml = curElement.get_attribute("innerHTML")
    # print("elementHtml=%s" % elementHtml)

    elementText = curElement.text  # sometimes does not work

    if not elementText:
        elementText = curElement.get_attribute("innerText")

    if not elementText:
        elementText = curElement.get_attribute("textContent")

    # print("elementText=%s" % elementText)
    return elementText


def close_tab(driver: WebDriver, handles: list[str] = None, max_retry=3):
    if handles is None:
        handles = driver.window_handles

    wait = get_driver_wait(driver)

    try:
        driver.close()
    except WebDriverException as e:
        myprint("Failed to close browser/tab. Retrying.....")
        try:
            # Wait to close the new window or tab
            wait.until(EC.number_of_windows_to_be(len(handles) - 1), "Waiting for browser/tab to close.")
            pass
        except TimeoutException as te:
            myprint(te)
            if (max_retry > 0):
                close_tab(driver, handles, max_retry - 1)
                pass


def get_driver_wait(driver):
    return WebDriverWait(driver, WAIT_DEFAULT_TIMEOUT,
                         # poll_frequency=3,
                         ignored_exceptions=[
                             NoSuchElementException,  # This is handled individually
                             StaleElementReferenceException  # This is handled by our click_element_wait_retry method
                         ])


def get_driver_wait_pair(headless=False, session_name: str = "ChromeTests", max_retry=3):
    # Create the driver
    if USE_DOCKER_BROWSER:
        for attempt in range(max_retry):
            try:
                driver = get_docker_driver(headless=headless, session_name=session_name)
                break  # Exit the loop if successful
            except SessionNotCreatedException as e:
                if attempt == max_retry - 1:
                    raise e  # Raise the exception if max retries reached
                wait_time = 30 * (2 ** attempt)  # Exponential backoff starting at 30 seconds
                time.sleep(wait_time)  # Wait before retrying
    else:
        driver = create_driver(headless=headless)

    wait = get_driver_wait(driver)

    myprint("Driver and Wait created. Waiting for one window handle")

    # Wait until at least one window handle is available (indicating that the browser has started)
    wait.until(lambda driver: len(driver.window_handles) > 0)

    myprint("Window handle found. Returning driver and wait pair.")

    # Give some time for multiple calls
    # time.sleep(2)

    return driver, wait


def clear_sessions():
    #base_url = f"http://{SELENIUM_HUB_HOST}:4444"
    base_url = f"http://{SELENIUM_HUB_HOST}:{SELENIUM_HUB_PORT}"
    response = requests.get(f"{base_url}/status")
    data = json.loads(response.text)

    for node in data['value']['nodes']:
        for slot in node['slots']:
            if slot['session']:
                session_id = slot['session']['sessionId']
                delete_url = f"{base_url}/session/{session_id}"
                requests.delete(delete_url)


def load_cookies(driver: WebDriver, cookies: list[dict]):
    for cookie in cookies:
        expiry = cookie['expiry']
        if expiry is not None:
            try:
                expiry = int(expiry)
            except ValueError:
                expiry = int((datetime.now() + timedelta(days=30)).timestamp())
        else:
            expiry = int((datetime.now() + timedelta(days=30)).timestamp())
        try:
            driver.add_cookie({
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie['domain'] if cookie['domain'] else None,
                'path': cookie['path'] if cookie['path'] else None,
                'expiry': expiry,
                'secure': bool(cookie['secure']) if cookie['secure'] is not None else False,
                'httpOnly': bool(cookie['http_only']) if cookie['http_only'] is not None else False,
            })
        except selenium.common.exceptions.InvalidArgumentException as e:
            myprint(f"Error loading cookie: {cookie}")
            myprint(f"Exception: {e}")
            pass
