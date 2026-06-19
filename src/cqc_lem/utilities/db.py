import json
import os
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Optional

import mysql.connector
from cqc_lem.utilities.env_constants import AWS_MYSQL_SECRET_NAME, AWS_REGION
from cqc_lem.utilities.linkedin.profile import LinkedInProfile
from cqc_lem.utilities.logger import myprint
from cqc_lem.utilities.utils import get_top_level_domain, get_aws_ssm_secret
from dotenv import load_dotenv
from mysql.connector import errorcode

# Load .env file
load_dotenv()

MAX_WAIT_RETRY = 3
WAIT_TIMEOUT = 3

# Retrieve MySQL connection details from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
MYSQL_PORT = os.getenv('MYSQL_PORT')


def get_db_connection():
    """Establishes a connection to the MySQL database and returns the connection object.

    Raises:
        mysql.connector.Error: If there is an error connecting to the database.
    """

    global MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_PORT

    # if MYSQL_USER and MYSQL_PASSWORD are empty try to get it from AWS using get_secret function
    if AWS_MYSQL_SECRET_NAME is not None and AWS_REGION is not None:
        secret_dict = get_aws_ssm_secret(AWS_MYSQL_SECRET_NAME, AWS_REGION)
        MYSQL_HOST = secret_dict['host']
        MYSQL_USER = secret_dict['username']
        MYSQL_PASSWORD = secret_dict['password']
        MYSQL_DATABASE = secret_dict['dbname']
        MYSQL_PORT = secret_dict['port']

    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        port=MYSQL_PORT
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

    access_token_created_at = datetime.now(timezone.utc)

    if refresh_token is not None:
        refresh_token_created_at = datetime.now(timezone.utc)
    else:
        refresh_token_created_at = None

    try:
        cursor.execute("""INSERT INTO users (email, linked_sub_id, access_token, access_token_expires_in, access_token_created_at, refresh_token, refresh_token_expires_in, refresh_token_created_at, last_login, linkedin_connection_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'connected')
        ON DUPLICATE KEY UPDATE
                linked_sub_id = VALUES(linked_sub_id),
                access_token = VALUES(access_token),
                access_token_expires_in = VALUES(access_token_expires_in),
                access_token_created_at = VALUES(access_token_created_at),
                refresh_token = VALUES(refresh_token),
                refresh_token_expires_in = VALUES(refresh_token_expires_in),
                refresh_token_created_at = VALUES(refresh_token_created_at),
                last_login = VALUES(last_login),
                linkedin_connection_status = 'connected'

        """, (
            email,
            linked_sub_id,
            access_token, access_token_expires_in, access_token_created_at,
            refresh_token, refresh_token_expires_in, refresh_token_created_at,
            datetime.now(timezone.utc)))
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
        cursor.execute(
            "SELECT access_token FROM users WHERE id = %s AND (token_expiry IS NULL OR token_expiry > NOW())",
            (user_id,),
        )

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


def insert_post(email: str, content: str, scheduled_time: datetime, post_type: PostType,
                video_url: Optional[str] = None, carousel_slides: Optional[list[str]] = None) -> bool:
    user_id = get_user_id(email)

    success = False

    if not user_id:
        print(f"User with email {email} not found.")
        return success

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        else:
            scheduled_time = scheduled_time.astimezone(timezone.utc)

        slides_json = json.dumps(carousel_slides) if carousel_slides else None

        cursor.execute("""
            INSERT INTO posts (content, scheduled_time, post_type, user_id, video_url, carousel_slides)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (content, scheduled_time, post_type.value, user_id, video_url, slides_json))

        connection.commit()
        success = cursor.rowcount == 1
    except mysql.connector.Error as e:
        success = False
        print(f"Count not insert post. An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()

    return success


def insert_planned_post(user_id: int, scheduled_time: datetime, post_type: PostType, buyer_stage: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    success = False

    try:
        # Convert scheduled_time to UTC
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        else:
            scheduled_time = scheduled_time.astimezone(timezone.utc)

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


def update_db_post(content: str, video_url: str, scheduled_time: datetime, post_type: PostType, post_id: int,
                   post_status: PostStatus) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    success = False

    try:

        # Convert scheduled_time to UTC
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        else:
            scheduled_time = scheduled_time.astimezone(timezone.utc)

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


def get_posts(user_id: int, limit: int = 10, offset: int = 0,
              sort_order: str = 'asc', status_filter: Optional[str] = None) -> tuple[list, int]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    order = 'ASC' if sort_order.lower() != 'desc' else 'DESC'

    try:
        where = "WHERE user_id = %s"
        params: list = [user_id]
        if status_filter:
            where += " AND status = %s"
            params.append(status_filter.lower())

        cursor.execute(
            f"SELECT COUNT(*) AS total FROM posts {where}",
            params
        )
        total = cursor.fetchone()['total']

        cursor.execute(
            f"SELECT id, content, video_url, scheduled_time, post_type, status, carousel_slides "
            f"FROM posts {where} ORDER BY scheduled_time {order} LIMIT %s OFFSET %s",
            params + [limit, offset]
        )
        posts = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get posts for user id: {user_id} | Error: {err}")
        posts = []
        total = 0
    finally:
        cursor.close()
        connection.close()

    return posts, total


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


def get_post_by_email(email: str, limit: int = 10, offset: int = 0,
                      sort_order: str = 'asc', status_filter: Optional[str] = None) -> tuple[list, int]:
    user_id = get_user_id(email)

    if not user_id:
        print(f"User with email {email} not found.")
        return [], 0

    return get_posts(user_id, limit=limit, offset=offset, sort_order=sort_order, status_filter=status_filter)


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


def get_post_user_id(post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))

        post = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get post user id for post id: {post_id} | Error: {err}")
        post = False
    finally:
        cursor.close()
        connection.close()

    return post['user_id'] if post else None


def get_post_video_url(post_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT video_url FROM posts WHERE id = %s", (post_id,))

        post = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get post video_url for post id: {post_id} | Error: {err}")
        post = False
    finally:
        cursor.close()
        connection.close()

    return post['video_url'] if post else None


def get_post_type(post_id: int) -> Optional[PostType]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT post_type FROM posts WHERE id = %s", (post_id,))
        row = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get post_type for post id: {post_id} | Error: {err}")
        row = None
    finally:
        cursor.close()
        connection.close()

    if row:
        try:
            return PostType(row['post_type'])
        except ValueError:
            return None
    return None


def get_carousel_slides(post_id: int) -> list[str]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT carousel_slides FROM posts WHERE id = %s", (post_id,))
        row = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get carousel_slides for post id: {post_id} | Error: {err}")
        row = None
    finally:
        cursor.close()
        connection.close()

    if row and row['carousel_slides']:
        try:
            slides = row['carousel_slides']
            if isinstance(slides, str):
                slides = json.loads(slides)
            return slides if isinstance(slides, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def bulk_update_posts(post_ids: list[int], status: Optional[PostStatus] = None,
                      scheduled_time: Optional[datetime] = None) -> bool:
    if not post_ids:
        return False

    connection = get_db_connection()
    cursor = connection.cursor()

    success = False
    try:
        sets = []
        params: list = []

        if status is not None:
            sets.append("status = %s")
            params.append(status.value)
        if scheduled_time is not None:
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
            else:
                scheduled_time = scheduled_time.astimezone(timezone.utc)
            sets.append("scheduled_time = %s")
            params.append(scheduled_time)

        if not sets:
            return False

        placeholders = ', '.join(['%s'] * len(post_ids))
        params.extend(post_ids)

        cursor.execute(
            f"UPDATE posts SET {', '.join(sets)} WHERE id IN ({placeholders})",
            params
        )
        connection.commit()
        success = cursor.rowcount > 0
    except mysql.connector.Error as e:
        myprint(f"Could not bulk update posts. An error occurred: {e}")
        success = False
    finally:
        cursor.close()
        connection.close()

    return success


def soft_delete_posts(post_ids: list[int]) -> bool:
    return bulk_update_posts(post_ids, status=PostStatus.REJECTED)


def get_ready_to_post_posts(pre_post_time: datetime = None, post_time_delta_minutes=20) -> list:
    """Query the database for any pending posts that are scheduled to post now or earlier"""

    now = datetime.now(timezone.utc)
    if pre_post_time is None:
        # Get time for post_time_delta after now
        pre_post_time = now + timedelta(minutes=post_time_delta_minutes)

    yesterday = now - timedelta(days=1)

    myprint(f"Getting post between : {yesterday} and {pre_post_time} (UTC)")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Get posts that have scheduled time between 24 hours ago and the pre_post_time
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


def add_linkedin_profile(profile: LinkedInProfile, user_id: Optional[int] = None):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO profiles (profile_url, email, data, user_id)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                    profile_url = VALUES(profile_url),
                    email = VALUES(email),
                    data = VALUES(data),
                    user_id = COALESCE(VALUES(user_id), user_id)
            """,
                       (str(profile.profile_url), profile.email, profile.model_dump_json(), user_id))

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


def get_linked_in_profile_by_user_id(user_id: int, updated_less_than_days_ago: int = 1):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT data FROM profiles WHERE user_id = %s AND updated_at > NOW() - INTERVAL %s DAY",
                       (user_id, updated_less_than_days_ago))
        profile_data = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get linkedin profile data by user_id | Error: {err}")
        profile_data = None
    finally:
        cursor.close()
        connection.close()

    return profile_data


def remove_linked_in_profile_by_user_id(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM profiles WHERE user_id = %s", (user_id,))
        connection.commit()
        success = True
    except mysql.connector.Error as err:
        myprint(f"Could not remove linkedin profile by user_id | Error: {err}")
        success = False
    finally:
        cursor.close()
        connection.close()
    return success


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
            f"SELECT user_id, id, post_type, buyer_stage FROM posts WHERE status = 'planning' {where_clause} AND YEARWEEK(scheduled_time, 1) = YEARWEEK(NOW(), 1)")
        planned_content = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get planned post for current week | Error: {err}")
        planned_content = []
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
            f"SELECT user_id, id, post_type, buyer_stage FROM posts WHERE status = 'planning' {where_clause} AND YEARWEEK(scheduled_time, 1) = YEARWEEK(NOW() + INTERVAL 7 DAY, 1)")
        planned_content = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get planned post for next week | Error: {err}")
        planned_content = []
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


def update_user(user_id: int, email: str = None, blog_url: str = None, sitemap_url: str = None) -> bool:
    if not any([email, blog_url, sitemap_url]):
        return False
    connection = get_db_connection()
    cursor = connection.cursor()
    fields, values = [], []
    if email:
        fields.append("email = %s")
        values.append(email)
    if blog_url:
        fields.append("blog_url = %s")
        values.append(blog_url)
    if sitemap_url:
        fields.append("sitemap_url = %s")
        values.append(sitemap_url)
    values.append(user_id)
    try:
        cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = %s", values)
        connection.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        myprint(f"Could not update user {user_id} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


def get_active_user_ids():
    """Return user IDs eligible for automated posting/engagement.

    A user is active when ALL of:
      1. Has a valid LinkedIn connection (linkedin_connection_status = 'connected'
         AND access_token not expired)
      2. Has an active subscription OR an unexpired trial
      3. Has logged in within their configured inactivate delay
         (NULL delay = never auto-inactivate)
    """
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id FROM users
            WHERE
                -- Must have a live LinkedIn token
                linkedin_connection_status = 'connected'
                AND access_token IS NOT NULL
                AND access_token_created_at IS NOT NULL
                AND access_token_created_at + INTERVAL access_token_expires_in SECOND > NOW()

                -- Must have an active or unexpired trial subscription
                AND (
                    subscription_status = 'active'
                    OR (
                        subscription_status = 'trial'
                        AND (trial_ends_at IS NULL OR trial_ends_at > NOW())
                    )
                )

                -- Must have logged in within their configured inactivity window
                AND (
                    last_login_inactivate_delay IS NULL
                    OR (
                        last_login IS NOT NULL
                        AND last_login >= NOW() - INTERVAL last_login_inactivate_delay DAY
                    )
                )
        """)
        active_user_ids = [row[0] for row in cursor.fetchall()]
    except mysql.connector.Error as err:
        myprint(f"Could not get active user ids | Error: {err}")
        active_user_ids = []
    finally:
        cursor.close()
        connection.close()

    return active_user_ids


def get_user_location(user_id: int) -> tuple[float, float] | None:
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT latitude, longitude FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get user location | Error: {err}")
        row = None
    finally:
        cursor.close()
        connection.close()
    return (float(row[0]), float(row[1])) if row and row[0] and row[1] else None


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


def get_dm_history_for_profile(user_id: int, profile_url: str) -> list[str]:
    """Return all DM messages previously sent by user_id to profile_url, oldest first."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT message FROM logs WHERE user_id = %s AND post_url = %s AND action_type = %s ORDER BY created_at ASC",
            (user_id, profile_url, LogActionType.DM.value),
        )
        rows = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get DM history for profile | Error: {err}")
        rows = []
    finally:
        cursor.close()
        connection.close()
    return [row[0] for row in rows if row[0]]


def get_post_status(post_id: int) -> str | None:
    """Return the current status string of a post, or None if not found."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT status FROM posts WHERE id = %s", (post_id,))
        row = cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get post status | Error: {err}")
        row = None
    finally:
        cursor.close()
        connection.close()
    return row[0] if row else None


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


def get_recent_logs(user_id: int, limit: int = 20) -> list:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """SELECT id, action_type, result, post_id, post_url, message, created_at
               FROM logs WHERE user_id = %s ORDER BY created_at DESC LIMIT %s""",
            (user_id, limit)
        )
        rows = cursor.fetchall()
    except mysql.connector.Error as err:
        myprint(f"Could not get recent logs | Error: {err}")
        rows = []
    finally:
        cursor.close()
        connection.close()

    return rows


def update_user_settings(user_id: int, blog_url: str = None, sitemap_url: str = None) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "UPDATE users SET blog_url = %s, sitemap_url = %s WHERE id = %s",
            (blog_url, sitemap_url, user_id)
        )
        connection.commit()
        success = cursor.rowcount >= 0
    except mysql.connector.Error as err:
        myprint(f"Could not update user settings | Error: {err}")
        success = False
    finally:
        cursor.close()
        connection.close()

    return success


# ---------------------------------------------------------------------------
# PIN authentication
# ---------------------------------------------------------------------------

def create_pin_for_email(email: str, pin_hash: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM email_pin_auth WHERE email = %s AND used = 0", (email,))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        cursor.execute(
            "INSERT INTO email_pin_auth (email, pin, expires_at) VALUES (%s, %s, %s)",
            (email, pin_hash, expires_at),
        )
        connection.commit()
        return cursor.rowcount == 1
    except mysql.connector.Error as err:
        myprint(f"Could not create PIN for {email} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


def verify_pin_for_email(email: str, pin_hash: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT id FROM email_pin_auth
               WHERE email = %s AND pin = %s AND used = 0 AND expires_at > %s
               ORDER BY id DESC LIMIT 1""",
            (email, pin_hash, datetime.now(timezone.utc)),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE email_pin_auth SET used = 1 WHERE id = %s", (row['id'],))
            connection.commit()
            return True
        return False
    except mysql.connector.Error as err:
        myprint(f"Could not verify PIN for {email} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def create_session(user_id: int) -> Optional[str]:
    import secrets
    token = secrets.token_hex(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO sessions (session_token, user_id, expires_at) VALUES (%s, %s, %s)",
            (token, user_id, expires_at),
        )
        cursor.execute(
            "UPDATE users SET last_login = %s WHERE id = %s",
            (now, user_id),
        )
        connection.commit()
        return token
    except mysql.connector.Error as err:
        myprint(f"Could not create session for user_id {user_id} | Error: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def get_session_user_id(token: str) -> Optional[int]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id FROM sessions WHERE session_token = %s AND expires_at > %s",
            (token, datetime.now(timezone.utc)),
        )
        row = cursor.fetchone()
        return row['user_id'] if row else None
    except mysql.connector.Error as err:
        myprint(f"Could not validate session token | Error: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def delete_session(token: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM sessions WHERE session_token = %s", (token,))
        connection.commit()
        return True
    except mysql.connector.Error as err:
        myprint(f"Could not delete session | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def add_user_by_email(email: str) -> Optional[int]:
    from cqc_lem.utilities.env_constants import FREE_TRIAL_DAYS
    now = datetime.now(timezone.utc)
    trial_ends = now + timedelta(days=FREE_TRIAL_DAYS)
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO users
               (email, subscription_status, subscription_tier, trial_started_at, trial_ends_at)
               VALUES (%s, 'trial', 'free_trial', %s, %s)""",
            (email, now, trial_ends),
        )
        connection.commit()
        user_id = cursor.lastrowid
        # Create a Stripe customer in the background (non-fatal if it fails)
        try:
            from cqc_lem.utilities.stripe_util import create_stripe_customer
            stripe_cid = create_stripe_customer(email, user_id)
            if stripe_cid:
                cursor.execute(
                    "UPDATE users SET stripe_customer_id = %s WHERE id = %s",
                    (stripe_cid, user_id),
                )
                connection.commit()
        except Exception as se:
            myprint(f"Stripe customer creation non-fatal error for {email}: {se}")
        return user_id
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            return get_user_id(email)
        myprint(f"Could not create user for {email} | Error: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def get_user_email(user_id: int) -> Optional[str]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return row['email'] if row else None
    except mysql.connector.Error as err:
        myprint(f"Could not get email for user_id {user_id} | Error: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def get_user_token_info(user_id: int) -> Optional[dict]:
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT access_token, access_token_expires_in, access_token_created_at,
                      refresh_token, refresh_token_expires_in, refresh_token_created_at
               FROM users WHERE id = %s""",
            (user_id,),
        )
        return cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get token info for user_id {user_id} | Error: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def update_user_access_token(
    user_id: int,
    access_token: str,
    expires_in: int,
    refresh_token: Optional[str] = None,
    refresh_token_expires_in: Optional[int] = None,
) -> bool:
    now = datetime.now(timezone.utc)
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        if refresh_token:
            cursor.execute(
                """UPDATE users SET
                       access_token = %s,
                       access_token_expires_in = %s,
                       access_token_created_at = %s,
                       refresh_token = %s,
                       refresh_token_expires_in = %s,
                       refresh_token_created_at = %s
                   WHERE id = %s""",
                (access_token, expires_in, now,
                 refresh_token, refresh_token_expires_in, now, user_id),
            )
        else:
            cursor.execute(
                """UPDATE users SET
                       access_token = %s,
                       access_token_expires_in = %s,
                       access_token_created_at = %s
                   WHERE id = %s""",
                (access_token, expires_in, now, user_id),
            )
        connection.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        myprint(f"Could not update access token for user_id {user_id} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


def update_user_linkedin_token(
    user_id: int,
    linked_sub_id: str,
    access_token: str,
    expires_in: int,
    refresh_token: Optional[str] = None,
    refresh_token_expires_in: Optional[int] = None,
    linkedin_email: Optional[str] = None,
) -> bool:
    """Write a fresh LinkedIn OAuth token to the user identified by user_id.

    Called from the OAuth callback so the token is always attached to the
    logged-in user, regardless of which email LinkedIn returns.
    """
    now = datetime.now(timezone.utc)
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        if refresh_token:
            cursor.execute(
                """UPDATE users SET
                       linked_sub_id = %s,
                       linkedin_email = %s,
                       access_token = %s,
                       access_token_expires_in = %s,
                       access_token_created_at = %s,
                       refresh_token = %s,
                       refresh_token_expires_in = %s,
                       refresh_token_created_at = %s,
                       linkedin_connection_status = 'connected'
                   WHERE id = %s""",
                (linked_sub_id, linkedin_email or None, access_token, expires_in, now,
                 refresh_token, refresh_token_expires_in, now, user_id),
            )
        else:
            cursor.execute(
                """UPDATE users SET
                       linked_sub_id = %s,
                       linkedin_email = %s,
                       access_token = %s,
                       access_token_expires_in = %s,
                       access_token_created_at = %s,
                       linkedin_connection_status = 'connected'
                   WHERE id = %s""",
                (linked_sub_id, linkedin_email or None, access_token, expires_in, now, user_id),
            )
        connection.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        myprint(f"Could not update LinkedIn token for user_id {user_id} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


def update_linkedin_connection_status(user_id: int, status: str) -> bool:
    """Set linkedin_connection_status to 'connected', 'expired', or 'disconnected'."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE users SET linkedin_connection_status = %s WHERE id = %s",
            (status, user_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        myprint(f"Could not update linkedin_connection_status for user_id {user_id} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


def get_user_subscription_info(user_id: int) -> Optional[dict]:
    """Return subscription fields for the given user."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT subscription_status, subscription_tier,
                      trial_started_at, trial_ends_at,
                      stripe_customer_id, stripe_subscription_id
               FROM users WHERE id = %s""",
            (user_id,),
        )
        return cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get subscription info for user_id {user_id} | Error: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def update_subscription_from_stripe(
    stripe_customer_id: str,
    status: str,
    tier: Optional[str],
    subscription_id: Optional[str],
    current_period_end: Optional[datetime] = None,
) -> bool:
    """Called from Stripe webhook handler to sync subscription state.

    When tier is None (e.g. subscription deleted) we preserve the existing tier so
    historical data is retained. Pass an explicit empty string to clear it.
    """
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        if tier is not None:
            cursor.execute(
                """UPDATE users
                   SET subscription_status = %s,
                       subscription_tier = %s,
                       stripe_subscription_id = %s,
                       subscription_current_period_end = %s
                   WHERE stripe_customer_id = %s""",
                (status, tier, subscription_id, current_period_end, stripe_customer_id),
            )
        else:
            # Don't overwrite the tier — preserve it for historical reference
            cursor.execute(
                """UPDATE users
                   SET subscription_status = %s,
                       stripe_subscription_id = %s,
                       subscription_current_period_end = %s
                   WHERE stripe_customer_id = %s""",
                (status, subscription_id, current_period_end, stripe_customer_id),
            )
        connection.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        myprint(f"Could not update subscription from Stripe for customer {stripe_customer_id} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


def get_users_with_stripe_subscriptions() -> list[dict]:
    """Return all users that have a Stripe subscription ID (for periodic sync)."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT id, stripe_customer_id, stripe_subscription_id,
                      subscription_status, subscription_tier
               FROM users
               WHERE stripe_subscription_id IS NOT NULL
                 AND subscription_status IN ('active', 'past_due')"""
        )
        return cursor.fetchall() or []
    except mysql.connector.Error as err:
        myprint(f"Could not fetch Stripe subscribers | Error: {err}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_user_preferences(user_id: int) -> Optional[dict]:
    """Return user preference fields: last_login_inactivate_delay and auto_schedule_posts."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT last_login_inactivate_delay, auto_schedule_posts FROM users WHERE id = %s",
            (user_id,),
        )
        return cursor.fetchone()
    except mysql.connector.Error as err:
        myprint(f"Could not get preferences for user_id {user_id} | Error: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def update_user_preferences(
    user_id: int,
    inactivate_delay: Optional[int],
    auto_schedule_posts: bool,
) -> bool:
    """Persist user-configurable inactivity delay (None = never) and auto-schedule flag."""
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """UPDATE users
               SET last_login_inactivate_delay = %s,
                   auto_schedule_posts = %s
               WHERE id = %s""",
            (inactivate_delay, 1 if auto_schedule_posts else 0, user_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        myprint(f"Could not update preferences for user_id {user_id} | Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()
