import json

from cqc_lem.linked_in_profile import LinkedInProfile
from cqc_lem.run_automation import send_dm, post_comment, invite_to_connect
from cqc_lem.utilities.ai.ai_helper import generate_ai_response, get_ai_description_of_profile, \
    get_ai_message_refinement, summarize_recent_activity
from cqc_lem.utilities.date import convert_viewed_on_to_date
from cqc_lem.utilities.env_constants import LI_USER, LI_PASSWORD
from cqc_lem.utilities.linked_in_helper import login_to_linkedin, get_linkedin_profile_from_url, get_my_profile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import create_driver, get_driver_wait


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
