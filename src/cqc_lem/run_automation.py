import inspect
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlparse

from celery_once import QueueOnce
from dotenv import load_dotenv
from selenium.common import NoSuchElementException, JavascriptException
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from cqc_lem.my_celery import app as shared_task
from cqc_lem.utilities.ai.ai_helper import generate_ai_response, get_ai_message_refinement, summarize_recent_activity
from cqc_lem.utilities.date import convert_viewed_on_to_date
from cqc_lem.utilities.db import get_user_password_pair_by_id, get_user_id, insert_new_log, LogActionType, \
    LogResultType, has_user_commented_on_post_url, get_post_url_from_log_for_user, get_post_message_from_log_for_user, \
    has_engaged_url_with_x_days, get_post_content, get_post_video_url, update_db_post_status, PostStatus
from cqc_lem.utilities.env_constants import LI_USER
from cqc_lem.utilities.linkedin.helper import login_to_linkedin, get_my_profile, get_linkedin_profile_from_url
from cqc_lem.utilities.linkedin.poster import share_on_linkedin
from cqc_lem.utilities.linkedin.profile import LinkedInProfile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import click_element_wait_retry, \
    get_element_wait_retry, get_elements_as_list_wait_stale, getText, close_tab, get_driver_wait_pair, quit_gracefully, \
    wait_for_ajax

# Load .env file
load_dotenv()

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
        wait_for_ajax(driver)

    try:
        # Find and click the "Sort by" dropdown
        click_element_wait_retry(driver, wait, '//button/hr',
                                 "Clicking Sort By Dropdown", use_action_chain=True)

        # time.sleep(1)
        wait_for_ajax(driver)

        # Select "Recent" from the dropdown
        click_element_wait_retry(driver, wait, '//div[contains(@class,"artdeco-dropdown")]/ul/li[2]',
                                 "Selecting Recent Option", max_retry=0, use_action_chain=True)

        wait_for_ajax(driver)
        time.sleep(3)  # Wait for the page to refresh with recent posts

        myprint("Feed Sorted By Recent Items First")

    except Exception as e:
        myprint("Error During Feed Sort |  Exception: " + str(e))

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


def emoji_to_ue_string(emoji):
    """Converts an emoji to its equivalent escaped sequence."""
    return emoji.encode('unicode_escape').decode('ascii')


def clear_text_from_element(element: WebElement):
    # Select All
    element.send_keys(Keys.CONTROL + "a")
    # Delete what is selected
    element.send_keys(Keys.DELETE)


def simulate_typing(driver: WebDriver, editable_element: WebElement, text):
    # Simulate typing the comment
    myprint("Typing Text...")
    type_speed_reducer = .5

    # Focus on Element
    actions = ActionChains(driver).move_to_element(editable_element).click()

    # Keep Track of characters to replace
    replacement_dict = {}

    for char in text:
        try:
            if ord(char) > 0xFFFF:
                # Generate a unique key for the character
                key = f"|_{len(replacement_dict) + 1}_|"
                # Record the character to replace later
                replacement_dict[key] = char

                # Insert the placeholder to replace later with JavaScript
                actions.send_keys(key)

                # Convert Emoji - THIS DOES NOT WORK
                # actions.send_keys(emoji_to_ue_string(char))

            else:
                actions.send_keys(char)
                # editable_element.send_keys(char)
        except Exception as e:
            myprint("Error while sending char(" + char + "): " + str(e))

        type_pause = random.uniform(0.05 * type_speed_reducer, 0.15 * type_speed_reducer)
        # time.sleep(type_pause)  # Simulate human typing speed
        actions.pause(type_pause)

    actions.perform()

    script_pre = "arguments[0].value = arguments[0].value.replace(arguments[1],arguments[2]);"
    if editable_element.tag_name == 'p':
        script_pre = script_pre.replace(".value", ".innerText")

    for key, char in replacement_dict.items():
        try:
            # Use JavaScript to set the value for characters outside the BMP
            driver.execute_script(script_pre, editable_element, key, char)
        except JavascriptException as e:
            myprint("Error while replacing char(" + key + "): " + str(e))
            # Get the current test
            current_text = getText(editable_element)
            # Remove the key from the text
            current_text = current_text.replace(key, '')
            # Clear all the text
            clear_text_from_element(editable_element)
            # Enter the new text without the char
            actions.send_keys(current_text).perform()

    if len(replacement_dict) > 0:
        # Send an additional space character (so changed register)
        actions.send_keys(Keys.SPACE).perform()

    myprint("Finished Typing!")


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, 'keys': ['user_id', 'post_link']},
                  reject_on_worker_lost=True, rate_limit='4/m')
def comment_on_post(self, user_id: int, post_link: str, comment_text: str):
    """Post a comment to the given post link"""

    # Check the database logs to make sure user hasn't already commented on this post
    if has_user_commented_on_post_url(user_id, post_link):
        myprint("User has already commented on this post. Skipping...")
        return "User has already commented on this post. Skipping..."

    driver, wait = get_driver_wait_pair(session_name='Post Comment')

    user_email, user_password = get_user_password_pair_by_id(user_id)

    login_to_linkedin(driver, wait, user_email, user_password)

    # Create an instance of ActionChains
    actions = ActionChains(driver)

    if post_link != driver.current_url:
        # Switch to post url
        driver.get(post_link)

    # Find the comment input area
    comment_box = click_element_wait_retry(driver, wait,
                                           '//div[contains(@class, "comments-comment-texteditor")]//div[@role="textbox"]',
                                           "Finding the Comment Input Area", use_action_chain=True)

    # Move viewport to the comment_box
    actions.scroll_to_element(comment_box).perform()

    # clear the contents of the comment_box
    comment_box.clear()

    # Simulate typing the comment
    simulate_typing(driver, comment_box, comment_text)

    # Sleep so post button shows up
    time.sleep(2)

    method_result = ''

    try:
        # Find and click the post button
        click_element_wait_retry(driver, wait, '//button[contains(@class, "comments-comment-box__submit-button--cr")]',
                                 "Clicking Post Button", max_retry=1, use_action_chain=True)

        myprint(f"Added Comment via Post Button")
        method_result = f"Added Comment via Post Button"

        # Update database with record of comment to this post
        insert_new_log(user_id=user_id, action_type=LogActionType.COMMENT, result=LogResultType.SUCCESS,
                       post_url=post_link, message=comment_text)

    except NoSuchElementException:
        # If the post button is not found, send a return key to post the comment
        # comment_box.send_keys('\n')
        comment_box.send_keys(Keys.ENTER)
        # Update database with record of comment to this post
        insert_new_log(user_id=user_id, action_type=LogActionType.COMMENT, result=LogResultType.FAILURE,
                       post_url=post_link, message=comment_text)
        myprint(f"Added Comment via return key. This might not have worked")
        method_result = f"Added Comment via return key. This might not have worked"

    try:

        # Get the main like button
        main_like_button = get_element_wait_retry(driver, wait,
                                                  '//button[contains(@aria-label, "Like") and contains(@class,"artdeco-button")]',
                                                  "Finding Main Like Button")

        button_label_options = ['Like', 'Celebrate', 'Insightful', 'Support',
                                # 'Love', 'Funny' # TODO: Not sure if these are universal for all post
                                ]

        # TODO: Use AI to get a preferences
        button_to_click_key = random.choice(button_label_options)

        max_retries = 3
        for attempt in range(max_retries):

            # Wait for new elements to appear (adjust time as needed)
            time.sleep(5)  # This is needed for it to become visible
            try:

                choice_dict = {}

                # For each key in the button_path_dict, get the element and add it to the choices list
                for button_label in button_label_options:
                    button = get_element_wait_retry(driver, wait,
                                                    f"//span[contains(@class,'menu')]//button[contains(@aria-label, '{button_label}')]",
                                                    f"Finding {button_label} Button",
                                                    element_always_expected=False, max_try=1)
                    if button:
                        choice_dict[button_label] = button

                # Get the choice dict keys as list
                choices = list(choice_dict.keys())

                # Randomly chose one of the available button options
                button_to_click_key = random.choice(choices)
                myprint(f"Clicking {button_to_click_key} Post Reaction")
                button_to_click = choice_dict[button_to_click_key]
                # Move to that button and click it
                # Hover over the main like button
                actions.scroll_to_element(main_like_button).move_to_element(main_like_button).move_to_element(
                    button_to_click).click().perform()
                wait_for_ajax(driver)
                time.sleep(2)
                myprint(f"Added Post Reaction")
                method_result += f" | Added Post Reaction"
                break  # Exit loop if click is successful
            except Exception as e:
                if attempt < max_retries - 1:
                    myprint(f"Removing {button_to_click_key} from choice options since it failed")
                    button_label_options.remove(button_to_click_key)
                    time.sleep(1)  # Wait a bit before retrying
                else:
                    myprint(f"Failed to click {button_to_click_key} Post Reaction: {e}")
                    method_result += f" | Added Post Reaction | Error: {e}"
    except Exception as e:
        myprint(f"Error while clicking post reaction: {e}")
        method_result += f"Could not add post reaction | Error: {e}"

    quit_gracefully(driver)  # Close the driver

    return method_result


def check_commented(driver, wait, user_id: int = None, post_url: str = None):
    """See if the current open url we've already posted on"""
    already_commented = False

    if post_url and post_url != driver.current_url:
        # Switch to post url
        driver.get(post_url)

    # Check against Database (in logs table)
    if user_id and post_url:
        already_commented = has_user_commented_on_post_url(user_id, post_url)

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


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True,'unlock_before_run': True, 'keys': ['user_id']})
def automate_commenting(self, user_id: int, loop_for_duration: int = None, future_forward: int = 60):
    global stop_all_thread

    myprint("Starting Automate Commenting Thread...")

    driver, wait, user_email, my_profile = get_current_profile(user_id=user_id, session_name="Automate Commenting")

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

    # Re-schedule the task in the queue for the future
    if loop_for_duration:
        elapsed_time = datetime.now() - start_time
        new_loop_for_duration = round(loop_for_duration - elapsed_time.total_seconds() - future_forward)
        frame = inspect.currentframe()
        current_function_name = frame.f_code.co_name
        args, _, _, values = inspect.getargvalues(frame)
        kwargs = {arg: values[arg] for arg in args}
        # myprint(f"{current_function_name} parameters: {kwargs}")

        if new_loop_for_duration < 0:
            myprint(f"Loop duration reached. Stopping {current_function_name} task...")
        else:
            # Change the value of the loop_for_duration parameter
            kwargs['loop_for_duration'] = new_loop_for_duration
            # Add our function call back to the task queue
            myprint(f"Adding {current_function_name} back to queue for {future_forward} seconds in the future...")
            # Remove 'self' from kwargs if it exists
            if 'self' in kwargs:
                del kwargs['self']
            # Call self again in the future
            globals()[current_function_name].apply_async(kwargs=kwargs, countdown=future_forward)

    quit_gracefully(driver)


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, 'unlock_before_run': True, 'keys': ['user_id', 'post_id']})
def automate_reply_commenting(self, user_id: int, post_id: int, loop_for_duration: int = 60, future_forward=60):
    """Reply to recent comments left on the post recently posted"""

    driver, wait, user_email, my_profile = get_current_profile(user_id=user_id, session_name="Reply to Comments")

    start_time = datetime.now()

    myprint(f"Replying to Comments of Post ID:{post_id} ...")

    # Use the user id and the post id to get the post_url from the database
    post_url = get_post_url_from_log_for_user(user_id, post_id)

    # Get the message content of the post
    post_message = get_post_message_from_log_for_user(user_id, post_id)

    if post_url:
        # Navigate to the Post
        if driver.current_url != post_url:
            driver.get(post_url)

        # If load more comments button exists click it until its gone
        while True:
            load_more_comments_button = click_element_wait_retry(driver, wait,
                                                                 '//button[contains(@class,"load-more-comments")]',
                                                                 "Finding Load More Comments Button",
                                                                 use_action_chain=True,
                                                                 max_retry=0,
                                                                 element_always_expected=False)
            if load_more_comments_button:
                myprint("Loading More Comments....")
                time.sleep(2)
            else:
                break

        try:

            # Get all the comments
            comments = get_elements_as_list_wait_stale(wait,
                                                       "//div[contains(@class,'comments-comment-list__container')]/article[contains(@class,'comments-comment-entity')]",
                                                       "Finding Comments",
                                                       max_retry=0,
                                                       )
        except Exception as e:
            myprint(f"Error while finding comments: {e}")
            comments = []

        # Print how many comments found
        myprint(f"Comments Found: {len(comments)}")

        # Get the unique_url_name after "in/" and before / or end or profile url
        path = urlparse(str(my_profile.profile_url)).path
        unique_url_name = path.split("/")[2] if len(path.split("/")) > 2 else None
        # myprint(f"Unique URL Name: {unique_url_name}")

        # For each comment element see if we have already replied; if so skip it
        for comment in comments:
            # Get the comment text
            comment_text = getText(comment.find_element(By.XPATH,
                                                        './/span[contains(@class,"comments-comment-item__main-content")][1]'))

            # Search the comment element using xpath for a child span that contains the text "Author"
            author_element = get_element_wait_retry(driver, wait,
                                                    f'.//a[contains(@href,"{unique_url_name}") and contains(@aria-label,"View")]',
                                                    "Finding Author Element", element_always_expected=False,
                                                    max_try=0,
                                                    parent_element=comment)

            if len(comment_text) > 75:
                short_comment_text = comment_text[:75]
            else:
                short_comment_text = comment_text
            if author_element:
                myprint(f"We already replied to this comment: {short_comment_text}...")
                continue
            else:
                myprint(f"Responding to this comment: {short_comment_text}...")

                # Use the context of the post, and the comment to generate a response
                response = generate_ai_response(post_message, my_profile, post_comment=comment_text)
                myprint(f"AI Generated Response to Comment: {response}")

                try:

                    # Find and click the Reply Button
                    reply_button = click_element_wait_retry(driver, wait,
                                                            './/button[contains(@class,"reply")][1]',
                                                            "Finding Reply Button",
                                                            use_action_chain=True,
                                                            parent_element=comment)

                    # Find the text box (should be the element that now has focus)
                    text_box = driver.switch_to.active_element

                    # Simulate typing the comment in the text box
                    simulate_typing(driver, text_box, response)

                    # Sleep so post button shows up
                    time.sleep(2)

                    # Click the send button
                    # Find the parent element of the current text_box element where the parent element is a div with a class containing "comments-comment-texteditor"
                    parent_element = text_box.find_element(By.XPATH,
                                                           './ancestor::form')

                    # From this parent element, find the child button element with a span element containing the text "Reply"
                    send_reply_button = click_element_wait_retry(driver, wait, './/button[contains(@class, "submit")]',
                                                                 "Finding Send Reply Button",
                                                                 parent_element=parent_element,
                                                                 max_retry=1, use_action_chain=True)

                    # Sleep 3 seconds to let the click register
                    time.sleep(3)

                    # Update DB with log entry
                    insert_new_log(user_id=user_id, post_id=post_id, action_type=LogActionType.REPLY,
                                   result=LogResultType.SUCCESS,
                                   post_url=post_url, message=response)

                    # From the parent element, find the like button and click it
                    like_button = click_element_wait_retry(driver, wait,
                                                           './/button[contains(@aria-label,"Like") and contains(@class,"react-button__trigger")][1]',
                                                           "Finding Like Comment Button",
                                                           parent_element=comment,
                                                           max_retry=1, use_action_chain=True)


                except Exception as e:
                    myprint(f"Error while replying to comment: {e}")
                    # Update DB with log entry
                    insert_new_log(user_id=user_id, post_id=post_id, action_type=LogActionType.REPLY,
                                   result=LogResultType.FAILURE,
                                   post_url=post_url, message=response)



    else:
        myprint("Could not find successful post for this user and post_id. Sleeping...")

    # Re-schedule the task in the queue for the future
    if loop_for_duration:
        elapsed_time = datetime.now() - start_time
        new_loop_for_duration = round(loop_for_duration - elapsed_time.total_seconds() - future_forward)
        frame = inspect.currentframe()
        current_function_name = frame.f_code.co_name
        args, _, _, values = inspect.getargvalues(frame)
        kwargs = {arg: values[arg] for arg in args}
        # myprint(f"{current_function_name} parameters: {kwargs}")

        if new_loop_for_duration < 0:
            myprint(f"Loop duration reached. Stopping {current_function_name} task...")
        else:
            # Change the value of the loop_for_duration parameter
            kwargs['loop_for_duration'] = new_loop_for_duration
            # Add our function call back to the task queue
            myprint(f"Adding {current_function_name} back to queue for {future_forward} seconds in the future...")
            # Remove 'self' from kwargs if it exists
            if 'self' in kwargs:
                del kwargs['self']

            # Call self again in the future
            globals()[current_function_name].apply_async(kwargs=kwargs, countdown=future_forward)

    quit_gracefully(driver)


def accept_connection_request(user_id: int):
    """Accept connection requests for the given user."""

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Accept Connection Requests')

    login_to_linkedin(driver, wait, user_email, user_password)

    # Navigate to the invitations manager page
    driver.get("https://www.linkedin.com/mynetwork/invitation-manager/")

    try:

        # Get all the invitation use the href and text (invitee name) to send a DM
        invitations = get_elements_as_list_wait_stale(wait,
                                                      "(//div[contains(@class,'invitation-card__container')]//div[contains(@class,'details')]//a)[2]",
                                                      "Finding Invitation Names and Urls")

        # For each invitation store the url and name to a dict using url as the key
        invitation_data = {invitation.get_attribute('href'): getText(invitation) for invitation in invitations}

        # Find and click all the accept buttons
        accept_buttons = get_elements_as_list_wait_stale(wait, '//button[contains(@aria-label,"Accept")]',
                                                         "Finding Accept Buttons")

        for accept_button in accept_buttons:
            accept_button.click()
            time.sleep(2)  # Wait for 2 seconds

    except Exception as e:
        myprint(f"Error while accepting connection requests: {e}")
        invitation_data = {}

    # Return the invitations list
    return invitation_data


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, 'unlock_before_run': True, 'keys':['user_id']}, reject_on_worker_lost=True,
                  rate_limit='2/m')
def automate_appreciation_dms_for_user(self, user_id: int, loop_for_duration: int = None, future_forward: int = 60):
    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Automate Appreciation DMs')

    login_to_linkedin(driver, wait, user_email, user_password)

    start_time = datetime.now()

    myprint("Sending Appreciations here...")

    result = "Appreciation DMs Sent"

    # After Accepting a Connection Request:
    invitations_accepted = accept_connection_request(user_id)
    # Send a private DM for each invitation
    for profile_url, name in invitations_accepted.items():
        message = f"Hi {name}, I appreciate you connecting with me on LinkedIn. I look forward to learning more about you and your work."
        send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})

    # TODO: After Receiving a Recommendation:

    # TODO: After an Interview:

    # TODO: For a Successful Collaboration:

    # General Appreciation:
    # "Hi [Name], I really appreciate your insights on [topic]. Your perspective helped me see things differently, and I'm grateful for the opportunity to learn from you."

    # profile_url = '' # TODO: Update
    # message = '' # TODO: Update
    # TODO: Use this line #send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})

    # Re-schedule the task in the queue for the future
    if loop_for_duration:
        elapsed_time = datetime.now() - start_time
        new_loop_for_duration = round(loop_for_duration - elapsed_time.total_seconds() - future_forward)
        frame = inspect.currentframe()
        current_function_name = frame.f_code.co_name
        args, _, _, values = inspect.getargvalues(frame)
        kwargs = {arg: values[arg] for arg in args}
        # myprint(f"{current_function_name} parameters: {kwargs}")

        if new_loop_for_duration < 0:
            myprint(f"Loop duration reached. Stopping {current_function_name} task...")
        else:
            # Change the value of the loop_for_duration parameter
            kwargs['loop_for_duration'] = new_loop_for_duration
            # Add our function call back to the task queue
            myprint(f"Adding {current_function_name} back to queue for {future_forward} seconds in the future...")
            # Remove 'self' from kwargs if it exists
            if 'self' in kwargs:
                del kwargs['self']
            # Call self again in the future
            globals()[current_function_name].apply_async(kwargs=kwargs, countdown=future_forward)

    quit_gracefully(driver)

    return result


def generate_and_post_comment(driver, wait, post_link, my_profile: LinkedInProfile) -> bool:
    if post_link != driver.current_url:
        # Switch to post url
        driver.get(post_link)

    # Get my user_id
    user_id = get_user_id(my_profile.email)

    # Check to make sure user hasn't already commented on this post
    if check_commented(driver, wait, user_id, post_link):
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
    read_time = simulate_reading_time(content) / 2
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
    kwargs = {'user_id': get_user_id(my_profile.email),
              'post_link': post_link,
              'comment_text': comment_text}
    comment_on_post.apply_async(kwargs=kwargs)

    myprint("Comment Posted")

    return True


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True,'unlock_before_run': True, 'keys':['user_id']})
def automate_profile_viewer_engagement(self, user_id: int, loop_for_duration: int = None, future_forward: int = 60):
    global stop_all_thread

    myprint(f"Starting Profile Viewer DMs")

    driver, wait, user_email, my_profile = get_current_profile(user_id=user_id, session_name="Profile Viewer DMs")

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
                if (datetime.now() - last_viewed_date).days > 1:
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

    # Get all the viewer names and urls into list so that elements don't go stale
    viewer_names = [
        getText(e.find_element(By.XPATH, './/div[contains(@class,"artdeco-entity-lockup__title")]/span/span[1]')) for e
        in viewer_elements]
    viewer_urls = [e.get_attribute('href') for e in viewer_elements]
    # Merge them into a dictionary to iterate over
    viewer_data = dict(zip(viewer_names, viewer_urls))

    # Get the viewed data from each element and filter by a day ago or specific date
    for viewer_name, viewer_url in viewer_data.items():
        # Switch back to tab
        driver.switch_to.window(current_tab)

        myprint(f"Viewer Name: {viewer_name}")
        myprint(f"Viewer URL: {viewer_url}")

        # Wait for the new window or tab
        driver.switch_to.new_window('tab')
        wait.until(EC.new_window_is_opened(handles))

        # Switch to viewer_url
        driver.get(viewer_url)

        # Engage with the viewer
        kwargs = {'user_id': get_user_id(my_profile.email),
                  'viewer_url': viewer_url,
                  'viewer_name': viewer_name}
        engage_with_profile_viewer.apply_async(kwargs=kwargs)

        # Close tab when done
        close_tab(driver)

    # Re-schedule the task in the queue for the future
    if loop_for_duration:
        elapsed_time = datetime.now() - start_time
        new_loop_for_duration = round(loop_for_duration - elapsed_time.total_seconds() - future_forward)
        frame = inspect.currentframe()
        current_function_name = frame.f_code.co_name
        args, _, _, values = inspect.getargvalues(frame)
        kwargs = {arg: values[arg] for arg in args}
        # myprint(f"{current_function_name} parameters: {kwargs}")

        if new_loop_for_duration < 0:
            myprint(f"Loop duration reached. Stopping {current_function_name} task...")
        else:
            # Change the value of the loop_for_duration parameter
            kwargs['loop_for_duration'] = new_loop_for_duration
            # Add our function call back to the task queue
            myprint(f"Adding {current_function_name} back to queue for {future_forward} seconds in the future...")
            # Remove 'self' from kwargs if it exists
            if 'self' in kwargs:
                del kwargs['self']

            # Call self again in the future
            globals()[current_function_name].apply_async(kwargs=kwargs, countdown=future_forward)

    quit_gracefully(driver)


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, 'keys': ['user_id', 'viewer_url']},
                  reject_on_worker_lost=True, rate_limit='2/m')
def engage_with_profile_viewer(self, user_id: int, viewer_url, viewer_name):
    myprint(f"Starting Profile Viewer Engagement")

    # Check if we already engaged with this viewer today
    if has_engaged_url_with_x_days(user_id, viewer_url, 1):
        myprint(f"Already engaged with {viewer_name} today. Skipping...")
        return
    else:

        # Log engagement efforts to the log
        insert_new_log(user_id=user_id, action_type=LogActionType.ENGAGED, result=LogResultType.SUCCESS,
                       post_url=viewer_url,
                       message=f"Engaged with {viewer_name}")

        driver, wait, user_email, my_profile = get_current_profile(user_id=user_id,
                                                                   session_name="Profile Viewer Engagement")

        myprint(f"Engaging from: {my_profile.full_name} to: {viewer_name}")

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
                recent_activities = profile.recent_activities

                myprint(f"Recent Activities Count: {len(recent_activities)}")

                # Filter activities by posted date less than a week ago
                recent_activities = [activity for activity in recent_activities if
                                     (datetime.now() - activity.posted).days <= 7]

                myprint(f"Recent Activities Filtered (1 week) Count: {len(recent_activities)}")

                # DONT: Shuffle the activities (they are already in order of latest to oldest)
                # random.shuffle(recent_activities)
                able_to_comment = False

                # Filter list to activities I haven't commented on
                for activity in recent_activities:
                    link = str(activity.link)

                    # Navigate to Link
                    myprint(f"Navigating To: {link}")
                    driver.get(link)
                    commented = check_commented(driver, link)
                    if not commented:
                        # Leave comment on that activity
                        able_to_comment = generate_and_post_comment(driver, wait, link, my_profile)
                        if able_to_comment:
                            break  # Only comment/interact with one

                if not able_to_comment:
                    myprint("No activities, unable to or already left comment")

                    # TODO: Send DM - offer something of value—whether it's insights, resources, or potential collaboration opportunities.
                    # TODO: Generate something of value to offer

                    # Get the first name from the view_name by splitting on space
                    first_name = viewer_name.split(" ")[0]
                    message = f"Hi {first_name}, I noticed we're connected on LinkedIn and wanted to reach out. I'm currently working on a project that I think you might find interesting. Would you be open to a quick chat to discuss it further?"

                    # Send actual DM
                    kwargs = {'user_id': get_user_id(my_profile.email),
                              'profile_url': str(profile.profile_url),
                              'message': message}
                    send_private_dm.apply_async(kwargs=kwargs)
            else:
                # myprint(f"We Are {profile.connection} Connections")
                # If not 1st connections, send them a connection request
                # Mention something specific about their profile or company to show genuine interest and that you've done your research
                recent_activity_summary = summarize_recent_activity(profile, my_profile)
                response = profile.generate_personalized_message(recent_activity_message=recent_activity_summary,
                                                                 from_name=my_profile.full_name)
                myprint(f"Original Response: {response}")
                refined_response = get_ai_message_refinement(response)
                myprint(f"Refined Response: {refined_response}")

                # Send connection request with this message
                kwargs = {'user_id': get_user_id(my_profile.email),
                          'profile_url': str(profile.profile_url),
                          'message': refined_response}
                invite_to_connect.apply_async(kwargs=kwargs)
        else:
            myprint(f"Failed to get profile data for {viewer_name}")

        quit_gracefully(driver)


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True}, reject_on_worker_lost=True,
                  rate_limit='2/m')
def clean_stale_invites(self, user_id: int):
    """Cleans up stale invites that the user has sent"""

    # TODO": Implement this method and
    # user_email, user_password = get_user_password_pair_by_id(user_id)

    # driver, wait = get_driver_wait_pair(session_name='Private DM')

    # login_to_linkedin(driver, wait, user_email, user_password)

    pass


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True}, reject_on_worker_lost=True,
                  rate_limit='2/m')
def send_private_dm(self, user_id: int, profile_url: str, message: str):
    """ Send dm message to a profile. Must be a 1st connection"""

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Private DM')

    login_to_linkedin(driver, wait, user_email, user_password)

    # Open the profile URL
    driver.get(profile_url)

    dm_sent = False

    myprint("Sending DM: " + message)

    final_result = "DM "

    try:

        # Click on message button
        click_element_wait_retry(driver, wait, '//main//button[contains(@aria-label,"Message")]',
                                 "Finding Message Button", max_retry=1, use_action_chain=True)

        # Find the message box
        message_box = get_element_wait_retry(driver, wait, '//div[contains(@class,"contenteditable")]//p',
                                             'Finding Message Box', max_try=1, )

        # Select All (Must be done this way. Clear command does not work)
        message_box.send_keys(Keys.CONTROL + "a")
        # Delete what is selected
        message_box.send_keys(Keys.DELETE)

        # Find the message box (again)
        # message_box = driver.switch_to.active_element
        message_box = get_element_wait_retry(driver, wait, '//div[contains(@class,"contenteditable")]//p',
                                             'Finding Message Box', max_try=1, )

        # Type the message into the box
        simulate_typing(driver, message_box, message)

        # Sleep so send button can become active
        time.sleep(2)

        # Click the send button
        click_element_wait_retry(driver, wait, "//button[contains(@class,'msg-form__send-button')]",
                                 "Finding Send Button", max_retry=1, use_action_chain=True)

        dm_sent = True

        final_result += " Sent Successfully"

    except Exception as e:
        final_result += f"Failed. Error: {str(e)}"

    # Update DB logs with DM Sent
    insert_new_log(user_id=user_id, action_type=LogActionType.DM,
                   result=LogResultType.SUCCESS if dm_sent else LogResultType.FAILURE,
                   post_url=profile_url, message=message)

    quit_gracefully(driver)  # Close the driver

    myprint(f"{final_result}")
    return final_result


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, 'keys': ['user_id', 'profile_url']},
                   reject_on_worker_lost=True, rate_limit='1/m')
def invite_to_connect(self, user_id: int, profile_url: str, message: str = None):
    # TODO: Add log entry for successfule and failed invites to connect

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Invite to Connect')

    login_to_linkedin(driver, wait, user_email, user_password)

    if profile_url != driver.current_url:
        # Open the profile URL
        driver.get(profile_url)

    myprint(f"Inviting to connect: {profile_url}")

    # Locate the connect button
    try:
        click_element_wait_retry(driver, wait, '//main//button[contains(@aria-label, "Invite ")]',
                                 "Finding Connect Button", max_retry=1, use_action_chain=True)

        myprint("Found Connect Button and clicked it")


    except Exception as ce:
        # If it doesn't exist click the more than find the connect button there
        try:
            # Click the last more button
            click_element_wait_retry(driver, wait,
                                     '//main//button[contains(@aria-label,"More actions")]',
                                     "Finding More Button", max_retry=1, use_action_chain=True)

            # driver.find_elements(By.XPATH, '//main//button[contains(@aria-label,"More actions")]')[-1].click()

            myprint("Found More Button and clicked it")

            # Click the last connect button
            click_element_wait_retry(driver, wait, '//main//div[contains(@aria-label,"connect")]',
                                     "Finding Connect Button", max_retry=1, use_action_chain=True)

            # driver.find_elements(By.XPATH, '//div[contains(@aria-label,"connect")]')[-1].click()

            myprint("Found Connect Button and clicked it")
        except Exception as e:
            myprint(f"Failed to find more or connect button: Error: {str(e)}")
            return f"Failed to find more or connect button: Error: {str(e)}"

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
            return f"Failed to Add a note. Error: {str(e)}"
    else:
        # Else click send connection
        try:
            click_element_wait_retry(driver, wait,
                                     '//button[contains(@aria-label,"Send without a note")]',
                                     "Finding Send Without Note Button", use_action_chain=True)

            myprint("Found Send Without a Note Button and clicked it")
        except Exception as e:
            myprint(f"Failed to find send without a note connection button. Error: {str(e)}")
            return f"Failed to find send without a note connection button. Error: {str(e)}"

    quit_gracefully(driver)  # Close the driver

    return "Connection Request Sent Successfully"


def start_process():
    # TOO: Get reid of this method
    pass


def final_method(drivers: List[WebDriver]):
    global stop_all_thread
    stop_all_thread.set()  # Set the flag to stop other threads
    for driver in drivers: quit_gracefully(driver)  # Quit all the drivers
    myprint("All drivers stopped. Program has exited.")
    sys.exit(0)


@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True}, reject_on_worker_lost=True,
                  rate_limit='1/m')
def update_stale_profile(self, user_id: int):
    myprint(f"Updating Stale Profile. User ID: {user_id}")
    driver, wait, user_email, my_profile = get_current_profile(user_id=user_id, session_name="Update Stale Profile")
    quit_gracefully(driver)
    return "Profile Updated Successfully"


def get_current_profile(user_id: int, session_name: str = "Get Current Profile") -> Tuple[
    WebDriver, WebDriverWait, str, LinkedInProfile]:
    """Update the profile of the user"""

    myprint(f"Getting Updated Profile")

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name=session_name)

    login_to_linkedin(driver, wait, user_email, user_password)

    my_profile = get_my_profile(driver, wait, user_email, user_password)

    return driver, wait, user_email, my_profile


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

    # start_process()
    # myprint("Process finished")
    pass





@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, 'keys': [ 'post_id']}, reject_on_worker_lost=True,
                  rate_limit='2/m')
def post_to_linkedin(self, user_id: int, post_id: int):
    """Posts to LinkedIn using the LinkedIn API - https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin#creating-a-share-on-linkedin"""

    # TODO: If this is still running 4 times then add de-duplication logic
    task_id = f"{self.request.id}-{user_id}-{post_id}"
    myprint(f"Post To LinkedIn | Task ID: {task_id}")
    # Mark the task as executed
    #TaskExecution.objects.create(task_id=task_id)

    # Login and publish post to LinkedIn
    user_email, user_password = get_user_password_pair_by_id(user_id)
    myprint(f"Posting to LinkedIn as user: {user_email}")

    # Get the post content
    content = get_post_content(post_id)
    myprint(f"Posting to LinkedIn: {content}")

    # Get the post video url
    video_url = get_post_video_url(post_id)

    # Add the query param content_type to the url
    if video_url:
        myprint(f"Adding to Post | Video URL: {video_url}")

    urn = share_on_linkedin(user_id, content, video_url)

    if urn:
        post_url = f"https://www.linkedin.com/feed/update/{urn}/"
        myprint(f"Successfully created post using /posts API endpoint: {post_url}")

        # Update DB with status=posted
        update_db_post_status(post_id, PostStatus.POSTED)

        # Schedule Reply to comments for 30 minutes now that this has been posted
        base_kwargs = {
            'user_id': user_id,
            'post_id': post_id,
            'loop_for_duration': 60 * 30
        }
        automate_reply_commenting.apply_async(kwargs=base_kwargs)

        # Update DB with status=success in the logs table and the post url
        insert_new_log(user_id=user_id, action_type=LogActionType.POST, result=LogResultType.SUCCESS, post_id=post_id,
                       post_url=post_url,
                       message=f"Successfully created post using /posts API endpoint.")

        return f"Post successfully created"

    else:
        myprint(f"Failed to create post using /posts API endpoint")
        # Update DB with status=failed in the logs table
        insert_new_log(user_id=user_id, action_type=LogActionType.POST, result=LogResultType.FAILURE, post_id=post_id,
                       message="Failed to create post using /posts API endpoint.")

        return f"Failed to create post using /posts API endpoint"
