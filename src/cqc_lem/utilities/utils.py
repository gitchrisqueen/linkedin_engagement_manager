import functools
import json
import os
from enum import Enum
from datetime import datetime, time, date
from urllib.parse import urlparse

import boto3
import requests
import tldextract

DEBUG_LEVEL = 3

def debug_function(func):
    global DEBUG_LEVEL

    @functools.wraps(func)
    def inner_function(*args, **kwargs):
        result = None
        if DEBUG_LEVEL >= 1:
            print(f"Before calling function {func.__name__}")
        if DEBUG_LEVEL != 2:
            result = func(*args, **kwargs)
        else:
            print(f"Calling function {func.__name__}")
        if DEBUG_LEVEL > 2:
            print(f"After calling function {func.__name__}")
        return result

    return inner_function


def create_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        # myprint(f"Folder '{folder_path}' created.")
    # else:
    # myprint(f"Folder '{folder_path}' already exists.")


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


class Satisfactory(Enum):
    YES = 1
    NO = 0

def get_top_level_domain(url: str) -> str:
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"

def get_best_posting_times():
    # Determine the best time for posting based on the selected date
    best_times = {
        0: time(14, 0),  # Monday
        1: time(9, 0),  # Tuesday
        2: time(12, 0),  # Wednesday
        3: time(17, 0),  # Thursday
        4: time(23, 0),  # Friday
        5: time(7, 0),  # Saturday
        6: time(9, 0)  # Sunday
    }

    return best_times


def get_best_posting_time(selected_date: date):
    best_times = get_best_posting_times()

    # Get the best time for the selected date
    best_time = best_times[selected_date.weekday()]

    return best_time

def get_12h_format_best_time(best_time: time):
    # Format the best time to 12-hour format
    best_time_12hr = best_time.strftime("%I:%M %p")
    return best_time_12hr


def save_video_url_to_dir(video_url: str, dir_path):
    # Extract the original file name from the URL
    parsed_url = urlparse(video_url)
    file_name = os.path.basename(parsed_url.path)

    # Fetch the content from the URL
    response = requests.get(video_url)
    response.raise_for_status()  # Ensure we notice bad responses

    # Save the video to the directory with the original file name
    video_path = os.path.join(dir_path, file_name)
    with open(video_path, 'wb') as f:
        f.write(response.content)

    return video_path

def get_file_extension_from_filepath(file_path: str, remove_leading_dot: bool = False) -> str:
    basename = os.path.basename(file_path)
    file_name, file_extension = os.path.splitext(basename)
    if remove_leading_dot and file_extension.startswith("."):
        # st.info("Removing leading dot from file extension: " + file_extension)
        file_extension = file_extension[1:]

    if file_extension:
        file_extension = file_extension.lower()

    # st.info("Base Name: " + basename + " | File Name: " + file_name + " | File Extension : " + file_extension)

    return file_extension


def get_aws_session():
    return boto3.session.Session()

def get_aws_client(service_name: str, region_name:str):
    session = get_aws_session()
    return session.client(
        service_name=service_name,
        region_name=region_name
    )

def get_cloudwatch_client(region:str = 'us-east-1'):
    return get_aws_client('cloudwatch', region)

def get_aws_ssm_secret(secret_name, region_name):
    """Gets the secret value from AWS Secrets Manager"""
    client = get_aws_client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        raise e

    secret = get_secret_value_response['SecretString']
    secret_dict = json.loads(secret)

    return secret_dict
