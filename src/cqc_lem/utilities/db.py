import json
import os
from datetime import datetime, timedelta
from enum import StrEnum

import boto3
import mysql.connector
from dotenv import load_dotenv
from mysql.connector import errorcode

from cqc_lem.utilities.linkedin.profile import LinkedInProfile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.utils import get_top_level_domain

# Load .env file
load_dotenv()

MAX_WAIT_RETRY = 3
WAIT_TIMEOUT = 3

# Retrieve MySQL connection details from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')


def get_secret(secret_name, region_name):
    """Gets the secret value from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(
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


def get_db_connection():
    """Establishes a connection to the MySQL database and returns the connection object.

    Raises:
        mysql.connector.Error: If there is an error connecting to the database.
    """

    global MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD,MYSQL_DATABASE

    # if MYSQL_USER and MYSQL_PASSWORD are empty try to get it from AWS using get_secret function
    if not MYSQL_USER or not MYSQL_PASSWORD:
        secret_dict = get_secret(os.getenv('AWS_SECRET_NAME'), os.getenv('AWS_REGION'))
        MYSQL_USER = secret_dict['username']
        MYSQL_PASSWORD = secret_dict['password']

    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )


class PostType(StrEnum):
    TEXT = 'text'
    CAROUSEL = 'carousel'
    VIDEO = 'video'


class PostStatus(StrEnum):
    PLANNING = 'planning'
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    SCHEDULED = 'scheduled'
    POSTED = 'posted'


# Enum for log actions types
class LogActionType(StrEnum):
    COMMENT = 'comment'
    DM = 'dm'
    REPLY = 'reply'
    POST = 'post'
    ENGAGED = 'engaged'


# ENum for log result options
class LogResultType(StrEnum):
    SUCCESS = 'success'
    FAILURE = 'failure'


def store_cookies(user_email: str, cookies: list[dict]):
    connection = get_db_connection()
    cursor = connection.cursor()

    user_id = get_user_id(user_email)

    for cookie in cookies:
        try:
            cursor.execute("""
                INSERT INTO cookies (name, value, domain, path, expiry, secure, http_only, user_id)
                VALUES (%s, %s, %s, %s, FROM_UNIXTIME(%s), %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    value = VALUES(value),
                    path = VALUES(path),
                    expiry = VALUES(expiry),
                    secure = VALUES(secure),
                    http_only = VALUES(http_only)
               
            """, (

                cookie['name'],
                cookie['value'],
                cookie['domain'],
                cookie['path'],
                cookie['expiry'] if 'expiry' in cookie else None,
                cookie['secure'],
                cookie['httpOnly'],
                user_id
            ))
        except mysql.connector.Error as err:
            myprint(f"Could not add cookie to database | Error: {err}")

    connection.commit()
    cursor.close()
    connection.close()


def get_cookies(url: str, user_email: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Extract the top-level domain from the URL
    tld = get_top_level_domain(url)

    try:
        cursor.execute("""
            SELECT c.name, c.value, c.domain, c.path, UNIX_TIMESTAMP(c.expiry) AS expiry, c.secure, c.http_only
            FROM cookies c
            JOIN users u ON c.user_id = u.id
            WHERE c.domain LIKE %s AND u.email = %s
        """, (f"%{tld}%", user_email))

        cookies = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get cookies from DB | Error: {err}")
        cookies = None
    finally:
        cursor.close()
        connection.close()

    return cookies


def add_user(email: str, password: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, password))
        connection.commit()
    except mysql.connector.Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            print(f"User with email {email} already exists.")
        else:
            print(f"An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()


def add_user_with_access_token(email: str, linked_sub_id: str, access_token: str, access_token_expires_in: str,
                               refresh_token: str = None,
                               refresh_token_expires_in: str = None):
    connection = get_db_connection()
    cursor = connection.cursor()

    access_token_created_at = datetime.now()

    if refresh_token is not None:
        refresh_token_created_at = datetime.now()
    else:
        refresh_token_created_at = None

    try:
        cursor.execute("""INSERT INTO users (email, linked_sub_id, access_token, access_token_expires_in, access_token_created_at, refresh_token, refresh_token_expires_in, refresh_token_created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
                linked_sub_id = VALUES(linked_sub_id),
                access_token = VALUES(access_token),
                access_token_expires_in = VALUES(access_token_expires_in),
                access_token_created_at = VALUES(access_token_created_at),
                refresh_token = VALUES(refresh_token),
                refresh_token_expires_in = VALUES(refresh_token_expires_in),
                refresh_token_created_at = VALUES(refresh_token_created_at)
                
        """, (
            email,
            linked_sub_id,
            access_token, access_token_expires_in, access_token_created_at,
            refresh_token, refresh_token_expires_in, refresh_token_created_at))
        connection.commit()
    except mysql.connector.Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            print(f"User with email {email} already exists.")
        else:
            print(f"An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()


def get_user_linked_sub_id(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT linked_sub_id FROM users WHERE id = %s", (user_id,))

        linked_sub_id = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user linked sub id | Error: {err}")
        linked_sub_id = None
    finally:
        cursor.close()
        connection.close()

    return linked_sub_id['linked_sub_id'] if linked_sub_id else None


def get_user_access_token(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT access_token FROM users WHERE id = %s", (user_id,))
        # TODO: Add where clause to only return non-expired tokens ????

        access_token = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user access token | Error: {err}")
        access_token = None
    finally:
        cursor.close()
        connection.close()

    return access_token['access_token'] if access_token else None


def get_user_id(email: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))

        user_id = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user id | Error: {err}")
        user_id = None
    finally:
        cursor.close()
        connection.close()

    return user_id['id'] if user_id else None


def insert_post(email: str, content: str, scheduled_time, post_type: PostType) -> bool:
    user_id = get_user_id(email)

    if not user_id:
        print(f"User with email {email} not found.")
        return False

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO posts (content, scheduled_time, post_type, user_id)
            VALUES (%s, %s, %s, %s)
        """, (content, scheduled_time, post_type.value, user_id))

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as e:
        success = False
        print(f"Count not insert post. An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()

    return success


def insert_planned_post(user_id: int, scheduled_time, post_type: PostType, buyer_stage: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO posts (scheduled_time, post_type, user_id, buyer_stage, status, content)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (scheduled_time, post_type.value, user_id, buyer_stage, PostStatus.PLANNING.value, 'TBD'))

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as e:
        success = False
        print(f"Count not insert planned post. An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()
    return success


def update_db_post(content: str, video_url: str, scheduled_time: str, post_type: PostType, post_id: int,
                   post_status: PostStatus) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "UPDATE posts SET content = %s, video_url = %s, scheduled_time =%s, post_type = %s, status = %s WHERE id = %s",
            (content, video_url, scheduled_time, post_type.value, post_status.value, post_id)
        )

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as e:
        success = False
        print(f"Count not update post. An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()

    return success


def update_db_post_content(post_id: int, content: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "UPDATE posts SET content = %s WHERE id = %s",
            (content, post_id)
        )

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as e:
        success = False
        print(f"Count not update post content. An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()

    return success


def update_db_post_video_url(post_id: int, video_url: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "UPDATE posts SET video_url = %s WHERE id = %s",
            (video_url, post_id)
        )

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as e:
        success = False
        print(f"Count not update post video url. An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()

    return success


def update_db_post_status(post_id: int, post_status: PostStatus) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    # TODO: Why Enum doesnt work inside this function (have to convert to string first but why) ????
    status_str = "posted"
    try:
        status_str = post_status.value
    except Exception:
        myprint(f"Error converting post_status to string: {post_status}")

    try:
        cursor.execute(
            """UPDATE posts SET status = %s WHERE id = %s""",
            (status_str, post_id)
        )

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as e:
        success = False
        print(f"Count not update post status. An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()

    return success


def get_posts(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, content, video_url, scheduled_time, post_type, status FROM posts WHERE user_id = %s ORDER BY scheduled_time asc",
            (user_id,))
        posts = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get posts for user id: {user_id} | Error: {err}")
        posts = None
    finally:
        cursor.close()
        connection.close()

    return posts


def get_posted_posts(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, content, scheduled_time, post_type, status FROM posts WHERE user_id = %s AND status = 'posted' ORDER BY scheduled_time asc",
            (user_id,))

        posts = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get posted posts for user id: {user_id} | Error: {err}")
        posts = None
    finally:
        cursor.close()
        connection.close()

    return posts


def get_post_by_email(email: str):
    user_id = get_user_id(email)

    if not user_id:
        print(f"User with email {email} not found.")
        return

    return get_posts(user_id)


def get_post_content(post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT content FROM posts WHERE id = %s", (post_id,))

        post = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get post content for post id: {post_id} | Error: {err}")
        post = False
    finally:
        cursor.close()
        connection.close()

    return post['content'] if post else None


def get_post_video_url(post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT video_url FROM posts WHERE id = %s", (post_id,))

        post = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get post video url for post id: {post_id} | Error: {err}")
        post = False
    finally:
        cursor.close()
        connection.close()

    return post['video_url'] if post else None


def get_ready_to_post_posts(pre_post_time: datetime = None) -> list:
    """Query the database for any pending posts that are scheduled to post now or earlier"""

    now = datetime.now()
    if pre_post_time is None:
        # Get time for 20 minutes after now
        pre_post_time = now + timedelta(minutes=20)

    yesterday = now - timedelta(days=1)

    myprint(f"Getting post between : {yesterday} and {pre_post_time}")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Get posts that have scheduled time between 24 hours ago and the next 20 minutes
        cursor.execute(
            """SELECT p.id, p.scheduled_time, p.user_id 
                FROM posts AS p
                WHERE status = 'approved' AND scheduled_time BETWEEN %s AND %s 
                ORDER BY scheduled_time ASC 
                """,
            (yesterday, pre_post_time,))
        posts = cursor.fetchall()
        # Print the id's ready to post
        myprint(f"Posts ready to post: {[post[0] for post in posts]}")
    except mysql.connector.Error as err:
        myprint(f"Could not get ready to post posts| Error: {err}")
        posts = None
    finally:
        cursor.close()
        connection.close()

    return posts


def get_user_password_pair_by_id(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT email, password FROM users WHERE id = %s", (user_id,))

        user_password_pair = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user password pair for user id: {user_id} | Error: {err}")
        user_password_pair = None
    finally:
        cursor.close()
        connection.close()

    if user_password_pair:
        return user_password_pair['email'], user_password_pair['password']
    else:
        return None, None


def get_active_user_password_pairs():
    connection = get_db_connection()
    cursor = connection.cursor()

    user_password_pairs = []

    active_users = get_active_user_ids()

    for user_id in active_users:
        email, password = get_user_password_pair_by_id(user_id)
        if email and password:
            user_password_pairs.append([email, password])

    return user_password_pairs


def add_linkedin_profile(profile: LinkedInProfile):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO profiles (profile_url, email, data) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                    profile_url = VALUES(profile_url),
                    email = VALUES(email),
                    data = VALUES(data)
            """,
                       (str(profile.profile_url), profile.email, profile.model_dump_json()))

        connection.commit()
        success = True
    except mysql.connector.Error as err:
        myprint(f"Could not add linkedin profile | Error: {err}")
        success = False
    finally:
        cursor.close()
        connection.close()
    return success


def get_linked_in_profile_by_url(profile_url: str, updated_less_than_days_ago: int = 1):
    connection = get_db_connection()
    cursor = connection.cursor()

    profile_url_without_end_slash = profile_url.rstrip('/')
    profile_url_with_end_slash = profile_url_without_end_slash + '/'

    try:
        cursor.execute(
            "SELECT data FROM profiles WHERE (profile_url = %s or profile_url = %s) AND updated_at > NOW() - INTERVAL %s DAY",
            (profile_url_with_end_slash, profile_url_without_end_slash, updated_less_than_days_ago))
        profile_data = cursor.fetchone()
    except mysql.connector.Error as err:
        profile_data = None
        myprint(f"Could not get linkedin profile by url | Error: {err}")
    finally:
        cursor.close()
        connection.close()

    return profile_data


def get_linked_in_profile_by_email(profile_email: str, updated_less_than_days_ago: int = 1):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT data FROM profiles WHERE email = %s AND updated_at > NOW() - INTERVAL %s DAY",
                       (profile_email, updated_less_than_days_ago))
        profile_data = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get linkedin profile data by email | Error: {err}")
        profile_data = None
    finally:
        cursor.close()
        connection.close()

    return profile_data


def remove_linked_in_profile_by_url(profile_url: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM profiles WHERE profile_url = %s", (profile_url,))
        connection.commit()
        success = True
    except mysql.connector.Error as err:
        myprint(f"Could not remove linkedin profile by url | Error: {err}")
        success = False
    finally:
        cursor.close()
        connection.close()
    return success


def remove_linked_in_profile_by_email(profile_email: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM profiles WHERE email = %s", (profile_email,))
        connection.commit()
        success = True
    except mysql.connector.Error as err:
        myprint(f"Could not remove linkedin profile by url | Error: {err}")
        success = False
    finally:
        cursor.close()
        connection.close()
    return success


def get_post_type_counts(user_id: int):
    """Query the database to get the count of each post_type in the 'posts' table for the given user id."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT post_type, COUNT(*) AS count FROM posts WHERE user_id = %s GROUP BY post_type",
                       (user_id,))
        post_counts = {row['post_type']: row['count'] for row in cursor.fetchall()}
    except mysql.connector.Error as err:
        myprint(f"Could not get post type counts | Error: {err}")
        post_counts = 0
    finally:
        cursor.close()
        connection.close()

    return post_counts


def get_planned_posts_for_current_week(user_id: int = None):
    """Query the database to get the planned content for the current week."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    where_clause = ''
    if user_id:
        where_clause = f"AND user_id = {user_id}"

    try:
        cursor.execute(
            f"SELECT user_id, id, post_type, buyer_stage FROM posts WHERE status = 'planning' {where_clause} AND WEEK(scheduled_time) = WEEK(NOW())")
        planned_content = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get planned post for current week | Error: {err}")
        planned_content = None
    finally:
        cursor.close()
        connection.close()

    return planned_content


def get_planned_posts_for_next_week(user_id: int = None):
    """Query the database to get the planned content for the next week."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    where_clause = ''
    if user_id:
        where_clause = f"AND user_id = {user_id}"

    try:
        cursor.execute(
            f"SELECT user_id, id, post_type, buyer_stage FROM posts WHERE status = 'planning' {where_clause} AND WEEK(scheduled_time) = WEEK(NOW()) +1")
        planned_content = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get planned post for next week | Error: {err}")
        planned_content = None
    finally:
        cursor.close()
        connection.close()

    return planned_content


def get_last_planned_post_date_for_user(user_id: int):
    """Query the database to get the last planned post date for the given user."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT MAX(scheduled_time) AS last_planned_date FROM posts WHERE user_id = %s AND status != 'rejected'",
            (user_id,))
        last_planned_date = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get last planned post date for user | Error: {err}")
        last_planned_date = None
    finally:
        cursor.close()
        connection.close()

    return last_planned_date[0] if last_planned_date else None


def get_user_blog_url(user_id: int):
    """Query the database to get the blog URL for the given user."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT blog_url FROM users WHERE id = %s", (user_id,))
        blog_url = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user blog url | Error: {err}")
        blog_url = None
    finally:
        cursor.close()
        connection.close()

    return blog_url[0] if blog_url else None


def get_user_sitemap_url(user_id: int):
    """Query the database to get the sitemap URL for the given user."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT sitemap_url FROM users WHERE id = %s", (user_id,))
        sitemap_url = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user sitemap url | Error: {err}")
        sitemap_url = None
    finally:
        cursor.close()
        connection.close()

    return sitemap_url[0] if sitemap_url else None


def get_active_user_ids():
    """Query the database to get the user ids of active users."""
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # cursor.execute("SELECT id FROM users WHERE active = 1") # TODO:  Update this when you have a way to see who is active (timestamp of login or paid ???)
        cursor.execute("SELECT id FROM users ")
        active_user_ids = [row[0] for row in cursor.fetchall()]
    except mysql.connector.Error as err:
        myprint(f"Could not get active user ids | Error: {err}")
        active_user_ids = None
    finally:
        cursor.close()
        connection.close()

    return active_user_ids


def insert_new_log(user_id: int, action_type: LogActionType, result: LogResultType, post_id: int = None,
                   post_url: str = None, message: str = None):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO logs (user_id, action_type, post_id, post_url, message, result)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, action_type.value, post_id, post_url, message, result.value))

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as err:
        myprint(f"Could not insert new log | Error: {err}")
        success = False
    finally:
        cursor.close()
        connection.close()

    return success


def has_user_commented_on_post_url(user_id: int, post_url: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT COUNT(*) FROM logs WHERE user_id = %s AND post_url = %s AND action_type = %s AND result = %s",
            (user_id, post_url, LogActionType.COMMENT.value, LogResultType.SUCCESS.value))
        count = cursor.fetchone()[0]
    except mysql.connector.Error as err:
        myprint(f"Could not determine if user commented on post url | Error: {err}")
        count = 0
    finally:
        cursor.close()
        connection.close()

    return count > 0


def get_post_url_from_log_for_user(user_id: int, post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""SELECT post_url FROM logs 
            WHERE user_id = %s AND post_id = %s AND action_type = %s AND result = %s  
            ORDER BY created_at DESC 
            LIMIT 1""",
                       (user_id, post_id, LogActionType.POST.value, LogResultType.SUCCESS.value))
        post_url = cursor.fetchone()[0]
    except mysql.connector.Error as err:
        myprint(f"Could not get post url from log for user | Error: {err}")
        post_url = None
    finally:
        cursor.close()
        connection.close()

    return post_url


def get_post_message_from_log_for_user(user_id: int, post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""SELECT message FROM logs 
            WHERE user_id = %s AND post_id = %s AND action_type = %s AND result = %s
            ORDER BY created_at DESC 
            LIMIT 1""",
                       (user_id, post_id, LogActionType.POST.value, LogResultType.SUCCESS.value))
        message = cursor.fetchone()[0]
    except mysql.connector.Error as err:
        myprint(f"Could not get post message from log for user | Error: {err}")
        message = None
    finally:
        cursor.close()
        connection.close()

    return message


def has_engaged_url_with_x_days(user_id: int, post_url: str, days: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT COUNT(*) FROM logs WHERE user_id = %s AND post_url = %s AND action_type = %s AND result = %s AND created_at > NOW() - INTERVAL %s DAY",
            (user_id, post_url, LogActionType.ENGAGED.value, LogResultType.SUCCESS.value, days))
        count = cursor.fetchone()[0]
    except mysql.connector.Error as err:
        myprint(f"Could not determine if user engaged with url with x days | Error: {err}")
        count = 0
    finally:
        cursor.close()
        connection.close()

    return count > 0


def get_company_linked_in_url_for_user(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT company_linked_in_url FROM users WHERE id = %s", (user_id,))
        company_linked_in_url = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user company linked in url | Error: {err}")
        company_linked_in_url = None
    finally:
        cursor.close()
        connection.close()

    return company_linked_in_url[0] if company_linked_in_url else None
