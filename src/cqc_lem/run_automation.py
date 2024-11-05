import json
import json
import random
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from selenium.common import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from cqc_lem.linked_in_profile import LinkedInProfile
# from celery import shared_task
from cqc_lem.my_celery import app as shared_task
from cqc_lem.utilities.date import convert_viewed_on_to_date
from cqc_lem.utilities.db import get_user_password_pair_by_id, get_user_id
from cqc_lem.utilities.env_constants import LI_USER, LI_PASSWORD
from cqc_lem.utilities.linked_in_helper import login_to_linkedin, get_my_profile, get_linkedin_profile_from_url
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import create_driver, click_element_wait_retry, \
    get_element_wait_retry, get_elements_as_list_wait_stale, getText, close_tab, get_driver_wait, get_driver_wait_pair
from cqc_lem.utilities.utils import debug_function

# Load .env file
load_dotenv()

# Retrieve OpenAI API key from environment variables
# openai.api_key = os.getenv("OPENAI_API_KEY") #<---- This is done be default
client = OpenAI(
    # This is the default and can be omitted
    # api_key=os.environ.get("OPENAI_API_KEY"),
)

# Global flag to indicate when to stop the thread
stop_all_thread = threading.Event()
time_remaining_seconds = 0


def countdown_timer(seconds):
    global stop_all_thread
    global time_remaining_seconds
    time_remaining_seconds = seconds
    while seconds > 0 and not stop_all_thread.is_set():
        mins, secs = divmod(seconds, 60)
        timer = f'Time left: {mins:02d}:{secs:02d}'
        sys.stdout.write('\r' + timer)
        sys.stdout.flush()
        time.sleep(1)
        seconds -= 1
        time_remaining_seconds = seconds
    sys.stdout.write('\rTime left: 00:00\n')
    sys.stdout.flush()
    stop_all_thread.set()  # Set the flag to stop other threads


def get_time_remaining_seconds():
    global time_remaining_seconds
    return time_remaining_seconds


def get_time_remaining_minutes():
    return get_time_remaining_seconds() // 60


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


def generate_ai_response_test():
    post_content = "Today was a good day to go outside"
    post_img_url = None,
    expertise = "dog that speaks to humans"

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


def generate_ai_response(post_content, profile: LinkedInProfile, post_img_url=None):
    image_attached = "(image attached)" if post_img_url else ""

    prompt = (f"""Please give me a comment in response to the following LinkedIn Content as the following LinkedIn User,"
              
                LinkedIn User Profile:\n\n{profile.model_dump_json()}\n\n"
              
                LinkedIn Content{image_attached}:\n\n'{post_content}'

                Only provide the final comment once it perfectly reflects the LinkedIn user’s style
                
                Do not surround your response in quotes or added any additional system text.

                Take a deep breath and work on this problem step-by-step.""")

    content = [{"type": "text", "text": prompt}]

    if post_img_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"{post_img_url}"},
        })

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like the LinkedIn profile user whose details you are about to analyze. 
        You have an extensive background in LinkedIn engagement, social media, and social marketing, with a specific expertise in aligning comments and content to an individual’s personal and professional style. 
        You excel at understanding a person's tone, interests, and the way they communicate online, especially on LinkedIn.
        
        Your main objective is to generate insightful, relevant comments in response to provided content, using the tone, voice, and style of the profile user. 
        These comments should align with the user’s professional identity and communication style, fostering engagement and authority.
        
        Step-by-step process:
        1. Analyze the LinkedIn profile provided: Carefully examine the user's tone, interests, and speaking style based on their LinkedIn activity. Identify patterns in how they engage with others—whether their tone is formal or informal, motivational or technical, concise or elaborate.
        2. Assess the content to be responded to: Identify the key points in the content you need to respond to. Make sure you understand its context within the broader conversation.
        3. Generate a response: Craft a thoughtful, insightful comment that matches the voice and style of the LinkedIn profile user. Use the following guidelines:
            - Reflect the user’s professional expertise and unique style of communication.
            - Keep the tone either conversational or authoritative, depending on the user’s style.
            - Engage others by making your response relevant to the ongoing conversation.
            - Be concise but impactful—focus on making the first 2-3 lines (~400 characters) compelling to encourage readers to expand and read more.
        4. Ensure relevance: The response should contribute value to the conversation. Draw connections between the content presented and the user's professional background.
        5. Maintain brevity and engagement: Keep the comment under 1250 characters, including spaces and punctuation. Aim to foster further discussion without overwhelming the reader with excessive information.
        6. Incorporate links if relevant: If there are links in the original content or discussion, briefly reference them if they are directly applicable. Use this to add depth to your response.
        
        Be original, creative, and insightful in your comment, always aiming to mirror the LinkedIn profile user’s tone, foster engagement, and drive further conversation.
        
        Take a deep breath and work on this problem step-by-step.
        
        Only respond with your final comment once you are satisfied with its quality, relevance, and alignment with the LinkedIn user’s style.
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


@shared_task.task
@debug_function
def post_comment(user_id: int, post_link, comment_text):
    """Post a comment to the currently opened post in the driver window"""

    driver, wait = get_driver_wait_pair()

    user_email, user_password = get_user_password_pair_by_id(user_id)

    if post_link != driver.current_url:
        # Switch to post url
        driver.get(post_link)

    # Find the comment input area
    comment_box = click_element_wait_retry(driver, wait,
                                           '//div[contains(@class, "comments-comment-texteditor")]//div[@role="textbox"]',
                                           "Finding the Comment Input Area", use_action_chain=True)

    # clear the contents of the comment_box
    comment_box.clear()

    # Simulate typing the comment
    myprint("Typing Comment...")
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

    myprint("Finished Typing Comment!")

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
                                                      "Finding Celebrate Button", element_always_expected=False,
                                                      max_try=1)
            if celebrate_button:
                choices.append(celebrate_button)
            insightful_button = get_element_wait_retry(driver, wait,
                                                       '//button[contains(@aria-label, "Insightful")]',
                                                       "Finding Insightful Button", element_always_expected=False,
                                                       max_try=1)
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
    """See if the current open url we've already posted on"""
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


@shared_task.task
@debug_function
def automate_commenting(user_id: int, loop_for_duration=None, **kwargs):
    global stop_all_thread

    myprint("Starting Automate Commenting Thread...")

    driver, wait = get_driver_wait_pair()

    user_email, user_password = get_user_password_pair_by_id(user_id)

    login_to_linkedin(driver, wait, user_email, user_password)

    my_profile = get_my_profile(driver, wait, user_email, user_password)

    navigate_to_feed(driver, wait)

    start_time = datetime.now()

    # Get 10 posts from the feed
    posts = get_feed_posts(driver, wait, num_posts=10)

    current_tab = driver.current_window_handle
    handles = driver.window_handles

    for post in posts:
        # break if it has been loop_for_duration seconds since the start time
        if loop_for_duration:
            elapsed_time = datetime.now() - start_time
            if elapsed_time.total_seconds() >= loop_for_duration:
                myprint("Loop duration reached. Stopping Automate Commenting thread...")
                break
        # Else do this (loop_for_duration overrides this break)
        elif stop_all_thread.is_set():
            myprint("Stopping Automate Commenting thread...")
            break

        # Switch back to tab
        driver.switch_to.window(current_tab)

        post_link = post['link']
        myprint(f"Post Link: {post_link}")

        # Wait for the new window or tab
        driver.switch_to.new_window('tab')
        wait.until(EC.new_window_is_opened(handles))

        # Generate and post comment
        generate_and_post_comment(driver, wait, post_link, my_profile)

        # Close tab when done
        close_tab(driver)

    # Switch back to tab
    driver.switch_to.window(current_tab)

    driver.quit()


@shared_task.task
@debug_function
def automate_reply_commenting(user_id: int, loop_for_duration=None, **kwargs):
    """"Reply to recent comments"""
    # TODO: Implement this function

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair()

    login_to_linkedin(driver, wait, user_email, user_password)

    start_time = datetime.now()

    while True:

        myprint("Responding to Comments here...")

        if loop_for_duration:
            elapsed_time = datetime.now() - start_time
            if elapsed_time.total_seconds() >= loop_for_duration:
                myprint("Loop duration reached. Stopping Automate Reply Commenting thread...")
                break
        else:
            break

        time.sleep(15)  # Sleep for 15 seconds

    driver.quit()


@shared_task.task
@debug_function
def automate_appreciation_dms(user_id: int, loop_for_duration=None):
    # TODO: Implement this function

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair()

    # After Accepting a Connection Request:

    # After Receiving a Recommendation:

    # After an Interview:

    # For a Successful Collaboration:

    # General Appreciation:
    # "Hi [Name], I really appreciate your insights on [topic]. Your perspective helped me see things differently, and I'm grateful for the opportunity to learn from you."

    login_to_linkedin(driver, wait, user_email, user_password)

    start_time = datetime.now()

    while True:

        myprint("Sending Appreciations here...")

        if loop_for_duration:
            elapsed_time = datetime.now() - start_time
            if elapsed_time.total_seconds() >= loop_for_duration:
                myprint("Loop duration reached. Stopping Automate Appreciations thread...")
                break
        else:
            break

        time.sleep(10)  # Sleep for 10 seconds

    driver.quit()


def generate_and_post_comment(driver, wait, post_link, my_profile: LinkedInProfile) -> bool:
    if post_link != driver.current_url:
        # Switch to post url
        driver.get(post_link)

    # Check to make sure we haven't already commented on this post
    if check_commented(driver, wait):
        myprint("Already commented on this post. Skipping...")
        return False  # Skip posts we've already commented on
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
        return False  # Skip posts without content

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
    comment_text = generate_ai_response(content, my_profile, img_url)

    myprint(f"AI Generated Comment: {comment_text}")
    # Simulate typing the AI-generated comment
    # for char in comment_text:
    #    if char == '\n':
    #        myprint()
    #    else:
    #        myprint(char, end='')
    #    time.sleep(random.uniform(0.05, 0.15))  # Simulate human typing speed

    # Comment out the actual posting of the comment for now
    post_comment.delay(
        kwargs={'user_id': get_user_id(my_profile.email),
                'post_link': post_link,
                'comment_text': comment_text}
    )

    myprint("Comment Posted")

    return True


def test_already_commented(driver, wait):
    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)

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

    profile_data = {
        "full_name": "Bob Barker",
        "title": "Building Builder"
    }
    profile = LinkedInProfile(**profile_data)

    for prompt in prompts:
        comment_text = generate_ai_response(prompt['prompt'], profile, prompt['image_url'])
        myprint(f"User Prompt: {prompt['prompt']}")
        myprint(f"AI Generated Comment: {comment_text}")


@shared_task.task
@debug_function
def automate_profile_viewer_dms(user_id: int, loop_for_duration=None, **kwargs):
    global stop_all_thread

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair()

    # Wait until there are 10 minutes or less on the timer
    while True:
        if loop_for_duration:
            break  # This overrides the remaining time and threading setup

        remaining_minutes = get_time_remaining_minutes()

        # Else do this (loop_for_duration overrides this break)
        if remaining_minutes <= 10:
            break
        # Sleep for the remaining time needed to be less than 10 minutes
        remaining_seconds = get_time_remaining_seconds()
        sleep_time = max(remaining_seconds - (10 * 60), 2)
        myprint(f"Waiting for {sleep_time} seconds to start Profile Viewer DMs")
        time.sleep(sleep_time)

    myprint(f"Starting Profile Viewer DMs")

    login_to_linkedin(driver, wait, user_email, user_password)

    my_profile = get_my_profile(driver, wait, user_email, user_password)

    # Navigate to profile view page
    driver.get("https://www.linkedin.com/analytics/profile-views/")

    start_time = datetime.now()

    viewed_on_xpath = './/div[contains(@class,"artdeco-entity-lockup__caption ember-view")]'

    while True:  # Keep looping until we find a viewed on date out of range
        # Get Each Viewer within the last day (or time of dm run via database log)
        viewer_elements = get_elements_as_list_wait_stale(wait,
                                                          '//ul[@aria-label="List of Entities"]//a[contains(@href,"linkedin.com/in") and not(contains(@aria-label,"Update"))]',
                                                          "Finding Profile Viewers")

        # myprint(f"Viewers count: {len(viewer_elements)}")

        if len(viewer_elements) > 0:
            # myprint("Here 1")
            # Get the last viewer
            last_viewer = viewer_elements[-1]
            # myprint("Here 2")
            # Extract the viewer's name
            name_element = last_viewer.find_element(By.XPATH,
                                                    './/div[contains(@class,"artdeco-entity-lockup__title")]/span/span[1]')
            # myprint("Here 3")
            if name_element:
                last_viewer_name = getText(name_element)
                # myprint(f"Last Viewer Name: {last_viewer_name}")
            else:
                last_viewer_name = random.choice(["John", "Jane"]) + " Doe"
                myprint("Could not find name of last viewer")

            last_viewed_on_element = last_viewer.find_element(By.XPATH, viewed_on_xpath)
            if last_viewed_on_element:
                last_viewed_on = getText(last_viewed_on_element).strip()
                # myprint(f"Last Viewed on: {last_viewed_on}")

                # Convert viewed on to date
                last_viewed_date = convert_viewed_on_to_date(last_viewed_on)
                # myprint(f"Last Viewed on Date: {last_viewed_date}")

                # if the last viewed on date is Greater than 24 hours break the while loop
                if (datetime.now() - last_viewed_date).days > 1:  # TODO: Change this to 1
                    # myprint("Last viewed on date is more than 24 hours ago")
                    break  # Break the while loop
            else:
                myprint(f"Could not find viewed on element for {last_viewer_name}")

            # Scroll down to get more elements
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        else:
            break  # Break the while loop

    # myprint(f"Viewers: {str(viewer_elements)}")
    myprint(f"Final Viewers count: {len(viewer_elements)}")

    try:
        # Filter the viewers by date within the last day
        viewer_elements = [e for e in viewer_elements if (datetime.now() - convert_viewed_on_to_date(
            getText(e.find_element(By.XPATH, viewed_on_xpath)))).days <= 1]
    except Exception as e:
        myprint(f"Error filtering viewers by date: {e}")

    myprint(f"Filtered Viewers count: {len(viewer_elements)}")

    current_tab = driver.current_window_handle
    handles = driver.window_handles

    # Get all the viewer names and urls into list so that elements dont go stale
    viewer_names = [
        getText(e.find_element(By.XPATH, './/div[contains(@class,"artdeco-entity-lockup__title")]/span/span[1]')) for e
        in viewer_elements]
    viewer_urls = [e.get_attribute('href') for e in viewer_elements]
    # Merge them into a dictionary to iterate over
    viewer_data = dict(zip(viewer_names, viewer_urls))

    # Get the viewed data from each element and filter by a day ago or specific date
    for viewer_name, viewer_url in viewer_data.items():

        if loop_for_duration:
            elapsed_time = datetime.now() - start_time
            if elapsed_time.total_seconds() >= loop_for_duration:
                myprint("Loop duration reached. Stopping Automate Commenting thread...")
                break
        elif stop_all_thread.is_set():
            myprint("Stopping Automate Profile Viewers DMs thread...")
            break

        # Switch back to tab
        driver.switch_to.window(current_tab)

        myprint(f"Viewer Name: {viewer_name}")
        myprint(f"Viewer URL: {viewer_url}")

        # Wait for the new window or tab
        driver.switch_to.new_window('tab')
        wait.until(EC.new_window_is_opened(handles))

        # Switch to viewer_url
        driver.get(viewer_url)

        # Send a DM to the viewer
        send_dm(driver, wait, my_profile, viewer_url, viewer_name)

        # Close tab when done
        close_tab(driver)

    driver.quit()


def get_ai_description_of_profile(linked_in_profile: LinkedInProfile):
    # Use json to output to string
    linked_in_profile_json = linked_in_profile.model_dump_json()
    prompt = f"""Please tell me what appears to be this person's personal interest based on their current job, skills, and recent activities.
             A short summary of your analysis of around 500 characters is all that is needed.
             Person: {linked_in_profile_json}"""

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional career coach and personality analyst with over 20 years of experience in understanding human behavior through social media profiles, particularly LinkedIn. Your expertise is in evaluating profiles to determine personal and professional character traits based on the content of their work experience, endorsements, skills, recommendations, posts, and interactions.

        Your objective is to thoroughly analyze LinkedIn profile data to extract insights about the individual’s character traits, such as leadership, teamwork, creativity, reliability, adaptability, communication skills, and more. Use subtle cues from the person's descriptions of job roles, their endorsements from others, the language used in their recommendations, and their professional interactions to form a comprehensive assessment. Ensure to identify both overt and nuanced traits, and support each finding with examples from the profile content. Pay special attention to the consistency between the skills endorsed by others and the responsibilities listed by the individual.
        
        Follow these steps:
        1. Start by identifying the general tone and language used in the profile, which may indicate personality traits like enthusiasm, confidence, or humility.
        2. Examine the person’s job titles and descriptions to identify traits such as leadership, initiative, and problem-solving abilities.
        3. Analyze the endorsements and recommendations, looking for patterns in how others describe the individual. Highlight any common traits mentioned (e.g., dependability, collaboration).
        4. Evaluate posts or comments for signs of professional engagement, thought leadership, or community involvement.
        5. Conclude with a comprehensive summary that combines these insights into a clear picture of the individual’s character traits, citing specific parts of the profile to support your findings.
        
        Take a deep breath and work on this problem step-by-step."""
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


def summarize_recent_activity(recent_activity_profile: LinkedInProfile, main_profile: LinkedInProfile):
    recent_activity_profile_sting = ''.join([f"{i + 1}. {activity.text} - [{activity.link}]\n" for i, activity in
                                             enumerate(recent_activity_profile.recent_activities)])

    # Clone the main profile and remove recent activities to reduce confusion form AI
    main_profile = main_profile.clone()
    main_profile.recent_activities = []

    main_profile_json = main_profile.model_dump_json()
    prompt = f"""We are analyzing the interests of one LinkedIn user (main_profile) and want to help them craft a personalized response to another LinkedIn user (second_profile) based on the second user's recent activities. 
    Analyze the main_profile’s interests and select the most relevant activity from second_profile’s list of recent activities. 
    Then, create a response as if it’s from main_profile to second_profile, mentioning the most relevant recent activity and providing a professional comment.

    Main Profile (User 1):
    {main_profile_json}
    
    Second Profile (User 2):
    Name: {recent_activity_profile.full_name}
    Recent Activities:
    {recent_activity_profile_sting}
    
    Create a response from {main_profile.full_name} to {recent_activity_profile.full_name} that references the most relevant recent activity from {recent_activity_profile.full_name}’s list.

    A short final response starting with 'I saw your recent post about' is all that is needed.
    """

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional career coach and personality analyst with over 20 years of experience in analyzing LinkedIn profiles and assessing professional interests. Your expertise lies in evaluating profiles to understand character traits and key interests, as well as identifying relevant connections between users based on their professional activities and interactions.

        You will be provided with details of a LinkedIn profile (main_profile) and a list of recent activities from another profile (recent_activities). Your objective is twofold:
        
        1. Analyze the main_profile to understand their core professional interests, focus areas, and potential motivations.
        2. Review the recent_activities and select the one that is most relevant to the interests of the main_profile. This may include shared professional fields, emerging trends that match their focus, or topics that directly address the needs of the main_profile.
        
        Once you identify the most relevant recent activity, compose a professional response. The response should acknowledge the activity and link it to the main_profile’s interests using a thoughtful and engaging tone. Use the following structure:
        
        - Begin by referencing the recent activity in a polite and personalized manner.
        - Summarize the most relevant recent activity.
        - Include the link for reference.
        - Provide a brief, positive analysis using a professional adjective to describe the relevance of the activity to the main_profile.
        
        Follow these steps:
        1. Analyze the provided main_profile data to understand their professional interests and areas of focus.
        2. Review the list of recent_activities, including the text and links, and identify the one that most closely aligns with the main_profile’s interests.
        3. Craft a response using the format: 'I also saw your recent post about [most relevant activity text summary] [insert_link_recent_activity] and found it [insert_professional_adjective]'. Ensure the adjective aligns with the nature of the content (e.g., insightful, innovative, thought-provoking, etc.).
        
        Take a deep breath and work on this problem step-by-step."""
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


def get_ai_message_refinement(original_message: str, character_limit: int = 300):
    character_limit_string = f"\nThe refined message needs to be less than or equal to {character_limit} characters including white spaces.\n\n " if character_limit > 0 else ""

    prompt = f"""Please review and refine the following message. {character_limit_string} Message: {original_message}
            """

    # myprint(f"Prompt: {prompt}")

    content = [{"type": "text", "text": prompt}]

    # System prompt to be included in every request
    system_prompt = {
        "role": "system",
        "content": f"""Act like a professional editor with expertise in communication for business professionals, particularly on platforms like LinkedIn. 
            You have helped clients refine and streamline their messaging for more than 15 years, ensuring clarity, professionalism, and engagement.
    
            Your task is to review a provided message. The goal is to ensure the message makes sense, reads smoothly, and presents key information in a clear, concise, and professional manner. Additionally, modify any titles, phrases, or sections that seem overly long, awkward, or redundant. 
            Your revisions should maintain the original intent while improving readability and impact.
            
            The review process includes:
            1. Check for clarity and coherence: Ensure the message has a logical flow and that each sentence connects smoothly to the next. Eliminate or revise any confusing or ambiguous phrases.
            2. Refine long titles and sections: Shorten overly detailed sections, such as professional titles, while preserving their key points. Ensure these parts are clear but not excessive.
            3. Improve engagement: The message should feel personalized and engaging. Identify opportunities to make the message more concise and approachable, particularly in the introduction and closing.
            4. Polish for professionalism: Ensure a professional tone throughout, appropriate for business communication.
            
            A final direct refined response without a subject line is all that is needed. 
            
            Take a deep breath and work on this problem step-by-step.
            """
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


def send_dm(driver, wait, my_profile: LinkedInProfile, viewer_url, viewer_name):
    myprint(f"Sending DM from: {my_profile.full_name} to: {viewer_name}")

    if viewer_url != driver.current_url:
        # Switch to viewer_url
        driver.get(viewer_url)

    profile_data = get_linkedin_profile_from_url(driver, wait, viewer_url)
    if profile_data:
        profile = LinkedInProfile(**profile_data)
        # message = profile.generate_personalized_message()
        # myprint(message)

        if profile.is_1st_connection:
            myprint("We Are 1st Connections")
            # engage with their content (
            green_activities = profile.recent_activities

            myprint(f"Green Activities Count: {len(green_activities)}")

            # Filter activities by posted date less than a week ago
            green_activities = [activity for activity in green_activities if
                                (datetime.now() - activity.posted).days <= 7]

            myprint(f"Green Activities Filtered (1 week) Count: {len(green_activities)}")

            # DONT: Shuffle the activities (they are already in order of latest to oldest)
            # random.shuffle(green_activities)
            able_to_comment = False

            # Filter list to activities I haven't commented on
            for activity in green_activities:
                # Navigate to Link
                myprint(f"Navigating To: {activity.link}")
                driver.get(str(activity.link))
                commented = check_commented(driver, wait)
                if not commented:
                    # Leave comment on that activity
                    able_to_comment = generate_and_post_comment(driver, wait, str(activity.link), my_profile)
                    if able_to_comment:
                        break  # Only comment/interact with one

            if not able_to_comment:
                myprint("No activities, unable to or already left comment")

                # TODO: Send DM - offer something of value—whether it's insights, resources, or potential collaboration opportunities.
                # TODO: Generate something of value to offer
                message = "Hi, I noticed we're connected on LinkedIn and wanted to reach out. I'm currently working on a project that I think you might find interesting. Would you be open to a quick chat to discuss it further?"

                # Send actual DM
                send_private_dm.delay(
                    kwargs={'user_id': get_user_id(my_profile.email),
                            'profile_url': profile.profile_url,
                            'message': message}
                )
        else:
            # myprint(f"We Are {profile.connection} Connections")
            # If not connected send them a connection request
            # Mention something specific about their profile or company to show genuine interest and that you've done your research
            recent_activity_summary = summarize_recent_activity(profile, my_profile)
            response = profile.generate_personalized_message(recent_activity_message=recent_activity_summary,
                                                             from_name=my_profile.full_name)
            myprint(f"Original Response: {response}")
            refined_response = get_ai_message_refinement(response)
            myprint(f"Refined Response: {refined_response}")

            # Send connection request with this message
            invite_to_connect.delay(
                kwargs={'user_id': get_user_id(my_profile.email),
                        'profile_url': profile.profile_url,
                        'message': refined_response}
            )
    else:
        myprint(f"Failed to get profile data for {viewer_name}")


@shared_task.task
@debug_function
def send_private_dm(user_id: int, profile_url: str, message: str):
    """ Send dm message to a profile. Must be a 1st connection"""

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair()

    login_to_linkedin(driver, wait, user_email, user_password)

    # Open the profile URL
    driver.get(profile_url)

    # TODO: Add code to post the dm message
    myprint("Sending DM: " + message)

    dm_sent = False

    return dm_sent


@shared_task.task
@debug_function
def invite_to_connect(user_id: int, profile_url: str, message: str = None):
    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair()

    login_to_linkedin(driver, wait, user_email, user_password)

    if profile_url != driver.current_url:
        # Open the profile URL
        driver.get(profile_url)

    myprint(f"Inviting to connect: {profile_url}")

    # Locate the connect button
    try:
        click_element_wait_retry(driver, wait, '//main//button[contains(@aria-label, "Invite ")]',
                                 "Finding Connect Button", max_try=1, use_action_chain=True)

        myprint("Found Connect Button and clicked it")


    except Exception as ce:
        # If it doesn't exist click the more than find the connect button there
        try:
            # Click the last more button
            click_element_wait_retry(driver, wait,
                                     '//main//button[contains(@aria-label,"More actions")]',
                                     "Finding More Button", max_try=1, use_action_chain=True)

            # driver.find_elements(By.XPATH, '//main//button[contains(@aria-label,"More actions")]')[-1].click()

            myprint("Found More Button and clicked it")

            # Click the last connect button
            click_element_wait_retry(driver, wait, '//main//div[contains(@aria-label,"connect")]',
                                     "Finding Connect Button", max_try=21, use_action_chain=True)

            # driver.find_elements(By.XPATH, '//div[contains(@aria-label,"connect")]')[-1].click()

            myprint("Found Connect Button and clicked it")
        except Exception as e:
            myprint(f"Failed to find more button or connect button: Error: {str(e)}")
            return False

    # If connection_message exist click the With note button
    if message:
        try:
            click_element_wait_retry(driver, wait, '//button[contains(@aria-label,"Add a note")]',
                                     "Finding Add a Note Button", use_action_chain=True)

            myprint("Found Add a Note Button and clicked it")

            # Find the message box
            message_box = click_element_wait_retry(driver, wait, '//textarea[@id="custom-message"]',
                                                   "Finding Message Box", use_action_chain=True)

            myprint("Found Message and clicked it")

            # Clear the message box
            message_box.clear()

            myprint("Cleared the message box")

            # Message must be less than 300 characters. Try 3 times to get a revised message under that limit
            for i in range(3):
                # Check Message character length
                if len(message) > 300:
                    message = get_ai_message_refinement(message, 300)
                else:
                    break

            # Put the text in the message box
            message_box.send_keys(message)

            myprint("Added message to message box")

            # Sleep so send button can become active
            time.sleep(2)

            myprint("Waited for send button to activate")

            # Click the send button
            click_element_wait_retry(driver, wait,
                                     '//button[contains(@aria-label,"Send invitation")]',
                                     "Finding Send Connection Button", use_action_chain=True)

            myprint("Found Send Connection Button and clicked it")
        except Exception as e:
            myprint(f"Failed to Add a note. Error: {str(e)}")
            return False
    else:
        # Else click send connection
        try:
            click_element_wait_retry(driver, wait,
                                     '//button[contains(@aria-label,"Send without a note")]',
                                     "Finding Send Without Note Button", use_action_chain=True)

            myprint("Found Send Without a Note Button and clicked it")
        except Exception as e:
            myprint(f"Failed to find send without a note connection button. Error: {str(e)}")
            return False


def start_process():
    global time_remaining_seconds

    # Set Timer for 3 minutes
    time_remaining_seconds = 60 * 15

    drivers_needed = 3

    # build as many drivers as there are threads, so each thread gets own driver
    # drivers_with_waits = [get_driver_wait_pair() for _ in range(drivers_needed)]
    # all_drivers = [driver for driver, _ in drivers_with_waits]

    #def signal_handler(sig, frame):

    # Get list of all drivers from drivers_with_waits

    # final_method(all_drivers)

    # Register the signal handler for SIGINT
    #signal.signal(signal.SIGINT, signal_handler)

    # Register the final_method to be called on exit
    # atexit.register(final_method, all_drivers)

    # Create the countdown timer in a separate thread
    with ThreadPoolExecutor(max_workers=max(4, drivers_needed)) as executor:
        executor.submit(countdown_timer, time_remaining_seconds)
        # Get a driver/wait set
        # driver, wait = drivers_with_waits.pop(0)
        executor.submit(automate_commenting, kwargs={'user_id': get_user_id(LI_USER)})
        # Get another driver/wait set
        # driver2, wait2 = drivers_with_waits.pop(0)
        executor.submit(automate_profile_viewer_dms,
                        kwargs={'user_id': get_user_id(
                            LI_USER)})  # TODO: Make this wait till there 10 min or less left on timer

    myprint("Time is up. Closing the browser")

    # final_method(all_drivers)


def final_method(drivers: List[WebDriver]):
    global stop_all_thread
    stop_all_thread.set()  # Set the flag to stop other threads
    for driver in drivers: driver.quit()  # Quit all the drivers
    myprint("All drivers stopped. Program has exited.")
    sys.exit(0)


def test_dates():
    myprint(f"Testing dates | 1d ago: {convert_viewed_on_to_date('Viewed 1d ago')}")
    myprint(f"Testing dates | 5d ago: {convert_viewed_on_to_date('viewed 5d ago')}")
    myprint(f"Testing dates | 1w ago: {convert_viewed_on_to_date('Viewed 1w ago')}")
    myprint(f"Testing dates | 1mo ago: {convert_viewed_on_to_date('Viewed 1mo ago')}")


def test_linked_in_profile():
    # Example usage with mutual connections being a mix of strings and LinkedInProfile objects
    profile_data = {
        "full_name": "Jane Doe",
        "company_name": "Tech Innovators",
        "industry": "Technology",
        "profile_url": "https://www.linkedin.com/in/janedoe",
        "recent_activity": ["AI in marketing"],
        "mutual_connections": [
            "John Smith",
            LinkedInProfile(full_name="Emily Davis", company_name="DataCorp")
        ],
        "endorsements": ["Marketing Strategy", "Digital Advertising"],
        "education": "Harvard Business School",
        "certifications": ["Google Analytics Certified"],
        "awards": ["Top 50 Women in Tech 2022"],
        "groups": ["Women in Tech", "AI Enthusiasts"],
        "interests": ["Marketing Analytics", "AI Innovations"]
    }

    profile = LinkedInProfile(**profile_data)

    # Generate a personalized message
    message = profile.generate_personalized_message()
    myprint(message)

    # Print a summary of the profile
    myprint(profile.profile_summary)


def test_get_linkedin_profile_from_url():
    driver = create_driver()
    wait = get_driver_wait(driver)

    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)

    profile_url = "https://www.linkedin.com/in/eric-partaker-5560b92"
    profile_data = get_linkedin_profile_from_url(driver, wait, profile_url)

    if profile_data:
        myprint("Profile data:")
        myprint(json.dumps(profile_data, indent=4))
        profile = LinkedInProfile(**profile_data)
        myprint(profile.profile_summary)
    else:
        myprint("Failed to get profile data")

    driver.quit()


def test_send_dm():
    driver = create_driver()
    wait = get_driver_wait(driver)

    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)

    my_profile = get_my_profile(driver, wait, LI_USER, LI_PASSWORD)

    # 2nd Connection
    profile_url = "https://www.linkedin.com/in/eric-partaker-5560b92"
    name = "Eric Partaker"
    send_dm(driver, wait, my_profile, profile_url, name)

    # 1st Connection
    profile_url_2 = "https://www.linkedin.com/in/byron-mcclure-0a20a837/"
    name_2 = "Bryon McClure"
    send_dm(driver, wait, my_profile, profile_url_2, name_2)

    # driver.quit()


def test_describe_profile():
    driver = create_driver()
    wait = get_driver_wait(driver)

    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)

    profile_url = "https://www.linkedin.com/in/christopherqueen"

    profile_data = get_linkedin_profile_from_url(driver, wait, profile_url)

    if profile_data:
        profile = LinkedInProfile(**profile_data)
        description = get_ai_description_of_profile(profile)
        myprint(description)

    else:
        myprint("Failed to get profile data")

    driver.quit()


def test_describe_summarize_interesting_activity():
    driver = create_driver()
    wait = get_driver_wait(driver)

    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)

    profile_url = "https://www.linkedin.com/in/christopherqueen"

    profile_data = get_linkedin_profile_from_url(driver, wait, profile_url)

    if profile_data:
        main_profile = LinkedInProfile(**profile_data)

        profile_2_url = "https://www.linkedin.com/in/eric-partaker-5560b92"
        profile_2_data = get_linkedin_profile_from_url(driver, wait, profile_2_url)
        if profile_2_data:
            second_profile = LinkedInProfile(**profile_2_data)
            description = summarize_recent_activity(second_profile, main_profile)
            myprint(description)
        else:
            myprint("Failed to get second profile data")

    else:
        myprint("Failed to get main profile data")

    driver.quit()


def test_post_comment():
    driver = create_driver()
    wait = get_driver_wait(driver)

    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)

    # Navigate to post
    driver.get(
        "https://www.linkedin.com/posts/christopherqueen_accounting-ai-automation-activity-7250701723214708737-0Cmg?utm_source=share&utm_medium=member_desktop")
    # driver.get("https://www.linkedin.com/posts/agacgfm_take-advantage-of-your-membership-and-join-activity-7249146500310528000-gUkv?utm_source=share&utm_medium=member_desktop")

    comment = """We're currently running a test to see how much traction we can get on this post. It's an experiment to measure engagement and visibility, so every interaction counts! Whether you're scrolling by or taking a moment to read through, feel free to drop a comment, like, or even share it if you find it interesting. The goal here is to explore how LinkedIn’s algorithms respond to posts like this, and whether we can reach a broader audience by simply encouraging more activity.

    Also, we’re curious to see if there's a notable difference in reach based on engagement in the early stages of a post's lifecycle, so if you're seeing this, a quick interaction would be greatly appreciated!
    
    In the meantime, we’ll keep monitoring the performance metrics and adjust our approach based on what we learn. If you have any tips or insights on how to boost engagement, we’d love to hear them! Thanks for being part of our little experiment—let's see where this goes!"""

    post_comment(driver, wait, comment)


def test_invite_to_connect():
    driver = create_driver()
    wait = get_driver_wait(driver)

    login_to_linkedin(driver, wait, LI_USER, LI_PASSWORD)

    invite_list = ["https://www.linkedin.com/in/eric-partaker-5560b92/",
                   "https://www.linkedin.com/in/bhavika-hariyani-444178222/"]

    message = """I came across your profile and was impressed by your experience as The CEO Coach and your recognition as CEO of the Year in 2019. Your work at The CEO Accelerator truly stands out. I also read your recent post, "20 Harsh Truths You Need to Accept to Take Your Career to the Next Level" [https://www.linkedin.com/feed/update/urn:li:activity:7253734954646339584], and found it incredibly insightful. Your thoughts on resilience, leadership, and continuous improvement align well with my commitment to empowering enterprises with AI solutions. 

    I would love to connect and explore potential collaboration opportunities.
    
    Best regards,  
    Christopher Queen"""

    myprint(f"Original Message: {message}")

    # Refine the message
    message = get_ai_message_refinement(message)

    myprint(f"Refined Message: {message}")

    for invite in invite_list:
        invite_to_connect(driver, wait, invite, message)
        # Clear message after first invite
        message = None


if __name__ == "__main__":
    # Create the driver
    # driver = create_driver()
    # wait = get_driver_wait(driver)
    # test_already_commented(driver, wait)

    # test_ai_responses()
    # generate_ai_response_test
    # test_dates()
    # test_linked_in_profile()
    # test_get_linkedin_profile_from_url()
    # test_describe_profile()
    # test_describe_summarize_interesting_activity()
    # test_post_comment()
    # test_send_dm()
    # test_invite_to_connect()
    # exit(0)

    start_process()
    myprint("Process finished")
