import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from dotenv import load_dotenv
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from cqc_lem.linked_in_profile import LinkedInProfile
from cqc_lem.my_celery import app as shared_task
from cqc_lem.utilities.ai.ai_helper import generate_ai_response, get_ai_message_refinement, summarize_recent_activity
from cqc_lem.utilities.date import convert_viewed_on_to_date
from cqc_lem.utilities.db import get_user_password_pair_by_id, get_user_id, insert_new_log, LogActionType, \
    LogResultType, has_user_commented_on_post_url, get_post_url_from_log_for_user, get_post_message_from_log_for_user
from cqc_lem.utilities.env_constants import LI_USER
from cqc_lem.utilities.linked_in_helper import login_to_linkedin, get_my_profile, get_linkedin_profile_from_url
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import click_element_wait_retry, \
    get_element_wait_retry, get_elements_as_list_wait_stale, getText, close_tab, get_driver_wait_pair, quit_gracefully
from cqc_lem.utilities.utils import debug_function

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
        time.sleep(5)  # Wait for the feed to load

    # Find and click the "Sort by" dropdown
    click_element_wait_retry(driver, wait, '//button/hr',
                             "Clicking Sort By Dropdown", use_action_chain=True)

    time.sleep(1)

    # Select "Recent" from the dropdown
    try:
        click_element_wait_retry(driver, wait, '//div[contains(@class,"artdeco-dropdown")]/ul/li[2]',
                                 "Selecting Recent Option", max_try=1, use_action_chain=True)

        time.sleep(3)  # Wait for the page to refresh with recent posts
    except TimeoutException as te:
        myprint("Timeout Exception: " + str(te))

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


def simulate_typing(driver: WebDriver, editable_element: WebElement, text):
    # Simulate typing the comment
    myprint("Typing Text...")
    for char in text:
        try:
            if ord(char) > 0xFFFF:
                # Use JavaScript to set the value for characters outside the BMP
                driver.execute_script("arguments[0].value += arguments[1];", editable_element, char)
            else:
                editable_element.send_keys(char)
        except Exception as e:
            myprint("Error while sending char(" + char + "): " + str(e))

        type_speed_reducer = .5
        time.sleep(random.uniform(0.05 * type_speed_reducer, 0.15 * type_speed_reducer))  # Simulate human typing speed
    myprint("Finished Typing!")


@shared_task.task(rate_limit='2/m')
@debug_function
def comment_on_post(user_id: int, post_link: str, comment_text: str):
    """Post a comment to the given post link"""

    driver, wait = get_driver_wait_pair(session_name='Post Comment')

    user_email, user_password = get_user_password_pair_by_id(user_id)

    login_to_linkedin(driver, wait, user_email, user_password)

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
    simulate_typing(driver, comment_box, comment_text)

    # Sleep so post button shows up
    time.sleep(2)

    method_result = ''

    try:
        # Find and click the post button
        click_element_wait_retry(driver, wait, '//button[contains(@class, "comments-comment-box__submit-button--cr")]',
                                 "Clicking Post Button", max_try=1, use_action_chain=True)

        myprint(f"Added Post via Post Button")
        method_result = f"Added Post via Post Button"

        # Update database with record of comment to this post
        insert_new_log(user_id=user_id, action_type=LogActionType.COMMENT, result=LogResultType.SUCCESS,
                       post_url=post_link, message=comment_text)

    except NoSuchElementException:
        # If the post button is not found, send a return key to post the comment
        comment_box.send_keys('\n')
        # Update database with record of comment to this post
        insert_new_log(user_id=user_id, action_type=LogActionType.COMMENT, result=LogResultType.FAILURE,
                       post_url=post_link, message=comment_text)
        myprint(f"Added Post via return key. This might not have worked")
        method_result = f"Added Post via return key. This might not have worked"

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
            myprint(f"Added Post Reaction")
            method_result += f" | Added Post Reaction"
            break  # Exit loop if click is successful
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait a bit before retrying
            else:
                myprint(f"Failed to click Post Reaction: {e}")
                method_result += f" | Added Post Reaction | Error: {e}"

    quit_gracefully(driver)  # Close the driver

    return method_result


def check_commented(driver, wait, user_id: int = None, post_url: str = None):
    """See if the current open url we've already posted on"""
    already_commented = False
    post_link = driver.current_url

    # Check if we have already commented on this post

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


@shared_task.task
@debug_function
def automate_commenting(user_id: int, loop_for_duration=None, **kwargs):
    global stop_all_thread

    myprint("Starting Automate Commenting Thread...")

    driver, wait = get_driver_wait_pair(session_name='Automate Commenting')

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

    quit_gracefully(driver)


@shared_task.task
@debug_function
def automate_reply_commenting(user_id: int, post_id: int, loop_for_duration=None, **kwargs):
    """Reply to recent comments left on the post recently posted"""

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Reply to Comments')

    login_to_linkedin(driver, wait, user_email, user_password)

    # Get My Profile for later use
    my_profile = get_my_profile(driver, wait, user_email, user_password)

    start_time = datetime.now()

    while True:

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
                                                                     max_try=0,
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
                                                           "Finding Comments")
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

                        # Find the text box (should be the element that now has focus
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
                        reply_button = click_element_wait_retry(driver, wait, './/button[contains(@class, "submit")]',
                                                                "Finding Send Reply Button",
                                                                parent_element=parent_element,
                                                                max_try=1, use_action_chain=True)

                        # Sleep 3 seconds to let the click register
                        time.sleep(3)

                        # Update DB with log entry
                        insert_new_log(user_id=user_id, action_type=LogActionType.REPLY, result=LogResultType.SUCCESS,
                                       post_url=post_url, message=response)

                    except Exception as e:
                        myprint(f"Error while replying to comment: {e}")
                        # Update DB with log entry
                        insert_new_log(user_id=user_id, action_type=LogActionType.REPLY, result=LogResultType.FAILURE,
                                       post_url=post_url, message=response)



        else:
            myprint("Could not find successful post for this user and post_id. Sleeping...")
            time.sleep(60)  # Sleep for 60 seconds

        if loop_for_duration:
            elapsed_time = datetime.now() - start_time
            if elapsed_time.total_seconds() >= loop_for_duration:
                myprint("Loop duration reached. Stopping Automate Reply Commenting thread...")
                break
        else:
            break

        time.sleep(15)  # Sleep for 15 seconds

    quit_gracefully(driver)


def accept_connection_request(user_id: int):
    """Accept connection requests for the given user."""

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Accept Connection Requests')

    login_to_linkedin(driver, wait, user_email, user_password)

    # Navigate to the invitations manager page
    driver.get("https://www.linkedin.com/mynetwork/invitation-manager/")

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

    # Return the invitations list
    return invitation_data


@shared_task.task(rate_limit='2/m')
@debug_function
def send_appreciation_dms_for_user(user_id: int, loop_for_duration=None):
    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Automate Appreciation DMs')

    login_to_linkedin(driver, wait, user_email, user_password)

    start_time = datetime.now()

    while True:

        myprint("Sending Appreciations here...")

        # After Accepting a Connection Request:
        invitations_accepted = accept_connection_request(user_id)
        # Send a private DM for each invitation
        for profile_url, name in invitations_accepted.items():
            message = f"Hi {name}, I appreciate you connecting with me on LinkedIn. I look forward to learning more about you and your work."
            send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})

        # After Receiving a Recommendation:

        # After an Interview:

        # For a Successful Collaboration:

        # General Appreciation:
        # "Hi [Name], I really appreciate your insights on [topic]. Your perspective helped me see things differently, and I'm grateful for the opportunity to learn from you."

        # profile_url = '' # TODO: Update
        # message = '' # TODO: Update
        # TODO: Use this line #send_private_dm.apply_async(kwargs={"user_id": user_id, "profile_url": profile_url, "message": message})

        if loop_for_duration:
            elapsed_time = datetime.now() - start_time
            if elapsed_time.total_seconds() >= loop_for_duration:
                myprint("Loop duration reached. Stopping Automate Appreciations thread...")
                break
        else:
            break

        time.sleep(10)  # Sleep for 10 seconds

    quit_gracefully(driver)

    return "Appreciation DMs Sent"


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
    kwargs = {'user_id': get_user_id(my_profile.email),
              'post_link': post_link,
              'comment_text': comment_text}
    comment_on_post.apply_async(kwargs=kwargs, retry=True, retry_policy={
        'max_retries': 3,
        'interval_start': 60,
        'interval_step': 30
    })

    myprint("Comment Posted")

    return True


@shared_task.task
@debug_function
def automate_profile_viewer_engagement(user_id: int, loop_for_duration=None, **kwargs):
    global stop_all_thread

    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Profile Viewer DMs')

    myprint(f"Starting Profile Viewer DMs")

    login_to_linkedin(driver, wait, user_email, user_password)

    my_profile = get_my_profile(driver, wait, user_email, user_password)

    # Navigate to profile view page
    driver.get("https://www.linkedin.com/analytics/profile-views/")

    start_time = datetime.now()

    viewed_on_xpath = './/div[contains(@class,"artdeco-entity-lockup__caption ember-view")]'

    continue_process = True

    while continue_process:  # Keep looping until we find a viewed on date out of range
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

        if loop_for_duration:
            elapsed_time = datetime.now() - start_time
            if elapsed_time.total_seconds() >= loop_for_duration:
                myprint("Loop duration reached. Stopping Automate Commenting thread...")
                continue_process = False
                break
        elif stop_all_thread.is_set():
            myprint("Stopping Automate Profile Viewers DMs thread...")
            continue_process = False
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

        # Engage with the viewer
        kwargs = {'user_id': get_user_id(my_profile.email),
                  'viewer_url': viewer_url,
                  'viewer_name': viewer_name}
        engage_with_profile_viewer.apply_async(kwargs=kwargs, retry=True,
                                               retry_policy={
                                                   'max_retries': 3,
                                                   'interval_start': 60,
                                                   'interval_step': 30

                                               })

        # Close tab when done
        close_tab(driver)

    quit_gracefully(driver)


@shared_task.task(rate_limit='2/m')
@debug_function
def engage_with_profile_viewer(user_id: int, viewer_url, viewer_name):
    user_email, user_password = get_user_password_pair_by_id(user_id)

    driver, wait = get_driver_wait_pair(session_name='Profile Viewer Engagement')

    myprint(f"Starting Profile Viewer Engagement")

    login_to_linkedin(driver, wait, user_email, user_password)

    my_profile = get_my_profile(driver, wait, user_email, user_password)

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
                kwargs = {'user_id': get_user_id(my_profile.email),
                          'profile_url': str(profile.profile_url),
                          'message': message}
                send_private_dm.apply_async(kwargs=kwargs, retry=True,
                                            retry_policy={
                                                'max_retries': 3,
                                                'interval_start': 60,
                                                'interval_step': 30

                                            })
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
            kwargs = {'user_id': get_user_id(my_profile.email),
                      'profile_url': str(profile.profile_url),
                      'message': refined_response}
            invite_to_connect.apply_async(kwargs=kwargs, retry=True,
                                          retry_policy={
                                              'max_retries': 3,
                                              'interval_start': 60,
                                              'interval_step': 30

                                          })
    else:
        myprint(f"Failed to get profile data for {viewer_name}")


@shared_task.task(rate_limit='2/m')
@debug_function
def send_private_dm(user_id: int, profile_url: str, message: str):
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

        # Click the message anywhere button
        message_anywhere_button = click_element_wait_retry(driver, wait,
                                                           "//a[contains(@class,'message-anywhere-button')]",
                                                           'Finding Message Anywhere Button', max_try=0,
                                                           use_action_chain=True, element_always_expected=False)

        if message_anywhere_button is None:
            myprint("Message anywhere button not found")

            # TODO: Figure out why this path doesnt work (Send button doesnt enable: Can/Should we force it)

            # Click on message button
            click_element_wait_retry(driver, wait, '//main//button[contains(@aria-label,"Message")]',
                                     "Finding Message Button", max_try=1, use_action_chain=True)

            # Find the message box (should be the element that now has focus)
            # message_box = driver.switch_to.active_element
            message_box = click_element_wait_retry(driver, wait, '//div[contains(@class,"contenteditable")]',
                                                   'Finding Message Box', max_try=1, use_action_chain=True)

        else:
            myprint("Clicked the Message anywhere button")
            # message_box = driver.switch_to.active_element
            message_box = click_element_wait_retry(driver, wait, '//div[contains(@class,"contenteditable")]',
                                                   'Finding Message Box', max_try=1, use_action_chain=True)

        # Send focus to message_box
        # ActionChains(driver).move_to_element(message_box).click().perform()

        # Clear the message box
        message_box.clear()

       # Create javascript to inject the message
        escaped_message = json.dumps(message)
        code = f"""
        var xpath = "//div[contains(@class,'contenteditable')]";
        var result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        var div = result.singleNodeValue;
        
        if (div) {{
            var element = document.createElement('p');
            var text = document.createTextNode('{escaped_message}');
            element.appendChild(text);
            div.appendChild(element);
        }}
        """

        # Add the message to the message box div
        driver.execute_script(code)

        # Sleep so send button can become active
        time.sleep(2)

        # Click the send button
        click_element_wait_retry(driver, wait, "//button[contains(@class,'msg-form__send-button')]",
                                 "Finding Send Button", max_try=1, use_action_chain=True)

        dm_sent = True

        final_result += " Sent Successfully"

    except Exception as e:
        myprint(f"Failed to send DM: {str(e)}")
        final_result += f"Failed. Error: {str(e)}"


    quit_gracefully(driver)  # Close the driver

    # Update DB logs with DM Sent
    insert_new_log(user_id=user_id, action_type=LogActionType.DM,
                   result=LogResultType.SUCCESS if dm_sent else LogResultType.FAILURE,
                   post_url=profile_url, message=message)

    return final_result


@shared_task.task(rate_limit='2/m')
@debug_function
def invite_to_connect(user_id: int, profile_url: str, message: str = None):
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
                                     "Finding Connect Button", max_try=2, use_action_chain=True)

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
    global time_remaining_seconds

    # Set Timer for 3 minutes
    time_remaining_seconds = 60 * 15

    drivers_needed = 3

    # build as many drivers as there are threads, so each thread gets own driver
    # drivers_with_waits = [get_driver_wait_pair() for _ in range(drivers_needed)]
    # all_drivers = [driver for driver, _ in drivers_with_waits]

    # def signal_handler(sig, frame):

    # Get list of all drivers from drivers_with_waits

    # final_method(all_drivers)

    # Register the signal handler for SIGINT
    # signal.signal(signal.SIGINT, signal_handler)

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
        executor.submit(automate_profile_viewer_engagement,
                        kwargs={'user_id': get_user_id(
                            LI_USER)})

    myprint("Time is up. Closing the browser")

    # final_method(all_drivers)


def final_method(drivers: List[WebDriver]):
    global stop_all_thread
    stop_all_thread.set()  # Set the flag to stop other threads
    for driver in drivers: quit_gracefully(driver)  # Quit all the drivers
    myprint("All drivers stopped. Program has exited.")
    sys.exit(0)


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
