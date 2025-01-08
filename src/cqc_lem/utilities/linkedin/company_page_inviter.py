import re
import time

from selenium.common import ElementClickInterceptedException, TimeoutException
from selenium.webdriver import ActionChains

from cqc_lem.utilities.db import get_user_password_pair_by_id, get_company_linked_in_url_for_user
from cqc_lem.utilities.linkedin.helper import login_to_linkedin
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import get_element_wait_retry, get_elements_as_list_wait_stale, getText, \
    wait_for_ajax, click_element_wait_retry


def get_available_credits(driver, wait):
    # myprint("Entering get_available_credits function.")
    current_credits = 0
    total_credits = 0

    try:
        credit_text_element = get_element_wait_retry(driver, wait, '//span[text()[contains(.,"credits available")]]/span',
                                                 "Finding Credits Text Element", max_try=0)
        credit_text = getText(credit_text_element)
        current_credits, total_credits = map(int, credit_text.split('/'))
    except TimeoutException as te:
        myprint("No remaining invite credits")

    myprint(f"Credits available: {current_credits}/{total_credits}")
    return current_credits, total_credits


def get_initial_selected_count(driver, wait):
    # myprint("Entering get_initial_selected_count function.")
    selected_text_element = get_element_wait_retry(driver, wait, '//span[text()[contains(.,"selected")]]',
                                                   "Finding Selected Text Element")
    selected_text = selected_text_element.text.strip()
    initial_selected_count = int(re.search(r'\d+', selected_text).group())
    myprint(f"Initial selected count: {initial_selected_count}")
    return initial_selected_count


def scroll_invitee_list(driver, wait):
    invitee_list_element = get_element_wait_retry(driver, wait,
                                                  "//div[contains(@class,'scaffold-finite-scroll__content')]",
                                                  "Finding Invitee List Element", max_try=0)

    # myprint("Entering scroll_invitee_list function.")
    current_height = driver.execute_script("return arguments[0].scrollHeight", invitee_list_element)
    #myprint(f"Current height: {current_height}")

    # There is a div at the bottom of the ul. Sroll it into view
    hidden_div = get_element_wait_retry(driver, wait, '//*[@id="invitee-picker-results-container"]/div/div[2]',
                                        "Finding Hidden Div")

    # driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight; arguments[1].scrollIntoView(false);",
    #                      invitee_list_element, hidden_div)  # Almost but no cigar

    # Use Selenium mouse wheel actions to simulate scrolling
    actions = ActionChains(driver)
    actions.move_to_element(invitee_list_element).move_to_element(hidden_div).scroll_by_amount(0,
                                                                                               1000).perform()  # Simulate scrolling down 1000 pixels
    wait_for_ajax(driver)  # Wait for the AJAX request to load more connections
    time.sleep(2)  # Sleep for a bit to let the AJAX request load more connections

    myprint("Scrolled down to load more connections.")


def select_connection_checkboxes(driver, wait, limit):
    # myprint("Entering select_connection_checkboxes function.")

    # Get the list of connections and scroll until there are as many available as the limit we need or end if there are now new connections
    checkbox_count = 0
    connections_list_count = 0
    checkboxes = []
    while checkbox_count < limit:
        connections_list = get_elements_as_list_wait_stale(wait,
                                                           "//div[contains(@class,'scaffold-finite-scroll__content')]//li",
                                                           "Finding Connections List", max_retry=0)
        new_connections_list_count = len(connections_list)

        try:
            checkboxes = get_elements_as_list_wait_stale(wait, "//input[@type='checkbox' and contains(@id, 'invitee')]",
                                                         "Finding Checkboxes", max_retry=0)
        except TimeoutException as te:
            myprint("No checkboxes found.")
            checkboxes = []

        new_checkbox_count = len(checkboxes)

        myprint(f"New connections list count: {new_connections_list_count}, New checkbox count: {new_checkbox_count}")

        if (new_checkbox_count != checkbox_count and new_checkbox_count < limit) and new_connections_list_count != connections_list_count:
            checkbox_count = new_checkbox_count
            connections_list_count = new_connections_list_count
            # Scroll
            scroll_invitee_list(driver, wait)
        else:
            myprint("No new checkboxes nor invitees after scrolling.")
            break  # Break the while loop

    selected_count = get_initial_selected_count(driver, wait)
    myprint(f"Starting with selected_count = {selected_count}")

    for checkbox in checkboxes:
        if selected_count >= limit:
            break
        if not checkbox.is_selected():
            driver.execute_script("arguments[0].click();", checkbox)
            selected_count += 1

    if selected_count < limit:
        myprint(f"Selected {selected_count} connections so far. Could not reach limit of {limit}.")

    myprint(f"Completed selecting checkboxes with selected_count = {selected_count}")
    return selected_count


def invite_selected_connections(driver, wait):
    # myprint("Entering invite_selected_connections function.")
    xpath = "//div[contains(@class,'modal')]//button[contains(@class,'artdeco-button--primary')]"
    invite_button = click_element_wait_retry(driver, wait, xpath, "Finding Invite Button",
                                             element_always_expected=False)
    if invite_button:
        # invite_button.click()
        myprint("Invite button clicked.")
        return True

    myprint("Invite button not found.")
    return False


def dismiss_prompt(driver, wait):
    # myprint("Entering dismiss_prompt function.")
    dismiss_button = click_element_wait_retry(driver, wait,
                                              "//button[@data-test-org-post-nudge-dismiss-cta]",
                                              "Finding Dismiss Button", element_always_expected=False,
                                              max_retry=0)
    if dismiss_button:
        myprint('"No thanks" button clicked.')
        return True
    myprint("No 'No thanks' button found.")
    return False


def automate_invitations(driver, wait, user_id):
    myprint("Automate invitations to Company Page.")

    user_email, user_password = get_user_password_pair_by_id(user_id)

    # Get Company page from DB
    li_company_page_url = get_company_linked_in_url_for_user(user_id)

    login_to_linkedin(driver, wait, user_email, user_password)

    # Add ?invite=true query parameter to the URL to navigate to the invite page
    invite_page_url = li_company_page_url + "?invite=true"

    # Navigate to Company Page
    if driver.current_url != invite_page_url:
        driver.get(invite_page_url)

    current_credits, total_credits = get_available_credits(driver, wait)
    if current_credits <= 0:
        myprint("No credits available. Exiting automate_invitations.")
        return

    myprint(f"Credits Available: {current_credits}/{total_credits}")

    selected_count = select_connection_checkboxes(driver, wait, current_credits)
    if selected_count > 0:
        if invite_selected_connections(driver, wait):
            time.sleep(2)  # Delay to ensure the prompt appears before checking for it
            if dismiss_prompt(driver, wait):
                myprint("Prompt handled")
            else:
                myprint("No prompt to handle.")

            # If the selected_count is less than the current_credits, we can continue inviting
            if selected_count < current_credits:
                myprint("Continuing automate_invitations.")
                selected_count += automate_invitations(driver, wait, user_id)
        else:
            myprint("No invite button found, stopping automate_invitations.")
    else:
        myprint("No more connections to invite or already selected. Exiting automate_invitations.")

    return selected_count