import copy
import re
import time
from typing import List

from bs4 import BeautifulSoup, PageElement
from selenium import webdriver
from utilities.date import get_linkedin_datetime_from_text

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


# Return all profiles urls of M&A employees of a certain company
def getProfileURLs(driver: webdriver, company_name):
    time.sleep(1)
    driver.get("https://www.linkedin.com/company/" + company_name + "/people/?keywords=M%26A%2CMergers%2CAcquisitions")
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    source = BeautifulSoup(driver.page_source)

    visibleEmployeesList = []
    visibleEmployees = source.find_all('a', class_='app-aware-link')
    for profile in visibleEmployees:
        if profile.get('href').split('/')[3] == 'in':
            visibleEmployeesList.append(profile.get('href'))

    invisibleEmployeeList = []
    invisibleEmployees = source.find_all('div',
                                         class_='artdeco-entity-lockup artdeco-entity-lockup--stacked-center artdeco-entity-lockup--size-7 ember-view')
    for invisibleguy in invisibleEmployees:
        title = invisibleguy.findNext('div', class_='lt-line-clamp lt-line-clamp--multi-line ember-view').contents[
            0].strip('\n').strip('  ')
        invisibleEmployeeList.append(title)

        # A profile can either be visible or invisible
        profilepiclink = ""
        visibleProfilepiclink = invisibleguy.find('img', class_='lazy-image ember-view')
        invisibleProfilepicLink = invisibleguy.find('img', class_='lazy-image ghost-person ember-view')
        if visibleProfilepiclink == None:
            profilepiclink = invisibleProfilepicLink.get('src')
        else:
            profilepiclink = visibleProfilepiclink.get('src')

        if profilepiclink not in invisibleEmployees:
            invisibleEmployeeList.append(profilepiclink)
    return (visibleEmployeesList[5:], invisibleEmployeeList)


# parses a type 2 job row
def parseType2Jobs(alltext):
    print('Job Type 2 Found')
    jobgroups = []
    company = alltext[16][:len(alltext[16]) // 2]
    totalDurationAtCompany = alltext[20][:len(alltext[20]) // 2]

    # get rest of the jobs in the same nested list
    groups = []
    count = 0
    index = 0
    for a in alltext:
        if a == '' or a == ' ':
            count += 1
        else:
            groups.append((count, index))
            count = 0
        index += 1

    numJobsInJoblist = [g for g in groups if g[0] == 21 or g[0] == 22 or g[0] == 25 or g[0] == 26]
    for i in numJobsInJoblist:
        # full time/part time case
        if 'time' in alltext[i[1] + 5][:len(alltext[i[1] + 5]) // 2].lower().split('-'):
            jobgroups.append((alltext[i[1]][:len(alltext[i[1]]) // 2], alltext[i[1] + 8][:len(alltext[i[1] + 8]) // 2]))
        else:
            jobgroups.append((alltext[i[1]][:len(alltext[i[1]]) // 2], alltext[i[1] + 4][:len(alltext[i[1] + 4]) // 2]))
    return ('type2job', company, 'no title', totalDurationAtCompany, jobgroups)


# parses a type 1 job row
def parseType1Job(alltext):
    print('Job Type 1 Found')
    jobtitle = alltext[16][:len(alltext[16]) // 2]
    company = alltext[20][:len(alltext[20]) // 2]
    duration = alltext[23][:len(alltext[23]) // 2]
    return ('type1job', company, jobtitle, duration)


def source_as_row(s: PageElement) -> List[str]:
    return s.getText().split('\n')


def get_start_identifier(list_text: List[str]) -> int:
    startIdentifier = 0
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
    if url not in driver.current_url:
        # Open the profile URL
        driver.get(url)
        time.sleep(2)

    # Force bottom page scroll twice
    for _ in range(scroll_times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    return BeautifulSoup(driver.page_source, "html.parser")


# returns LinkedIn profile information
def returnProfileInfo(driver: webdriver, employeeLink, companyName=None):
    url = employeeLink
    source = get_page_source(driver, url, 0)
    profile = {}
    info = source.find('div', class_='mt2 relative')
    name = info.find('h1', class_='text-heading-xlarge').get_text().strip()
    title = info.find('div', class_='text-body-medium break-words').get_text().lstrip().strip()
    connection = info.find('span', class_='dist-value')
    profile['full_name'] = name
    if companyName:
        profile['company_name'] = companyName
    profile['job_title'] = title
    if connection:
        profile['connection'] = connection.get_text().strip()
    profile_li = source.find_all('li', class_='artdeco-list__item')

    # print_header("Profile Li(s)")
    # print(profile_li)
    # for x in profile_li:
    # alltext = source_as_row(x)
    # print(alltext)
    # si = get_start_identifier(alltext)
    # Print the start identifier and the first 20 characters of the row from the start identifier
    # print("Start Index: " + str(si), " | ", alltext[si][:20]) # TODO: For Debugging
    # print("Start Index: " + str(si), " | ", str(alltext))  # TODO: For Debugging

    # Education
    profile['education'] = get_profile_education(driver, employeeLink)

    # Experiences
    profile['experiences'] = get_profile_experiences(driver, employeeLink)

    # Certifications
    profile['certifications'] = get_profile_certifications(driver, employeeLink)

    # Skills
    profile['skills'] = get_profile_skills(driver, employeeLink)

    # Recent Activity
    profile['recent_activity'] = get_profile_recent_activity(driver, employeeLink)

    # Get the industry - TODO: This may not be publicly visible
    # TODO: Get the mutual connections
    # TODO: Get the endorsements
    # TODO: Get the awards

    print_header("Profile")
    print(profile)
    print_header("")

    return profile


def get_profile_education(driver, employeeLink):
    url = employeeLink
    source = get_page_source(driver, url)
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


def get_profile_recent_activity(driver, employeeLink):
    url = employeeLink + '/recent-activity/all/'
    source = get_page_source(driver, url, 1)
    profile_activity = []
    activities = source.find_all('li')
    # Find all the links that have 'activity' in the url
    links = source.find_all('div',attrs={'data-urn': re.compile('activity')})
    found_links = ['https://www.linkedin.com/feed/update/' + link.get('data-urn') for link in links]

    #print_header("Recent Activity")
    #print("Found Links", found_links)

    for a in activities:
        row = source_as_row(a)
        si = get_start_identifier(row)
        # Print the start identifier and the first 20 characters of the row from the start identifier
        # print("Start Index: " + str(si), " | ", row[si][:40])
        #print("Start Index: " + str(si), " | ", str(row))
        rai = start_identifier_map['recent_activity_text']
        if si == start_identifier_map['recent_activity_number'] and rai < len(row) and row[rai]:
            activity = row[rai]
            profile_activity.append(activity)

    # combine the profile activity and the found links into a mapped dict list
    profile_activity = [{'text': activity, 'link': link} for activity, link in zip(profile_activity, found_links)]

    return profile_activity


def get_profile_experiences(driver, employeeLink):
    url = employeeLink + '/details/experience/'
    driver.get(url)
    time.sleep(2)
    source = BeautifulSoup(driver.page_source, "html.parser")
    time.sleep(1)
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
                (start_date, end_date) = get_start_end_dates(row[sesi][:len(row[sesi]) // 2])
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


def get_profile_certifications(driver, employeeLink):
    url = employeeLink + '/details/certifications/'
    source = get_page_source(driver, url, 2)
    profile_certifications = []
    certs = source.find_all('li')
    # print_header("Certifications")
    for c in certs:
        row = source_as_row(c)
        # print(row)
        si = get_start_identifier(row)

        if si == start_identifier_map['cert_name']:
            name = row[si][:len(row[si]) // 2]
            cbi = start_identifier_map['cert_by']
            company = row[cbi][:len(row[cbi]) // 2]
            ioi = start_identifier_map['cert_on']
            issued_on = row[ioi][:len(row[ioi]) // 2]
            # Remove Issued from prefix
            issued_on = issued_on.replace("Issued ", "").strip()
            ski = start_identifier_map['cert_skills']
            cert_skills = row[ski][:len(row[ski]) // 2]
            # remove Skills: from prefix
            cert_skills = cert_skills.replace("Skills: ", "").strip()
            cert_skills = cert_skills.split(' · ')
            cci = start_identifier_map['cert_credential']
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


def get_profile_skills(driver, employeeLink):
    # Skills
    url = employeeLink + '/details/skills/'
    source = get_page_source(driver, url, 5)
    profile_skills = []
    skills = source.find_all('li')
    # print_header("Skills")
    #skills_search_word_frequency = {}
    for s in skills:
        row = source_as_row(s)
        si = get_start_identifier(row)
        #print("Start Index: " + str(si), " | ", str(row))

        # TODO: Below is for debugging
        #skills_search_word_frequency = record_search_word_frequency(row, si, ['endorsements'], skills_search_word_frequency)

        if si == start_identifier_map['skills']:
            skill = row[si][:len(row[si]) // 2]
            profile_skills.append({"name": skill})
        elif si == start_identifier_map['endorsements']:
            # Find endorsements
            endorsements = row[si][:len(row[si]) // 2]
            print("Endorsements: ", endorsements)
            # extract only the number from the endorsements text
            endorsement_numbers = re.findall(r'\d+', endorsements)
            if endorsement_numbers:
                endorsements = int(endorsement_numbers[0])
                # Get the last skill if profile_skills is not empty
                if profile_skills:
                    profile_skills[-1]['endorsements'] = endorsements

    # TODO: Below is for debugging
    #print_header("Search Word Frequency")
    #print(skills_search_word_frequency)
    # TODO: Above is for debugging

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
        end_date = startendlist[1]
        # print("End Date: ", end_date)
    else:
        # The currently work here
        end_date = "Present"
        start_date = get_linkedin_datetime_from_text(line)

    return start_date, end_date
