import calendar
import json
import os
import random
from datetime import datetime, timedelta
from typing import Tuple
from urllib.parse import urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from cqc_lem import assets_dir
from cqc_lem.app.my_celery import app as shared_task
from cqc_lem.utilities.ai.ai_helper import get_blog_summary_post_from_ai, get_website_content_post_from_ai, \
    get_flux_image_prompt_from_ai, generate_flux1_image_from_prompt, get_runway_ml_video_prompt_from_ai, \
    create_runway_video, get_ai_linked_post_refinement
from cqc_lem.utilities.ai.ai_helper import get_thought_leadership_post_from_ai, \
    get_industry_news_post_from_ai, get_personal_story_post_from_ai, generate_engagement_prompt_post
from cqc_lem.utilities.db import get_post_type_counts, insert_planned_post, update_db_post_content, \
    get_planned_posts_for_current_week, get_last_planned_post_date_for_user, get_user_password_pair_by_id, \
    get_user_blog_url, get_user_sitemap_url, get_active_user_ids, get_planned_posts_for_next_week, PostStatus, \
    update_db_post_video_url, update_db_post_status, PostType
from cqc_lem.utilities.env_constants import API_URL_FINAL
from cqc_lem.utilities.linkedin.helper import get_my_profile
from cqc_lem.utilities.linkedin.profile import LinkedInProfile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.selenium_util import get_driver_wait_pair, quit_gracefully
from cqc_lem.utilities.utils import get_best_posting_time, create_folder_if_not_exists, save_video_url_to_dir
from requests.adapters import HTTPAdapter
from urllib3 import Retry


@shared_task.task
def auto_generate_content():
    # Get active users from DB
    active_users = get_active_user_ids()
    # For each user generate content for the next 30 days
    for user_id in active_users:
        plan_content_for_user.apply_async(kwargs={"user_id": user_id})


@shared_task.task(bind=True, reject_on_worker_lost=True, rate_limit='1/m')
def plan_content_for_user(self, user_id: int):
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
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    myprint(f"Days in Month: {days_in_month}")

    # Determine the start date as the day after the last scheduled post in planning status
    last_planned_date = get_last_planned_post_date_for_user(user_id)

    # myprint(f"Last Planned Date: {last_planned_date}")

    # Use the last planned date if it exists and it is after today
    if last_planned_date and last_planned_date.date() > datetime.now().date():
        start_date = last_planned_date + timedelta(days=1)  # Start with the next day

        # If the start date is greate than 30 days from today just skip the process
        if start_date > datetime.now() + timedelta(days=30):
            myprint(f"Content Plan | Start Date: {start_date} | >30 days out | Skipped")
            return
    else:
        start_date = datetime.now() + timedelta(days=1)  # Start with the next day
    myprint(f"Content Plan | Start Date: {start_date}")



    # Determine how many days are left in this month
    days_left_in_month = days_in_month - start_date.day

    myprint(f"Days Left in Month after Start Date: {days_left_in_month}")

    # Need on more post than days left in month
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

    # 3. Plan content across the buyer journey stages | logic: randomly select a post type and buyer journey stage for each post
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

    # Generate content plan evenly across buyer journey stages and post types
    for day in range(target_posts):  # Plan for end of this month
        # Choose a post type from the shuffled list
        post_type = post_types.pop()

        # Choose a buyer journey stage in a round-robin fashion
        stage = journey_stages[day % len(journey_stages)]

        # TODO: Delete below |  Call the helper function to create content for this post type and buyer journey stage
        # create_content(user_id, post_type, stage)

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

    video_url = None

    if post_type == "video":
        content, video_url = create_video_content(user_id, stage)
    elif post_type == "carousel":
        content = f"Content created for {post_type} in the {stage} stage. However, this is unfinished"
    else:
        content = create_text_post(user_id, stage)
        # Strip leading and ending white spaces
        content = content.strip()

    return content, video_url


def create_video_content(user_id: int, stage: str) -> tuple[str, str | None]:
    # user_email, user_password = get_user_password_pair_by_id(user_id)
    # driver, wait = get_driver_wait_pair(session_name='Create Content')
    # my_profile = get_my_profile(driver, wait, user_email, user_password)

    # Get Text Content
    text_content = create_text_post(user_id, stage)  # TODO: Should we limit this to specific post_types ???

    # Create an image prompt from the text content
    image_prompt = get_flux_image_prompt_from_ai(text_content)
    print(f"Generated AI Image Prompt: {image_prompt}")

    # Create the image from the image prompt using flux1
    image_path = generate_flux1_image_from_prompt(image_prompt)
    print(f"Generated Image From Prompt | Path: {image_path}")

    # Create a video prompt from the text content and image
    video_prompt = get_runway_ml_video_prompt_from_ai(text_content, image_prompt)
    print(f"Runway ML Video Prompt: {video_prompt}")

    # Make sure the video_prompt is less than 512 characters
    video_prompt = video_prompt[:512]

    # Create a video from the image url and video prompt using Runway ML
    video_url = create_runway_video(image_path, video_prompt)
    print(f"Generated Video URL: {video_url}")

    # quit_gracefully(driver)

    return text_content, video_url


def create_text_post(user_id: int, stage: str, post_type: str = None, user_profile: LinkedInProfile=None,
                     refine_final_post: bool = True):
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
        try:
            user_profile = get_my_profile(driver, wait, user_email, user_password)
        except Exception as e:
            myprint(f"Error getting user profile: {e}")
            # Create empty dummy user profile
            user_profile = LinkedInProfile(full_name="John Doe", job_title="Software Developer", company_name="ABC Inc.",)
        finally:
            quit_gracefully(driver)

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
            final_content = create_text_post(user_id, stage, post_type, user_profile, refine_final_post=False)
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
                final_content = create_text_post(user_id, stage, post_type, user_profile, refine_final_post=False)
        else:
            myprint("No sitemap found for this user. Generating another post type")
            # Chose another random post type that is not "website_content"
            post_types.remove("website_content")
            post_type = random.choice(post_types)
            final_content = create_text_post(user_id, stage, post_type, user_profile, refine_final_post=False)
    elif post_type == "industry_news":
        final_content = get_industry_news_post_from_ai(user_profile, stage)
    elif post_type == "personal_story":
        final_content = get_personal_story_post_from_ai(user_profile, stage)
    else:
        final_content = generate_engagement_prompt_post(user_profile, stage)

    if refine_final_post:
        final_content = get_ai_linked_post_refinement(final_content)

        # Strip leading and ending white spaces
        final_content = final_content.strip()

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

    session, headers = get_session_for_response()

    recent_posts = None

    try:
        # Make the request
        response = session.get(wp_api_url, headers=headers, timeout=10)

        # Raise an exception for HTTP errors
        response.raise_for_status()

        if response.status_code == 200:
            # Use WordPress API to get recent posts
            recent_posts = response.json()
            myprint("WordPress blog detected. Fetching posts via API...")
        else:
            # If the API is not available, fall back to web scraping
            myprint("Non-WordPress blog detected or API unavailable. Fetching posts via web scraping...")
            recent_posts = scrape_recent_posts(blog_url)

    except requests.exceptions.HTTPError as http_err:
        myprint(f"HTTP error occurred: {http_err}")
        myprint("Falling back to web scraping...")
        # In case of any request failure, fall back to web scraping
        recent_posts = scrape_recent_posts(blog_url)
    except requests.exceptions.ConnectionError as conn_err:
        myprint(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        myprint(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        myprint(f"Some other request error occurred: {req_err}")
        myprint("Falling back to web scraping...")
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

                # if post_url is a relative URL, convert it to an absolute URL
                if not post_url.startswith("http"):
                    post_url = urlparse(blog_url).scheme + "://" + urlparse(blog_url).hostname + post_url

                # post_content = title_element.get_text(strip=True)
                post_content = fetch_content(post_url)
                recent_posts.append({
                    "link": post_url,
                    "content": post_content
                })
    except requests.RequestException as e:
        myprint(f"Error fetching or parsing blog page: {e}")

    if len(recent_posts) == 0:
        myprint(f"No recent posts found on the blog page: {blog_url}")
    else:
        myprint(f"Found {len(recent_posts)} post(s) from: {blog_url}")

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
    myprint(f"Founds {len(page_urls)} URLs from sitemap {sitemap_url}")

    # 2. Filter URLs that are likely to contain shareable content
    relevant_urls = filter_relevant_urls(page_urls)
    myprint(f"Found {len(relevant_urls)} relevant URLs in the sitemap.")

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


def get_session_for_response() -> Tuple[requests.Session, dict]:
    # Set up headers to simulate a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.91 Safari/537.36',
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

    return session, headers


# Function to make a request and return parsed HTML content
def fetch_content(url):
    session, headers = get_session_for_response()

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
        url_elements = tree.findall('.//ns:url', namespaces)

        # Process URLs if present
        if url_elements:
            url_lastmod_pairs = []
            for url_element in url_elements:
                loc = url_element.find('ns:loc', namespaces).text
                lastmod = url_element.find('ns:lastmod', namespaces)
                if lastmod is not None:
                    lastmod = lastmod.text
                else:
                    lastmod = '1985-03-13'  # Default to a very old date if lastmod is not present
                url_lastmod_pairs.append((loc, lastmod))

            # Sort URLs by last modified time in descending order
            url_lastmod_pairs.sort(key=lambda x: x[1], reverse=True)
            urls = [url for url, lastmod in url_lastmod_pairs]

        # Process sub-sitemaps recursively if present (except for certain sitemap URLs)
        skip_if_contains_text = ['sitemap-misc.xml', 'post_tag-sitemap.xml', 'category-sitemap.xml', 'page-sitemap.xml']
        if sitemap_elements:
            for sitemap in sitemap_elements:
                sub_sitemap_url = sitemap.text
                if any(text in sub_sitemap_url for text in skip_if_contains_text):
                    myprint(f"Skipping sub-sitemap: {sub_sitemap_url}")
                    continue
                myprint(f"Fetching sub-sitemap: {sub_sitemap_url}")
                urls.extend(fetch_sitemap_urls(sub_sitemap_url))  # Recursive call

    except requests.RequestException as e:
        print(f"Error fetching sitemap: {e}")
    except ElementTree.ParseError as e:
        print(f"Error parsing sitemap XML: {e}")

    return urls


def filter_relevant_urls(urls: list[str], by_blog_post_check=True, max_list_size=10):
    """
    Filter the URLs to keep only those that are likely to be a blog post or contain shareable content.
    """
    keywords = ["blog", "case-study", "testimonial", "service", "news", "about"]

    relevant_urls = []
    for url in urls:
        if (by_blog_post_check and is_blog_post_combined(url)) or (
                not by_blog_post_check and any(keyword in url for keyword in keywords)):
            relevant_urls.append(url)
            if len(relevant_urls) >= max_list_size:
                break

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
        # Convert plan['post_type'] to Post Type object
        post_type = PostType[plan['post_type'].upper()]
        insert_planned_post(user_id, plan['scheduled_datetime'], post_type, plan['stage'])


@shared_task.task
def auto_create_weekly_content(user_id: int = None):
    """Creates content for the week from the planed content in the database"""

    if user_id is not None:
        myprint(f"Creating weekly content for user id: {user_id}")

    # Get the planned content for the current week or next week if today is saturday
    if datetime.now().weekday() >= 5:
        planned_posts = get_planned_posts_for_next_week(user_id)
    else:
        planned_posts = get_planned_posts_for_current_week(user_id)

    for post in planned_posts:
        user_id = post['user_id']
        post_id = post['id']
        post_type = post['post_type']
        stage = post['buyer_stage']

        # For each content create it
        content, video_url = create_content(user_id, post_type, stage)

        # Copy the video from url to our assets/video folder and store it to the database for later retrieval via api call
        if video_url:
            # Define and create assets_dir / videos
            videos_dir = os.path.join(assets_dir, 'videos', 'runwayml')
            create_folder_if_not_exists(videos_dir)
            video_file_path = save_video_url_to_dir(video_url, videos_dir)
            myprint(f"Video from url: {video_url} | Saved to: {video_file_path}")
            # Get the file name from the video file path
            video_file_name = os.path.basename(video_file_path)

            # The video url is our api prefix + 'assets?file=videos/runwayml' +  video_file_name
            api_video_url = f"{API_URL_FINAL}/assets?file_name=videos/runwayml/{video_file_name}"
            myprint(f"Video URL: {api_video_url}")

            # Update the database with the video url
            update_db_post_video_url(post_id, api_video_url)

        # Update the database with the created content
        myprint(f"Updating content for post_id: {post_id}")
        update_db_post_content(post_id, content)

        # Update the status of the post in the db to pending
        myprint(f"Updating post_id: {post_id} Status={PostStatus.PENDING}")

        update_db_post_status(post_id, PostStatus.PENDING)


def is_blog_post(url):
    parsed = urlparse(url)
    path = parsed.path.strip('/')

    # Check if the path contains typical blog indicators
    if any(segment.isdigit() for segment in path.split('/')) or len(path.split('/')) > 1:
        return True
    return False


def is_blog_post_by_metadata(url):
    try:
        content = fetch_content(url)
        # myprint(f"Fetched URL: {url}: Content: {content}")
        soup = BeautifulSoup(content, 'html.parser')

        # Look for common blog-related tags
        # if soup.find('article') or soup.find('meta', {'name': 'author'}):
        if soup.find('meta', {'name': 'author'}):
            return True
    except Exception as e:
        myprint(f"Error fetching URL: {e}")
    return False


def is_blog_post_combined(url):
    if is_blog_post(url):
        return True
    if is_blog_post_by_metadata(url):
        return True
    return False


if __name__ == '__main__':
    myprint("Generating content plan for 30 days")
    auto_generate_content()
    myprint("Creating weekly content")
    auto_create_weekly_content()
    myprint("Process finished")
