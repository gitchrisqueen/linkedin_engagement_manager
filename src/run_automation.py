import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import mysql.connector
from dotenv import load_dotenv
from openai import OpenAI
from selenium import webdriver
from selenium.common import NoSuchElementException, WebDriverException, TimeoutException, \
    StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Load .env file
load_dotenv()

MAX_WAIT_RETRY = 3
WAIT_TIMEOUT = 3

# Retrieve MySQL connection details from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

# Retrieve LinkedIn credentials from environment variables
LI_USER = os.getenv('LI_USER')
LI_PASSWORD = os.getenv('LI_PASSWORD')

# Retrieve OpenAI API key from environment variables
# openai.api_key = os.getenv("OPENAI_API_KEY") #<---- This is done be default
client = OpenAI(
    # This is the default and can be omitted
    # api_key=os.environ.get("OPENAI_API_KEY"),
)

# Global flag to indicate when to stop the thread
stop_post_commenting_thread = threading.Event()


def myprint(message):
    sys.stdout.flush()
    sys.stdout.write('\r' + message + '\n')
    sys.stdout.flush()


def countdown_timer(seconds):
    global stop_post_commenting_thread
    while seconds > 0 and not stop_post_commenting_thread.is_set():
        mins, secs = divmod(seconds, 60)
        timer = f'Time left: {mins:02d}:{secs:02d}'
        sys.stdout.write('\r' + timer)
        sys.stdout.flush()
        time.sleep(1)
        seconds -= 1
    sys.stdout.write('\rTime left: 00:00\n')
    sys.stdout.flush()
    stop_post_commenting_thread.set()  # Set the flag to stop other threads


def create_database():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

    cursor = conn.cursor()
    with open('schema.sql', 'r') as schema_file:
        schema = schema_file.read()
        cursor.execute(schema, multi=True)

    conn.commit()
    cursor.close()
    conn.close()

    myprint("Database creation finished!")


class Satisfactory(Enum):
    YES = 1
    NO = 0


def are_you_satisfied():
    """Prompts the user to select if they are satisfied or not."""

    enum = Satisfactory

    print("Are you satisfied?")
    for i, member in enumerate(enum):
        print(f"{member.value}: {member.name}")

    default = Satisfactory.YES
    default_value = default.value
    user_input = int(input('Enter your selection [' + str(default_value) + ']: ').strip() or default_value)

    try:
        sf = Satisfactory(user_input)
        print(f"You selected {sf.name}")
        return sf.value == default_value
    except ValueError:
        print("Invalid selection.")
        return are_you_satisfied() == default_value


def create_driver():
    # Setup Selenium options (headless for Docker use)
    options = Options()
    # TODO: Uncomment below
    # options.add_argument('--headless')  # Run in headless mode for Docker
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option("detach", True)  # Change if you want to close when program ends

    # Options to make us undetectable (Review https://amiunique.org/fingerprint from the browser to verify)
    options.add_argument("window-size=1280,800")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
    options.add_argument(
        "user-data-dir=/Users/christopherqueen/workspace/linkedin_engagement_manager/src/selenium_profile")  # This is to keep the browser logged in between runs

    # Set up the Chrome driver
    driver = webdriver.Chrome(options=options)

    # Remove navigator.webdriver Flag using JavaScript
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

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


def login_to_linkedin(driver, wait):
    driver.get("https://www.linkedin.com")

    # Wait for the login page to load
    time.sleep(2)

    if "feed" in driver.current_url:
        myprint("Already Logged in!")
    else:

        # click the Sign in button
        click_element_wait_retry(driver, wait, '//a[contains(text(),"Sign in")][1]', 'Clicking Sign In Button')

        # Wait for the login page to load
        # time.sleep(2)

        # Find the username and password input fields and log in
        username_field = get_element_wait_retry(driver, wait, 'username', "Finding Username Field", By.ID)
        password_field = get_element_wait_retry(driver, wait, 'password', "Finding Password Field", By.ID)

        # Fill in the form and submit
        username_field.send_keys(LI_USER)
        password_field.send_keys(LI_PASSWORD)
        click_element_wait_retry(driver, wait, '//*[@type="submit"]', "Finding Login Button", use_action_chain=True)

        # Wait for the home page to load
        # time.sleep(5)

        # Check for successful login by looking for the search box
        if "feed" in driver.current_url:
            myprint("Login successful!")
        else:
            myprint("Login failed. Check your credentials.")
            are_you_satisfied()


def navigate_to_feed(driver, wait):
    # Check to see if driver url is not already on feed
    if "feed" not in driver.current_url:
        # Navigate to LinkedIn home feed
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(5)  # Wait for the feed to load

    # Find and click the "Sort by" dropdown
    click_element_wait_retry(driver, wait, '//button/hr',
                             "Clicking Sort By Dropdown", use_action_chain=True)

    # time.sleep(1)

    # Select "Recent" from the dropdown

    click_element_wait_retry(driver, wait, '//div[contains(@class,"artdeco-dropdown__content--is-open")]//ul/li[2]',
                             "Selecting Recent Option")

    time.sleep(3)  # Wait for the page to refresh with recent posts

    # are_you_satisfied()


def get_feed_posts(driver, wait, num_posts=10):
    posts = []

    # Find the posts in the feed
    post_element_xpath = '//div[contains(@data-id, "urn:li:activity")]'
    post_elements = get_elements_as_list_wait_stale(wait, post_element_xpath, "Finding Posts in Feed")

    if len(post_elements) == 0:
        print(" No posts found in feed.")

    while len(post_elements) < num_posts:
        # Scroll to the bottom of the page to load more posts
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait for the posts to load
        time.sleep(5)

        # Find the posts in the feed
        new_post_elements = get_elements_as_list_wait_stale(wait, post_element_xpath, "Finding New Posts in Feed")

        if len(new_post_elements) == len(post_elements):
            # No new posts. Exit the loop
            break

        post_elements = new_post_elements

    # Limit to the number of posts we want
    for post in post_elements[:num_posts]:
        # Get the link to the post
        post_link = 'https://www.linkedin.com/feed/update/' + post.get_attribute('data-id')

        posts.append({
            'link': post_link,

        })

    return posts


def simulate_reading_time(content):
    # Estimate reading time based on the number of words (average human reads 200-300 words per minute)
    words = len(content.split())
    read_time = words / 250 * 60  # Convert to seconds
    # Round to integer
    return round(read_time)


def simulate_thinking_time():
    # Random thinking time between 2 and 5 seconds
    return round(random.uniform(2, 5))


def simulate_writing_time(content):
    # Simulate a human writing time (around 5 characters per second)
    char_count = len(content)
    writing_time = char_count / 5
    return round(writing_time)


def generate_ai_response_test(post_content, post_img_url=None,
                              expertise="dog that speaks to humans"):
    prompt = f"Please tell me:\n\n'{post_content}'"

    content = [{"type": "text", "text": prompt}]

    if post_img_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"{post_img_url}"},
        })

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a {expertise}. Respond to all user prompts with 'bark bark' followed by your response to the prompt then ending in 'bark bark'"""
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Call the API with the system and user prompt only (no memory of past prompts)
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Specify the model you want to use
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        # temperature=0.3,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    # Extract and return the model's response
    comment = response.choices[0].message.content.strip()
    return comment


def generate_ai_response(post_content, post_img_url=None,
                         expertise="AI Consultant empowering enterprises with AI solutions"):
    prompt = f"Please give me a comment in response to the following LinkedIn Content:\n\n'{post_content}'"

    content = [{"type": "text", "text": prompt}]

    if post_img_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"{post_img_url}"},
        })

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""
Act like a seasoned {expertise} with over 50 years of experience. You are also an expert in LinkedIn, Social Media, and Social Marketing, with a deep understanding of how to leverage these platforms to enhance online presence. You specialize in analyzing LinkedIn content and crafting thoughtful, engaging comments that highlight your authority in the subject matter.

Your main objective is to generate insightful, relevant comments that initiate and maintain engagement. Ensure your comments reflect your extensive expertise, drawing connections between the content presented and your own deep knowledge as a {expertise}.

Task 1: When reading LinkedIn posts, identify the key points and align your commentary to these topics. Reflect on how your expertise can contribute to the conversation.
Task 2: Create comments that are conversational, inviting others to engage while keeping a professional yet approachable tone.
Task 3: Be concise but impactful—focus on making the first 2-3 lines (~400 characters) compelling, as they are crucial for grabbing attention before the ‘see more’ button is clicked.
Task 4: Ensure the comment is directly relevant to the content or discussion, increasing its value and engagement potential.
Task 5: Keep comments under 1250 characters, including spaces and punctuation, ensuring they are informative, concise, and inspire further discussion.
Task 6: If any links are present in the content, review them to stay well-informed and use this insight to make your commentary more profound and relevant.
Be original, creative, and insightful in your comments, always aiming to foster deeper conversations with the content creator and other readers. Your goal is to provide value while maintaining the interest of future readers.

Take a deep breath and work on this problem step-by-step.

Only respond with your final comment once you are satisfied with its quality and relevance.
            """
    }

    # User prompt to be sent with each API call
    user_message = {
        "role": "user",
        "content": content
    }

    # Choose temperature between .5 and .7 rounded to 2 decimal places
    temperature = round(random.uniform(.5, .7), 2)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system_prompt, user_message],  # System prompt + current user prompt
        temperature=temperature,  # Adjust this parameter as per your needs
        # max_tokens=150  # Set token limit as required
    )

    comment = response.choices[0].message.content.strip()
    return comment


def post_comment(driver, wait, comment_text):
    """Post a comment to the currently opened post in the driver window"""

    # Find the comment input area
    comment_box = click_element_wait_retry(driver, wait, '//div[contains(@aria-placeholder, "Add a comment")]',
                                           "Finding the Comment Input Area", use_action_chain=True)

    # clear the contents of the comment_box
    comment_box.clear()

    # Simulate typing the comment
    for char in comment_text:
        try:
            if ord(char) > 0xFFFF:
                # Use JavaScript to set the value for characters outside the BMP
                driver.execute_script("arguments[0].value += arguments[1];", comment_box, char)
            else:
                comment_box.send_keys(char)
        except Exception as e:
            myprint("Error while sending char(" + char + "): " + str(e))

        type_speed_reducer = .5
        time.sleep(random.uniform(0.05 * type_speed_reducer, 0.15 * type_speed_reducer))  # Simulate human typing speed

    # Sleep so post button shows up
    time.sleep(2)

    try:
        # Find and click the post button
        click_element_wait_retry(driver, wait, '//button[contains(@class, "comments-comment-box__submit-button--cr")]',
                                 "Clicking Post Button")

        # TODO: Update database with record of comment to this post (use the link)

    except NoSuchElementException:
        # If the post button is not found, send a return key to post the comment
        comment_box.send_keys('\n')

    # Get the main like button
    main_like_button = get_element_wait_retry(driver, wait,
                                              '//button[contains(@aria-label, "Like") and contains(@class,"artdeco-button--4")]',
                                              "Finding Main Like Button")

    # Create an instance of ActionChains
    actions = ActionChains(driver)

    max_retries = 3
    for attempt in range(max_retries):
        # Hover over the main like button
        actions.move_to_element(main_like_button).perform()

        # Wait for new elements to appear (adjust time as needed)
        time.sleep(.5)
        try:
            choices = []
            like_button = get_element_wait_retry(driver, wait, '//button[contains(@aria-label, "Like")]',
                                                 "Finding Like Button", element_always_expected=False, max_try=1)
            if like_button:
                choices.append(like_button)
            celebrate_button = get_element_wait_retry(driver, wait, '//button[contains(@aria-label, "Celebrate")]',
                                                      "Finding Celebrate Button", element_always_expected=False, max_try=1)
            if celebrate_button:
                choices.append(celebrate_button)
            insightful_button = get_element_wait_retry(driver, wait,
                                                       '//button[contains(@aria-label, "Insightful")]',
                                                       "Finding Insightful Button", element_always_expected=False, max_try=1)
            if insightful_button:
                choices.append(insightful_button)
            button_to_click = random.choice(choices)
            button_to_click.click()
            break  # Exit loop if click is successful
        except ElementClickInterceptedException as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait a bit before retrying
            else:
                myprint(f"Failed to click Post Reaction: {e}")


def check_commented(driver, wait):
    """See if the current open url we've alredy posted on"""
    already_commented = False
    post_link = driver.current_url

    # Check if we have already commented on this post

    # TODO:  1. Check against Database

    # 2. Check against LinkedIn Recent Activity Comments
    if not already_commented:

        # See if the current user is in the comments section
        alink = get_element_wait_retry(driver, wait,
                                       '//div[contains(@class,"comments-comment-list__container")]//a[contains(@aria-label,"• You")]',
                                       "Finding Comments Container with 'You' In it", max_try=1,
                                       element_always_expected=False)
        if alink:
            already_commented = True

    return already_commented


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
    return WebDriverWait(driver, WAIT_TIMEOUT,
                         # poll_frequency=3,
                         ignored_exceptions=[
                             NoSuchElementException,  # This is handled individually
                             StaleElementReferenceException  # This is handled by our click_element_wait_retry method
                         ])


def automate_commenting(driver, wait):
    global stop_post_commenting_thread

    navigate_to_feed(driver, wait)

    # Get 10 posts from the feed
    posts = get_feed_posts(driver, wait, num_posts=10)

    current_tab = driver.current_window_handle
    handles = driver.window_handles

    for post in posts:
        if stop_post_commenting_thread.is_set():
            myprint("Stopping thread...")
            break

        # Switch back to tab
        driver.switch_to.window(current_tab)

        post_link = post['link']
        myprint(f"Post Link: {post_link}")

        # Wait for the new window or tab
        driver.switch_to.new_window('tab')
        wait.until(EC.new_window_is_opened(handles))

        # Switch to post url
        driver.get(post_link)

        # Check to make sure we haven't already commented on this post
        if check_commented(driver, wait):
            myprint("Already commented on this post. Skipping...")
            # Close tab when done
            close_tab(driver)
            continue
        else:
            myprint("Haven't commented on this post yet. Proceeding...")

        try:
            # Get the post content (text) if available
            content = getText(
                get_element_wait_retry(driver, wait,
                                       '//div[contains(@class,"fie-impression-container")]//div[contains(@class,"feed-shared-inline-show-more-text")]',
                                       "Finding Post Text"))
        except Exception as wde:
            myprint("Failed to get post content. Skipping.." + str(wde))

            # Close tab when done
            close_tab(driver)
            continue  # Skip posts without readable content

        img_url = None

        # Get the image of post if available (Will not retry)
        img_element = get_element_wait_retry(driver, wait,
                                             '//div[contains(@class,"fie-impression-container")]//div[contains(@class,"update-components-image")]//img',
                                             'Finding Post Image', max_try=0, element_always_expected=False)
        if img_element:
            img_url = img_element.get_attribute('src')

        # NOTE: There is no read more button on full post url page
        # Click the "Read More" Button if exist
        # click_element_wait_retry(driver, wait, '//button[contains(@class, "see-more")]', "Clicking Read More Button",
        #                         parent_element=post['element'], max_try=0, element_always_expected=False)

        # Simulate reading the post
        read_time = simulate_reading_time(content)
        myprint(f"Simulated Reading... for {read_time} seconds")
        time.sleep(read_time)

        # Simulate thinking time
        thinking_time = simulate_thinking_time()
        myprint(f"Simulated Thinking... for {thinking_time} seconds")
        time.sleep(thinking_time)

        # Generate AI response
        comment_text = generate_ai_response(content, img_url)

        myprint(f"AI Generated Comment: {comment_text}")
        # Simulate typing the AI-generated comment
        # for char in comment_text:
        #    if char == '\n':
        #        myprint()
        #    else:
        #        myprint(char, end='')
        #    time.sleep(random.uniform(0.05, 0.15))  # Simulate human typing speed

        # Comment out the actual posting of the comment for now
        post_comment(driver, wait, comment_text)

        # Close tab when done
        close_tab(driver)


    # Switch back to tab
    driver.switch_to.window(current_tab)


def test_already_commented(driver, wait):
    login_to_linkedin(driver, wait)

    post_links = [
        "https://www.linkedin.com/posts/axellemalek_this-is-a-sketch-to-photo-ai-from-ideogram-ugcPost-7246808027901661184-_ewe/?utm_source=share&utm_medium=member_desktop",
        'https://www.linkedin.com/feed/update/urn:li:activity:7254086938373095424/']

    # Check each post_link to see if we commented
    for post_link in post_links:
        myprint(f"Checking Commented Status for {post_link}")
        # Navigate to the url first
        driver.get(post_link)
        if check_commented(driver, wait):
            myprint("Already commented on this post. Skipping...")
        else:
            myprint("Not commented on this post yet. Proceeding...")


def test_ai_responses():
    prompts = [{"prompt": "1. What is in this image? 2. Why is it funny?",
                "image_url": "https://media.gettyimages.com/id/146582583/photo/cat-sandwich.jpg?s=1024x1024&w=gi&k=20&c=rhUM1pdFbwPGsuO7q64oPWVe7WSkYqJOUGBZJp5rLcI="},
               {"prompt": "1. What is the main color of this car? 2. What type of car is it?",
                "image_url": "https://www.dodgegarage.com/news-api/wp-content/uploads/2022/11/BlackGhost_IMG002.jpg"},
               {
                   "prompt": "1. What was the first question I asked you? 2. How do the first 2 images I sent relate to each other",
                   "image_url": None}]

    for prompt in prompts:
        comment_text = generate_ai_response_test(prompt['prompt'], prompt['image_url'])
        myprint(f"User Prompt: {prompt['prompt']}")
        myprint(f"AI Generated Comment: {comment_text}")


def start_process():
    # Set Timer for 3 minutes
    time_in_secs = 60 * 15

    # Make sure the database is created
    # create_database() # TODO: Uncomment this line

    # Create the driver
    driver = create_driver()
    wait = get_driver_wait(driver)

    login_to_linkedin(driver, wait)
    # test_already_commented(driver, wait)
    # automate_commenting(driver, wait)

    # Create the countdown timer in a separate thread
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.submit(countdown_timer, time_in_secs)
        executor.submit(automate_commenting, driver, wait)

    myprint("Time is up. Closing the browser")

    # Close the browser
    driver.quit()

def automate_profile_viewer_dms(driver, wait):
    #Navigate to profile view page
    driver.get("https://www.linkedin.com/analytics/profile-views/")


    # Get Each Viewer within the last day (or time of dm run via database log)

    # For each viewer# TODO: Use AI and memory to get insightful comments to send viewers

        # If not connected send them a connection request
            # Mention something specific about their profile or company to show genuine interest and that you've done your research


        # If they are connected
            # engage with their content

            # Send DM - offer something of value—whether it's insights, resources, or potential collaboration opportunities.




if __name__ == "__main__":
    # Create the driver
    # driver = create_driver()
    # wait = get_driver_wait(driver)
    # test_already_commented(driver, wait)

    # test_ai_responses()

    start_process()
    myprint("Process finished")
