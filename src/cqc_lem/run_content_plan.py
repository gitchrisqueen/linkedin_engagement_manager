import json
import random
from datetime import datetime, timedelta
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from cqc_lem.my_celery import app as shared_task
from cqc_lem.utilities.ai.ai_helper import get_blog_summary_post_from_ai, get_website_content_post_from_ai
from cqc_lem.utilities.ai.ai_helper import get_video_content_from_ai, get_thought_leadership_post_from_ai, \
    get_industry_news_post_from_ai, get_personal_story_post_from_ai, generate_engagement_prompt_post
from cqc_lem.utilities.db import get_post_type_counts, insert_planned_post, update_db_post_content, \
    get_planned_posts_for_current_week, get_last_planned_post_date_for_user, get_user_password_pair_by_id, \
    get_user_blog_url, get_user_sitemap_url, get_active_user_ids
from cqc_lem.utilities.linked_in_helper import get_my_profile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import get_driver_wait_pair
from cqc_lem.utilities.utils import get_best_posting_time


@shared_task.task
def generate_content():
    # Get active users from DB
    active_users = get_active_user_ids()
    # For each user generate content for the next 30 days
    for user_id in active_users:
        generate_content_for_user(user_id)


def generate_content_for_user(user_id: int):
    """
    Generate and plan content for the next 30 days based on current content representation in the database.
    Ensures a balanced distribution of post types (carousel, text, video) and buyer journey stages.
    """

    # 1. Review existing content in the database
    # Query the database to count the current representation of each post_type in the 'posts' table
    # Example: SELECT COUNT(*) FROM posts WHERE post_type = 'carousel'
    current_counts = get_post_type_counts(user_id)

    # Calculate the total posts and percentages of each type
    total_posts = sum(current_counts.values())
    percentages = {post_type: (count / total_posts) * 100 for post_type, count in current_counts.items()}

    # Log the current representation for debugging
    # myprint(f"Current Content Percentages: {percentages}")

    # 2. Determine the target distribution of post types for the next 30 days
    # Based on the percentages, calculate how many posts of each type are needed to balance the content

    # Determine how many days are in this month
    days_in_month = datetime.now().replace(day=1).replace(month=datetime.now().month + 1,
                                                          day=1) - datetime.now().replace(day=1)
    days_in_month = days_in_month.days

    # myprint(f"Days in Month: {days_in_month}")

    # Determine the start date as the day after the last scheduled post in planning status
    last_planned_date = get_last_planned_post_date_for_user(user_id)

    # myprint(f"Last Planned Date: {last_planned_date}")

    if last_planned_date:
        start_date = last_planned_date + timedelta(days=1)  # Start with the next day
    else:
        start_date = datetime.now() + timedelta(days=1)  # Start with the next day

    # myprint(f"Start Date: {start_date}")

    # Determine how many days are left in this month
    days_left_in_month = days_in_month - start_date.day +1 # dont cont today

    # myprint(f"Days Left in Month after Start Date: {days_left_in_month}")

    # 4. Create content for each post type and buyer journey stage
    # Example logic: randomly select a post type and buyer journey stage for each post
    target_posts = days_left_in_month + 1  # Total posts till the end of the month

    # myprint(f"Target Posts: {target_posts}")

    needed_posts = {post_type: target_posts // 3 for post_type in ['carousel', 'text', 'video']}

    # myprint(f"Needed Posts: {needed_posts}")

    # Ensure all post types are present in current_counts and percentages
    for post_type in ['carousel', 'text', 'video']:
        if post_type not in percentages:
            percentages[post_type] = 0.0

    # myprint(f"Updated Content Percentages: {percentages}" )

    # Loop until the total needed posts equals the target posts
    while sum(needed_posts.values()) != target_posts:
        max_key = get_max_key(percentages)
        min_key = get_min_key(percentages)

        # Adjust the counts
        if sum(needed_posts.values()) < target_posts:
            needed_posts[min_key] += 1
        else:
            needed_posts[max_key] -= 1

        # Recalculate percentages
        total_posts = sum(needed_posts.values())
        for post_type in percentages:
            percentages[post_type] = (needed_posts[post_type] / total_posts) * 100

    # Output the final needed_posts and percentages
    # myprint(f"Final Needed Posts: {needed_posts}")
    # myprint(f"Final Percentages: {percentages}")

    # 3. Plan content across the buyer journey stages
    # Define buyer journey stages: Awareness, Consideration, Decision
    journey_stages = ["awareness", "consideration", "decision"]
    daily_plan = []

    # Shuffle the journey stages to ensure a random order
    random.shuffle(journey_stages)

    # Create a list of post types based on needed_posts
    post_types = []
    for post_type, count in needed_posts.items():
        post_types.extend([post_type] * count)

    # Shuffle the post types to ensure a random order
    random.shuffle(post_types)

    # Generate content evenly across buyer journey stages and post types
    for day in range(target_posts):  # Plan for end of this month
        # Choose a post type from the shuffled list
        post_type = post_types.pop()

        # Choose a buyer journey stage in a round-robin fashion
        stage = journey_stages[day % len(journey_stages)]

        # Call the helper function to create content for this post type and buyer journey stage
        create_content(user_id, post_type, stage)

        # Add this post to the daily plan
        post_date = start_date + timedelta(days=day)

        # Get the best time for the selected date
        post_time = get_best_posting_time(post_date.date())

        # Combine the selected date and time into a single datetime object
        scheduled_datetime = datetime.combine(post_date, post_time)

        daily_plan.append({
            "scheduled_datetime": scheduled_datetime,
            "post_type": post_type,
            "stage": stage
        })

        # Update the needed_posts count for the selected post type
        needed_posts[post_type] -= 1

    # Log the final content plan for the next 30 days
    # myprint(f"Generated content plan: {daily_plan}")
    myprint(f"Generated content plan")

    # 4. Save the daily plan to the database for tracking and scheduling
    save_content_plan(user_id, daily_plan)


# Function to find the key with the highest value in a dictionary
def get_max_key(d):
    return max(d, key=d.get)


# Function to find the key with the lowest value in a dictionary
def get_min_key(d):
    return min(d, key=d.get)


def create_content(user_id: int, post_type: str, stage: str):
    """Create content based on the specified post type and buyer journey stage."""

    if post_type == "video":
        #content = create_video_content(user_id, stage) # TODO: Find a way to implement this
        content = f"Content created for {post_type} in the {stage} stage. However, this is unfinished"
    elif post_type == "carousel":
        content = f"Content created for {post_type} in the {stage} stage. However, this is unfinished"
    else:
        content = create_text_post(user_id, stage)
        # Strip leading and ending white spaces
        content = content.strip()

    return content


def create_video_content(user_id: int, stage: str):
    user_email, user_password = get_user_password_pair_by_id(user_id)
    driver, wait = get_driver_wait_pair(session_name='Create Content')
    my_profile = get_my_profile(driver, wait, user_email, user_password)

    content = get_video_content_from_ai(my_profile, stage)

    driver.quit()

    return content


def create_text_post(user_id: int, stage: str, post_type: str = None, user_profile=None):
    """
    Generate a text post for LinkedIn based on the user's profile, blog, or website content.

    Parameters:
    - user_id: ID of user to grab user profile
    - stage: Buyer journey stage for the post.

    Returns:
    - str: Generated text post content.
    """

    final_content = None

    # Define possible post types
    post_types = ["thought_leadership", "blog_summary", "website_content", "industry_news", "personal_story",
                  "engagement_prompt"]

    if post_type is None:
        # Randomly select a post type
        post_type = random.choice(post_types)

    if user_profile is None:
        user_email, user_password = get_user_password_pair_by_id(user_id)
        driver, wait = get_driver_wait_pair(session_name='Create Text Post')
        user_profile = get_my_profile(driver, wait, user_email, user_password)
        driver.quit()

    # Generate the post based on the selected type
    myprint(f"Creating text post of type: {post_type} for stage: {stage}")
    if post_type == "thought_leadership":
        final_content = get_thought_leadership_post_from_ai(user_profile, stage)
    elif post_type == "blog_summary":
        # Get the users blog url
        user_main_blog_url = get_user_blog_url(user_id)
        blog_post_url, blog_post_content = get_main_blog_url_content(user_main_blog_url)
        if blog_post_url and blog_post_content:
            process_selected_post(blog_post_url, blog_post_content)
            final_content = get_blog_summary_post_from_ai(blog_post_url, blog_post_content, user_profile, stage)
        else:
            myprint("No blog post found for this user. Generating another post type")
            # Chose another random post type that is not "blog_summary"
            post_types.remove("blog_summary")
            post_type = random.choice(post_types)
            final_content = create_text_post(user_id, stage, post_type, user_profile)
    elif post_type == "website_content":
        # Get the users sitemap url
        sitemap_url = get_user_sitemap_url(user_id)
        if sitemap_url:
            content = generate_website_content_post(sitemap_url, user_profile, stage)
            if content:
                final_content = content
            else:
                myprint("No relevant content found in the sitemap. Generating another post type")
                # Chose another random post type that is not "website_content"
                post_types.remove("website_content")
                post_type = random.choice(post_types)
                final_content = create_text_post(user_id, stage, post_type, user_profile)
        else:
            myprint("No sitemap found for this user. Generating another post type")
            # Chose another random post type that is not "website_content"
            post_types.remove("website_content")
            post_type = random.choice(post_types)
            final_content = create_text_post(user_id, stage, post_type, user_profile)
    elif post_type == "industry_news":
        final_content = get_industry_news_post_from_ai(user_profile, stage)
    elif post_type == "personal_story":
        final_content = get_personal_story_post_from_ai(user_profile, stage)
    else:
        final_content = generate_engagement_prompt_post(user_profile, stage)

    return final_content


def get_main_blog_url_content(blog_url):
    """
    Retrieve recent posts from a blog, randomly select one, and send the post content to another function.

    Parameters:
    - blog_url (str): URL of the blog's homepage.

    Returns:
    - None
    """
    # Check if the blog is a WordPress site by trying the REST API
    wp_api_url = f"{blog_url.rstrip('/')}/wp-json/wp/v2/posts"

    try:
        response = requests.get(wp_api_url, timeout=5)
        response.raise_for_status()  # Check if the request was successful
        if response.status_code == 200:
            # Use WordPress API to get recent posts
            recent_posts = response.json()
            myprint("WordPress blog detected. Fetching posts via API...")
        else:
            # If the API is not available, fall back to web scraping
            myprint("Non-WordPress blog detected or API unavailable. Fetching posts via web scraping...")
            recent_posts = scrape_recent_posts(blog_url)
    except requests.RequestException:
        myprint("Error fetching blog posts via API. Falling back to web scraping...")
        # In case of any request failure, fall back to web scraping
        recent_posts = scrape_recent_posts(blog_url)

    # Randomly select one post from recent posts
    if recent_posts:
        selected_post = random.choice(recent_posts)
        # myprint(f"Randomly selected post")
        post_content = selected_post.get("content", "")
        try:
            # If post_content is a string, try to parse it as JSON
            if isinstance(post_content, str):
                post_content = json.loads(post_content)

            # Check if post_content is a dictionary and contains the "rendered" key
            if isinstance(post_content, dict) and "rendered" in post_content:
                post_content = post_content["rendered"]

        except (json.JSONDecodeError, TypeError):
            # If JSON decoding fails or another error occurs, return None
            myprint(f"Error parsing post content: {post_content}")

        # myprint(f"Randomly selected post content: {post_content}")
        post_url = selected_post.get("link", blog_url)

        return post_url, post_content
    else:
        myprint("No recent posts found or unable to fetch posts.")
        return None, None


def scrape_recent_posts(blog_url):
    """
    Fallback method to scrape recent posts from a non-WordPress blog.

    Parameters:
    - blog_url (str): URL of the blog's homepage.

    Returns:
    - list: List of dictionaries containing 'content' and 'link' for each post.
    """
    recent_posts = []
    try:
        content = fetch_content(blog_url)

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")

        # Attempt to find recent post links by typical blog post selectors
        # Adjust these selectors based on the structure of the blog
        for article in soup.select("article"):
            title_element = article.find("a", href=True)
            if title_element:
                post_url = title_element["href"]
                post_content = title_element.get_text(strip=True)

                myprint(f"Found post content: {post_content}")
                recent_posts.append({
                    "link": post_url,
                    "content": post_content
                })
    except requests.RequestException as e:
        myprint(f"Error fetching or parsing blog page: {e}")

    if len(recent_posts) == 0:
        myprint(f"No recent posts found on the blog page: {blog_url}")

    return recent_posts


def process_selected_post(url, content):
    """
    Process the selected post's content and URL.

    Parameters:
    - content (str): The text content of the selected post.
    - url (str): The URL of the selected post.

    Returns:
    - None
    """
    if not url:
        url = "Could not retrieve URL"
    if not content:
        content = "Could not retrieve content"

    # If content is a list joint it by space
    if isinstance(content, list):
        content = " ".join(content)

    # Placeholder for whatever processing needs to be done
    myprint(f"Selected Post URL: {url}")
    if content:
        myprint(f"Selected Post Content: {content[:200]}...")  # Print the first 200 characters for preview
    else:
        myprint("Selected Post Content: None")


def generate_website_content_post(sitemap_url, linked_user_profile, stage: str):
    """
    Generate a post based on content found on the user's website using their sitemap url catered to readers in the desired buyers journey stage.
    Scrapes or retrieves key points from the website's sitemap.
    """

    # 1. Fetch and parse the sitemap XML
    page_urls = fetch_sitemap_urls(sitemap_url)

    # 2. Filter URLs that are likely to contain shareable content
    relevant_urls = filter_relevant_urls(page_urls)

    # 3. Randomly select a URL to gather content from
    if relevant_urls:
        content = None
        selected_url = None
        attempts = 3
        while attempts > 0 and relevant_urls:
            selected_url = random.choice(relevant_urls)
            title, content = extract_page_content(selected_url)
            if content:
                break
            else:
                relevant_urls.remove(selected_url)
                attempts -= 1
        if content is not None:
            # 4. Generate a social media post based on the extracted content
            social_media_post = get_website_content_post_from_ai(content, selected_url, linked_user_profile, stage)
            return social_media_post
        else:
            myprint("No content extracted from the selected URL.")
            return None
    else:
        myprint("No relevant URLs found in the sitemap.")
        return None


# Function to make a request and return parsed HTML content
def fetch_content(url):
    # Set up headers to simulate a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    # Configure retries to handle intermittent network issues gracefully
    retry_strategy = Retry(
        total=5,  # Retry 5 times
        backoff_factor=1,  # Wait progressively longer each time
        status_forcelist=[403, 429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["HEAD", "GET"]
    )

    # Mount session with the retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    content = None

    try:
        # Make the request
        response = session.get(url, headers=headers, timeout=10)

        # Raise an exception for HTTP errors
        response.raise_for_status()

        content = response.content

    except requests.exceptions.HTTPError as http_err:
        myprint(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        myprint(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        myprint(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        myprint(f"Some other request error occurred: {req_err}")

    # Return the content
    return content


def fetch_sitemap_urls(sitemap_url):
    """
    Fetch and parse the sitemap XML to get a list of URLs, including any sub-sitemaps.

    Parameters:
    - sitemap_url (str): The URL of the main sitemap.

    Returns:
    - list: A list of URLs from the sitemap and any sub-sitemaps.
    """
    urls = []
    try:

        content = fetch_content(sitemap_url)

        # Parse the XML content of the sitemap
        tree = ElementTree.fromstring(content)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        # Check if the sitemap contains sub-sitemaps or URLs
        sitemap_elements = tree.findall('.//ns:sitemap/ns:loc', namespaces)
        url_elements = tree.findall('.//ns:url/ns:loc', namespaces)

        # Process URLs if present
        if url_elements:
            urls.extend([element.text for element in url_elements])

        # Process sub-sitemaps recursively if present
        if sitemap_elements:
            for sitemap in sitemap_elements:
                sub_sitemap_url = sitemap.text
                print(f"Fetching sub-sitemap: {sub_sitemap_url}")
                urls.extend(fetch_sitemap_urls(sub_sitemap_url))  # Recursive call

    except requests.RequestException as e:
        print(f"Error fetching sitemap: {e}")
    except ElementTree.ParseError as e:
        print(f"Error parsing sitemap XML: {e}")

    return urls


def filter_relevant_urls(urls):
    """
    Filter the URLs to keep only those that are likely to contain shareable content.
    """
    keywords = ["blog", "case-study", "testimonial", "service", "news", "about"]
    relevant_urls = [url for url in urls if any(keyword in url for keyword in keywords)]

    return relevant_urls


def extract_page_content(page_url):
    """
    Extract key content from the page, such as the title, main points, or summary.
    """
    try:
        content = fetch_content(page_url)

        # Parse the HTML content
        soup = BeautifulSoup(content, "html.parser")

        # Extract the page title
        title = soup.title.string if soup.title else "Untitled"

        # Extract the main content (adjust selectors based on typical page structure)
        # Common areas to look at: main headings, paragraphs, meta descriptions
        main_content = []
        for p in soup.select("p"):
            if len(p.get_text(strip=True)) > 50:  # Skip very short paragraphs
                main_content.append(p.get_text(strip=True))

        return title, main_content
    except requests.RequestException as e:
        myprint(f"Error fetching page content: {e}")
        return None, None


def save_content_plan(user_id: int, daily_plan: list[dict]):
    """Save the planned content schedule to the database."""
    # Insert the 'daily_plan' into a database table for future reference and scheduling
    for plan in daily_plan:
        insert_planned_post(user_id, plan['scheduled_datetime'], plan['post_type'], plan['stage'])


@shared_task.task
def create_weekly_content():
    """Creates content for the week from the planed content in the database"""

    # Get the planned content for the current week
    planned_posts = get_planned_posts_for_current_week()

    for post in planned_posts:
        user_id = post['user_id']
        post_id = post['id']
        post_type = post['post_type']
        stage = post['buyer_stage']

        # For each content create it
        content = create_content(user_id, post_type, stage)

        # Update the database with the created content
        myprint(f"Updating post content for post_id: {post_id}")
        update_db_post_content(post_id, content)


if __name__ == '__main__':
    myprint("Generating content plan for 30 days")
    generate_content()
    myprint("Creating weekly content")
    create_weekly_content()
    myprint("Process finished")
