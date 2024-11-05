import time
from enum import Enum

import chromedriver_autoinstaller
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException, \
    TimeoutException, WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait



def which_browser():
    """Prompts the user to select a value from the given enum."""
    enum = BrowserType

    print("Please select a browser:")
    for i, member in enumerate(enum):
        print(f"{member.value}: {member.name}")

    default = BrowserType.LOCAL_CHROME.value
    user_input = int(input('Enter your selection [' + str(default) + ']: ').strip() or default)

    try:
        bt = BrowserType(user_input)
        print(f"You selected {bt.name}")
        return bt
    except ValueError:
        print("Invalid selection.")
        return which_browser()


class BrowserType(Enum):
    DOCKER_CHROME = 1
    LOCAL_CHROME = 2
    BROWSERLESS = 3


def close_tab(driver: WebDriver, handles: list[str] = None, max_retry=3):
    if handles is None:
        handles = driver.window_handles

    wait = get_driver_wait(driver)

    try:
        driver.close()
    except WebDriverException as e:
        logger.exception("Failed to close browser/tab. Retrying.....")
        try:
            # Wait to close the new window or tab
            wait.until(EC.number_of_windows_to_be(len(handles) - 1), "Waiting for browser/tab to close.")
            pass
        except TimeoutException as te:
            logger.exception(te)
            if (max_retry > 0):
                close_tab(driver, handles, max_retry - 1)
                pass


def get_browser_driver():
    if IS_GITHUB_ACTION:
        browser_type = BrowserType.LOCAL_CHROME
    elif HEADLESS_BROWSER:
        browser_type = BrowserType.BROWSERLESS
    else:
        browser_type = which_browser()
    driver = None
    match browser_type:
        case BrowserType.DOCKER_CHROME:
            driver = get_docker_driver(HEADLESS_BROWSER)
        case BrowserType.LOCAL_CHROME:
            driver = get_local_chrome_driver(HEADLESS_BROWSER)
        case BrowserType.BROWSERLESS:
            driver = get_local_chrome_driver(True)
    return driver


def get_docker_driver(headless=True):
    options = getBaseOptions()
    # options.headless = headless
    if headless:
        options = add_headless_options(options)

    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Remote(
        command_executor='http://chrome:4444/wd/hub',
        options=options
    )
    if not headless:
        driver.maximize_window()

    return driver


def get_local_chrome_driver(headless=True):
    options = getBaseOptions()
    detached = True
    if headless:
        options = add_headless_options(options)
        # detached = False

    options.add_experimental_option("detach", detached)  # Change if you want to close when program ends
    # options.headless = headless
    driver = webdriver.Chrome(
        # TODO: Working before below but checking for streamlit cloud
        # service=Service(
        # ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install() # Not working locally but works on streamlit cloud but partially (inputs not going into formas)
        # ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install() # Works locally but not in streamlit cloud
        # ),
        service=Service(),  # Works locally and on streamlit cloud
        # TODO: Working before above but checking for streamlit cloud
        options=options
    )
    # driver.set_window_size(1800, 900)
    if not headless:
        driver.maximize_window()
    else:
        # TODO: Determine what size you want to set
        # driver.maximize_window()
        driver.set_window_size(1800, 900)

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


def getBaseOptions():
    options = Options()
    # options.add_argument("--incognito") # TODO: May cause issues with tabs
    prefs = {"download.default_directory": os.getcwd() + '/downloads',
             "download.prompt_for_download": False,
             "download.directory_upgrade": True,
             "plugins.always_open_pdf_externally": True}
    options.add_experimental_option("prefs", prefs)

    # options.page_load_strategy = 'eager'  # interactive
    # options.page_load_strategy = "normal"  # complete

    return options


def get_session_driver():
    driver = get_browser_driver()
    wait = get_driver_wait(driver)

    return driver, wait


def get_driver_wait(driver):
    return WebDriverWait(driver, WAIT_DEFAULT_TIMEOUT,
                         # poll_frequency=3,
                         ignored_exceptions=[
                             NoSuchElementException,  # This is handled individually
                             StaleElementReferenceException  # This is handled by our click_element_wait_retry method
                         ])


def click_element_wait_retry(driver: WebDriver, wait: WebDriverWait, find_by_value: str, wait_text: str,
                             find_by: str = By.XPATH,
                             max_try: int = MAX_WAIT_RETRY) -> WebElement:
    # element = False
    try:
        # Wait for element
        element = get_element_wait_retry(driver, wait, find_by_value, wait_text, find_by, max_try)

        # Wait for element to be clickable
        element = wait.until(EC.element_to_be_clickable(element))
        ActionChains(driver).move_to_element(element).click().perform()
        wait_for_ajax(driver)
        # element.click()

    except (StaleElementReferenceException, ElementNotInteractableException, TimeoutException) as se:
        logger.debug(wait_text + " | Stale or Not Interactable | .....retrying")
        time.sleep(5)  # wait 5 seconds
        driver.implicitly_wait(5)  # wait on driver 5 seconds
        if max_try > 1:
            element = click_element_wait_retry(driver, wait, find_by_value, wait_text, find_by, max_try - 1)
        else:
            #raise TimeoutException("Timeout while " + wait_text)
            raise se

    return element


def get_element_wait_retry(driver: WebDriver, wait: WebDriverWait, find_by_value: str, wait_text: str,
                           find_by: str = By.XPATH,
                           max_try: int = MAX_WAIT_RETRY) -> WebElement:
    # element = False
    try:
        # Wait for element
        # TODO: Below was working so put back if anything stops
        element = wait.until(
            lambda d: d.find_element(find_by, find_by_value),
            wait_text)
        # TODO: Above was working fine. Put back if below is not working
        # element = wait.until(
        #    EC.presence_of_element_located((find_by, find_by_value)), wait_text)

    except (StaleElementReferenceException, TimeoutException) as se:
        logger.debug(wait_text + " | Stale | .....retrying")
        time.sleep(5)  # wait 5 seconds
        driver.implicitly_wait(5)  # wait on driver 5 seconds
        if max_try > 1:
            element = get_element_wait_retry(driver, wait, find_by_value, wait_text, find_by, max_try - 1)
        else:
            #raise TimeoutException("Timeout while " + wait_text)
            raise se

    return element


def get_elements_as_list_wait_stale(wait: WebDriverWait, find_by_value: str, wait_text: str,
                                         find_by: str = By.XPATH, max_retry=3) -> list[WebElement]:
    elements = []

    try:
        elements = wait.until(lambda d: d.find_elements(find_by, find_by_value), wait_text)
        # elements_list = list(map(lambda x: getText(x), elements))
    except (StaleElementReferenceException, TimeoutException) as se:
        logger.debug(wait_text + " | Stale | .....retrying")
        time.sleep(5)  # wait 5 seconds
        if max_retry > 1:
            elements = get_elements_as_list_wait_stale(wait, find_by_value, wait_text, find_by, max_retry - 1)
        else:
            # raise NoSuchElementException("Could not find element by %s with value: %s" % (find_by, find_by_value))
            raise se

    return elements


def get_elements_text_as_list_wait_stale(wait: WebDriverWait, find_by_value: str, wait_text: str,
                                         find_by: str = By.XPATH, max_retry=3) -> list[str]:

    elements = get_elements_as_list_wait_stale(wait, find_by_value, wait_text, find_by, max_retry)
    elements_list = []
    for element in elements:
        try:
            elements_list.append(getText(element))
        except StaleElementReferenceException:
            # Attempt to relocate the element and retry
            try:
                logger.info("Element went stale. Relocating by XPath: %s" % element.get_attribute('xpath'))
                relocated_element = wait.until(lambda d: d.find_element(By.XPATH, element.get_attribute('xpath')))
                elements_list.append(getText(relocated_element))
            except StaleElementReferenceException:
                logger.warning("Element went stale and could not be relocated.")


    return elements_list


def get_elements_href_as_list_wait_stale(wait: WebDriverWait, find_by_value: str, wait_text: str,
                                         find_by: str = By.XPATH, max_retry=3) -> list:
    elements = get_elements_as_list_wait_stale(wait, find_by_value, wait_text, find_by, max_retry)
    elements_list = []
    for element in elements:
        try:
            elements_list.append(element.get_attribute('href'))
        except StaleElementReferenceException:
            # Attempt to relocate the element and retry
            try:
                logger.info("Element went stale. Relocating by XPath: %s" % element.get_attribute('xpath'))
                relocated_element = wait.until(lambda d: d.find_element(By.XPATH, element.get_attribute('xpath')))
                elements_list.append(relocated_element.get_attribute('href'))
            except StaleElementReferenceException:
                logger.warning("Element went stale and could not be relocated.")

    return elements_list


def wait_for_ajax(driver):
    wait = get_driver_wait(driver)
    try:
        wait.until(lambda d: d.execute_script('return jQuery.active') == 0)
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except Exception as e:
        pass


def wait_for_element_to_hide(wait: WebDriverWait, find_by_value: str, wait_text: str,
                             find_by: str = By.XPATH):
    try:
        wait.until(EC.invisibility_of_element_located((find_by, find_by_value)), wait_text)
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
