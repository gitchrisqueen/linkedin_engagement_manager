import functools
import os
from enum import Enum
from datetime import datetime, time, date

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