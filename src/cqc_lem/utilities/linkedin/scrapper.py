import copy
import random
import re
from typing import List

from bs4 import BeautifulSoup, PageElement
from selenium import webdriver
from selenium.webdriver.common.by import By

from cqc_lem.utilities.date import convert_datetime_to_start_of_day
from cqc_lem.utilities.date import convert_viewed_on_to_date
from cqc_lem.utilities.date import get_linkedin_datetime_from_text
from cqc_lem.utilities.selenium_util import click_element_wait_retry, get_driver_wait, get_elements_as_list_wait_stale, \
    getText, wait_for_ajax

start_identifier_map = {
    "education": 19,
    "skills": 15,
    "endorsements": 19,
    "experience_company": 20,
    "experience_company_2": 26,
    "experience_company|start_end_date": 29,
    "experience_title": 16,
    "experience_title|start_end_date": 22,
    "experience_description": 7,
    "cert_name": 20,
    "cert_by": 26,
    "cert_on": 29,
    "cert_skills": 74,
    "cert_credential": 32,
    "recent_activity_number": 11,
    "recent_activity_text": 87

}


def source_as_row(s: PageElement) -> List[str]:
    return s.getText().split('\n')


def get_start_identifier(list_text: List[str]) -> int:
    startIdentifier = -1
    for e in list_text:
        if e == '' or e == ' ':
            startIdentifier += 1
        else:
            break
    return startIdentifier


def print_header(text):
    """ Print to the console with 5 newlines before text and dashes before and after text to mark as header"""
    dashes = "-" * 10
    break_lines = "\n" * 5
    print(break_lines + dashes + text + dashes + "\n" * 2)


def deep_compare(dict1, dict2):
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        if dict1.keys() != dict2.keys():
            return False
        return all(deep_compare(dict1[key], dict2[key]) for key in dict1)
    elif isinstance(dict1, list) and isinstance(dict2, list):
        return all(deep_compare(item1, item2) for item1, item2 in zip(dict1, dict2))
    else:
        return dict1 == dict2


def get_page_source(driver, url, scroll_times=0):
    if url != driver.current_url:
        # Open the profile URL
        driver.get(url)
        wait_for_ajax(driver)

    # Force bottom page scroll by scroll_times
    for _ in range(scroll_times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        wait_for_ajax(driver)
        # time.sleep(2)

    return BeautifulSoup(driver.page_source, "html.parser")


# returns LinkedIn profile information
def returnProfileInfo(driver: webdriver, profile_url, company_name=None, is_main_user=False):
    url = profile_url
    source = get_page_source(driver, url, 0)
    profile = {}
    info = source.find('div', class_='mt2 relative')
    name = info.find('h1', class_='break-words').get_text().strip()
    title = info.find('div', class_='text-body-medium break-words').get_text().lstrip().strip()
    connection = info.find('span', class_='dist-value')
    profile['full_name'] = name
    if company_name:
        profile['company_name'] = company_name
    profile['job_title'] = title
    if connection:
        profile['connection'] = connection.get_text().strip()
    profile['profile_url'] = profile_url

    # profile_li = source.find_all('li', class_='artdeco-list__item')

    # print_header("Profile Li(s)")
    # print(profile_li)
    # for x in profile_li:
    # alltext = source_as_row(x)
    # print(alltext)
    # si = get_start_identifier(alltext)
    # Print the start identifier and the first 20 characters of the row from the start identifier
    # print("Start Index: " + str(si), " | ", alltext[si][:20]) # For Debugging
    # print("Start Index: " + str(si), " | ", str(alltext))  # For Debugging

    functions = [
        ('education', lambda: get_profile_education(driver, profile_url)),
        ('experiences', lambda: get_profile_experiences(driver, profile_url)),
        ('certifications', lambda: get_profile_certifications(driver, profile_url)),
        ('skills', lambda: get_profile_skills(driver, profile_url)),
        ('recent_activities', lambda: get_profile_recent_activity(driver, profile_url)),
        # TODO: Get the awards
        # TODO: Get Interest (top voices, companies, groups, newsletters
    ]

    # Add mutual_connections function if not is_main_user
    if not is_main_user:
        functions.append(('mutual_connections', lambda: get_mutual_connections(driver, profile_url)))

    # Shuffle the functions to make the execution order random
    random.shuffle(functions)

    # Call each function and add the result to the profile
    for key, func in functions:
        try:
            profile[key] = func()
        except Exception as e:
            print(f"Error getting: {key} | Exception: {e}")

    # print_header("Profile")
    # print(profile)
    # print_header("")

    return profile

    # Randomizing the function calls to appear natural and avoid detection
    random.shuffle(functions)

    for key, func in functions:
        # print("Calling function to get: ", key)
        try:
            profile[key] = func()
        except Exception as e:
            print("Error getting ", key, " | ", e)


    # print_header("Profile")
    # print(profile)
    # print_header("")

    return profile


def go_to_base_employee_link(driver, employee_link):
    if employee_link != driver.current_url:
        # Open the profile URL
        driver.get(employee_link)
        wait_for_ajax(driver)
        # time.sleep(2)


def get_mutual_connections(driver, employee_link):
    go_to_base_employee_link(driver, employee_link)

    wait = get_driver_wait(driver)

    # click the link for mutual connections
    click_element_wait_retry(driver, wait, "//a[contains(@href,'facetNetwork')]", "Finding Mutual Connections Link", max_retry=0)

    # Get the text of the element that contains the connection's name
    mutual_connections = get_elements_as_list_wait_stale(wait,
                                                         "//div[contains(@class,'linked-area')]//span//a//span//span[1]",
                                                         "Getting Mutual Connection Names", max_retry=0)
    # Get the text from the elements
    mutual_connections = [getText(mc) for mc in mutual_connections]

    return mutual_connections


def get_profile_education(driver, employee_link):
    source = get_page_source(driver, employee_link)
    profile_education = []
    education = source.find_all('li')
    # print_header("Education")

    for e in education:
        row = source_as_row(e)
        si = get_start_identifier(row)
        # Print the start identifier and the first 20 characters of the row from the start identifier
        # print("Start Index: " + str(si), " | ", row[si][:40])
        # print("Start Index: " + str(si), " | ", str(row))
        if si == start_identifier_map['education']:
            text_find = ['university', 'college', 'ba']
            line = row[si][:len(row[si]) // 2]
            if any(word in line.lower().split(' ') for word in text_find):
                profile_education.append(line)
                # print_header('Education: ' + line)

    return profile_education


def get_profile_recent_activity(driver, employee_link):
    go_to_base_employee_link(driver, employee_link)
    url = driver.current_url.rstrip('/') + '/recent-activity/all/'
    driver.get(url)
    wait_for_ajax(driver)

    source = get_page_source(driver, url, 2)
    # activities = source.find_all('li')
    # Find all the links that have 'activity' in the url
    links = source.find_all('div', attrs={'data-urn': re.compile('activity')})
    found_links = ['https://www.linkedin.com/feed/update/' + link.get('data-urn') for link in links]
    texts = source.find_all('div', class_='update-components-text')
    found_text = [text.getText().strip() for text in texts]
    posted_dates = source.select(
        'div[class*="fie-impression-container"] div.relative span[class*="update-components-actor__sub-description"] span[aria-hidden="true"]')
    found_dates = [date.getText().strip() for date in posted_dates]

    # print_header("Recent Activity")
    # print("Found Links", found_links)
    # print("Found Test", found_text)

    # combine the profile activity and the found links into a mapped dict list
    profile_activity = [{'text': text,
                         'link': link,
                         'posted': convert_datetime_to_start_of_day(convert_viewed_on_to_date(date + " ago"))} for
                        text, link, date in zip(found_text, found_links, found_dates)]

    # print(f"Profile URL: {employee_link} | Recent Activity Links {profile_activity}")

    return profile_activity


def get_profile_experiences(driver, employee_link):
    # TODO: Fix this method

    go_to_base_employee_link(driver, employee_link)  # Link may need to redirect so we do this first
    url = driver.current_url.rstrip('/') + '/details/experience/'
    driver.get(url)
    wait_for_ajax(driver)

    source = BeautifulSoup(driver.page_source, "html.parser")
    exp = source.find_all('li')
    profile_experiences = []
    empty_position = {"title": "No title", 'details': [], 'skills': []}
    empty_experience = {"company_name": "No Company Name", "positions": [empty_position]}
    empty_experience2 = {"company_name": "No Company Name", "positions": []}
    experience = copy.deepcopy(empty_experience)

    # print_header("Experiences")
    for e in exp:
        row = source_as_row(e)
        si = get_start_identifier(row)
        # Print the start identifier and the first 20 characters of the row from the start identifier
        # print("Start Index: " + str(si), " | ", row[si][:40])
        # print("Start Index: " + str(si), " | ", str(row))

        if si == start_identifier_map['experience_company']:

            # We've hit a new experience. if experience variable is not empty add it to the profile experiences
            profile_experiences.append(experience)
            experience = copy.deepcopy(empty_experience)

            # print_header("Company Info Uncut")
            # print("Start Index: " + str(si), " | ", row)

            if 'yrs' in row[start_identifier_map["experience_company_2"]].split(' '):
                # This is company
                experience['company_name'] = row[si][:len(row[si]) // 2]

                # Start and End Date is here
                sesi = start_identifier_map["experience_company_2"]
                (start_date, end_date) = get_start_end_dates(row[sesi][:len(row[sesi]) // 2])

                if len(experience['positions']) == 0:
                    experience['positions'].append(copy.deepcopy(empty_position))

                last_position = experience['positions'][-1]
                last_position['start_date'] = start_date
                last_position['end_date'] = end_date


            else:
                # This is a job title
                title = row[si][:len(row[si]) // 2]
                # print_header("Job title Uncut")
                # print("Start Index: " + str(si), " | ", row[si])
                new_position = copy.deepcopy(empty_position)
                new_position['title'] = title
                # Start and End Date is here
                sesi = start_identifier_map["experience_company|start_end_date"]
                try:
                    (start_date, end_date) = get_start_end_dates(row[sesi][:len(row[sesi]) // 2])
                except IndexError:
                    start_date, end_date = None, None

                new_position['start_date'] = start_date
                new_position['end_date'] = end_date
                experience['positions'].append(new_position)

                # The company is found on the same row different index
                csi = start_identifier_map["experience_company_2"]
                experience['company_name'] = row[csi][:len(row[csi]) // 2]
                # print_header("Company Type 2 Info Uncut")
                # print("Start Index: " + str(si), "| Company Index: "+str(csi)+" | ", row[csi])



        elif si == start_identifier_map['experience_title']:
            title = row[si][:len(row[si]) // 2]
            new_position = copy.deepcopy(empty_position)
            new_position['title'] = title
            # Start and End Date is also on this line
            sesi = start_identifier_map['experience_title|start_end_date']

            try:
                start_end_line = row[sesi][:len(row[sesi]) // 2]
                # print_header("StartEnd Uncut "+start_end_line)
                start_date, end_date = get_start_end_dates(start_end_line)
                new_position['start_date'] = start_date
                new_position['end_date'] = end_date
            except IndexError:
                pass  # The index may not exist on this row

            # Add the new position to the current experience
            experience['positions'].append(new_position)

        elif si == start_identifier_map['experience_description']:
            # print_header("Details Uncut")
            # print(row[si])
            if len(experience['positions']) == 0:
                experience['positions'].append(copy.deepcopy(empty_position))

            last_position = experience['positions'][-1]

            # If details starts with "Skills:", then it is a skills not a detail
            if row[si].startswith("Skills:"):
                skills = row[si][:len(row[si]) // 2]
                last_position['skills'] = skills.split(":")[1].split(" · ")
            else:
                # TODO: Fix for when prefix is empty

                # Using the first 10 characters of the row[si] details as prefix
                prefix = row[si][:10]
                # Details equals row[si] and stops at the second index of the prefix
                details = prefix + row[si].split(prefix)[1]

                # Strip white spaces
                details = details.strip()

                # Remove entry if it contains these words by themselves or is empty
                remove_words = ['Follow', 'Connect']
                if any(word in details for word in remove_words) or details == '':
                    continue

                # details = row[si][:len(row[si]) // 2]
                last_position['details'].append(details)
        elif si == start_identifier_map['experience_title|start_end_date']:
            start_end_line = row[si][:len(row[si]) // 2]

            if len(experience['positions']) == 0:
                experience['positions'].append(copy.deepcopy(empty_position))

            last_position = experience['positions'][-1]
            start_date, end_date = get_start_end_dates(start_end_line)

            last_position['start_date'] = start_date
            last_position['end_date'] = end_date
            continue

    # Add the last experience captured
    if not deep_compare(experience, empty_experience):
        profile_experiences.append(experience)

    # Clean up empty positions from experiences that do not match the empty_positions
    profile_experiences = [
        {**exp,
         'positions': [pos for pos in exp['positions'] if len(pos) != 0 and not deep_compare(pos, empty_position)]}
        for exp in profile_experiences
    ]

    # Clean up experiences that match empty_experience2
    profile_experiences = [exp for exp in profile_experiences if not deep_compare(exp, empty_experience2)]

    return profile_experiences


def get_profile_certifications(driver, employee_link):
    go_to_base_employee_link(driver, employee_link)  # May need to redirect first

    url = driver.current_url.rstrip('/') + '/details/certifications/'
    driver.get(url)
    wait_for_ajax(driver)

    source = get_page_source(driver, url, 2)
    profile_certifications = []
    certs = source.find_all('li')
    # print_header("Certifications")
    for c in certs:
        row = source_as_row(c)
        # print(row)
        si = get_start_identifier(row)
        if si == start_identifier_map['cert_name']:
            # Reset vars
            company = None
            issued_on = None
            cert_skills = None
            credential_id = None

            name = row[si][:len(row[si]) // 2]

            cbi = start_identifier_map['cert_by']
            if cbi < len(row) and row[cbi]:
                company = row[cbi][:len(row[cbi]) // 2]

            ioi = start_identifier_map['cert_on']
            if ioi < len(row) and row[ioi]:
                issued_on = row[ioi][:len(row[ioi]) // 2]
                # Remove Issued from prefix
                issued_on = issued_on.replace("Issued ", "").strip()

            ski = start_identifier_map['cert_skills']
            if ski < len(row) and row[ski]:
                cert_skills = row[ski][:len(row[ski]) // 2]
                # remove Skills: from prefix
                cert_skills = cert_skills.replace("Skills: ", "").strip()
                cert_skills = cert_skills.split(' · ')

            cci = start_identifier_map['cert_credential']
            if cci < len(row) and row[cci]:
                credential_id = row[cci][:len(row[cci]) // 2]
                # Remove "Credential ID " from prefix
                credential_id = credential_id.replace("Credential ID ", "").strip()

            # Create a new certification dictionary and add it to the profile's certifications list.    '
            certification = {"name": name}
            if company:
                certification["company"] = company
            if issued_on:
                certification["issue_date"] = issued_on
            if cert_skills:
                certification["skills"] = cert_skills
            if credential_id:
                certification["credential_id"] = credential_id
            profile_certifications.append(certification)

    return profile_certifications


def get_profile_skills(driver, employee_link):
    go_to_base_employee_link(driver, employee_link)  # May need to redirect first

    # Skills
    url = driver.current_url.rstrip('/') + '/details/skills/'
    driver.get(url)
    wait_for_ajax(driver)

    wait = get_driver_wait(driver)

    profile_skills = []

    skills = get_elements_as_list_wait_stale(wait, "//a[contains(@data-field,'skill')]", "Getting Skills", max_retry=0)

    # Get the text from all the skills
    for each_skill in skills:
        skill_name = getText(each_skill)
        # Remove all new lines from the skill name
        skill_name = skill_name.replace('\n', '')
        # Remove leading and trailing spaces
        skill_name = skill_name.strip()

        # Split the skill name in half because LI has 2 text elements in the one we find
        skill_name = skill_name[:len(skill_name) // 2]

        skill_dict = {"name": skill_name}

        try:
            # Use the parent element to find the child element looking for endorsement
            endorsement_element = wait.until(
                lambda d: each_skill.find_element(By.XPATH, ".//ancestor::li//span[contains(text(),'endorsement')][1]"),
                'Finding Endorsement Text')
        except Exception:
            # No endorsement element found
            endorsement_element = None

        if endorsement_element:
            endorse_text = getText(endorsement_element)
            #print(f"Endorsement Text: {endorse_text}")
            skill_dict["endorsements"] = int(re.search(r'\d+', endorse_text).group())

        profile_skills.append(skill_dict)

    return profile_skills


def record_search_word_frequency(row, si, search_words, search_word_frequency=None):
    if search_word_frequency is None:
        search_word_frequency = {}

    # if any of the search words are found in any of the row items record its index in the row to the search word frequency map
    for word in search_words:
        if any(word in item for item in row):
            # Find the index in the row where the word is found
            word_index = [i for i, item in enumerate(row) if word in item][0]
            key = 'si:' + str(si) + "fi:" + str(word_index)
            # Check if key is in search_word_frequency, if not add it
            if key not in search_word_frequency:
                search_word_frequency[key] = 0
            # Increase the word frequency by 1
            search_word_frequency[key] += 1
    return search_word_frequency


def get_start_end_dates(line):
    # print("StartEnd Years Date: ", line)
    yrs_splitter = ' · '
    dates_splitter = ' - '
    if yrs_splitter in line:
        start_end = line.split(yrs_splitter)[0]
        # print("StartEnd Date: ", start_end)
        startendlist = start_end.split(dates_splitter)
        # print("StartEnd List: ", startendlist)
        start_date = startendlist[0]
        # print("Start Date: ", start_date)
        if len(startendlist) > 1:
            end_date = startendlist[1]
        else:
            end_date = "Present"
        # print("End Date: ", end_date)
    else:
        # The currently work here
        end_date = "Present"
        start_date = get_linkedin_datetime_from_text(line)

    return start_date, end_date
