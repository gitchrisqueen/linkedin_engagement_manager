import os
from datetime import datetime, timedelta

import mysql.connector
from dotenv import load_dotenv

from cqc_lem.linked_in_profile import LinkedInProfile
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


def get_db_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )


def store_cookies(user_email: str, cookies: list[dict]):
    connection = get_db_connection()
    cursor = connection.cursor()

    user_id = get_user_id(user_email)

    for cookie in cookies:
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

    connection.commit()
    cursor.close()
    connection.close()


def get_cookies(url: str, user_email: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Extract the top-level domain from the URL
    tld = get_top_level_domain(url)

    cursor.execute("""
        SELECT c.name, c.value, c.domain, c.path, UNIX_TIMESTAMP(c.expiry) AS expiry, c.secure, c.http_only
        FROM cookies c
        JOIN users u ON c.user_id = u.id
        WHERE c.domain LIKE %s AND u.email = %s
    """, (f"%{tld}%", user_email))

    cookies = cursor.fetchall()
    cursor.close()
    connection.close()
    return cookies


def add_user(email: str, password: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, password))
        connection.commit()
    except mysql.connector.errors.IntegrityError as e:
        if e.errno == mysql.connector.errorcode.ER_DUP_ENTRY:
            print(f"User with email {email} already exists.")
        else:
            print(f"An error occurred: {e}")
    finally:
        cursor.close()
        connection.close()


def get_user_id(email: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))

    user_id = cursor.fetchone()
    cursor.close()
    connection.close()
    return user_id['id'] if user_id else None


def insert_post(email, content, scheduled_time, post_type) -> bool:
    user_id = get_user_id(email)

    if not user_id:
        print(f"User with email {email} not found.")
        return False

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO posts (content, scheduled_time, post_type, user_id)
        VALUES (%s, %s, %s, %s)
    """, (content, scheduled_time, post_type, user_id))

    connection.commit()
    success = cursor.rowcount == 1
    cursor.close()
    connection.close()
    return success

def insert_planned_post(user_id: int, scheduled_time, post_type: str, buyer_stage: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO posts (scheduled_time, post_type, user_id, buyer_stage, status, content)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (scheduled_time, post_type, user_id, buyer_stage, 'planning', 'TBD'))

    connection.commit()
    success = cursor.rowcount == 1
    cursor.close()
    connection.close()
    return success

def update_db_post(content: str, scheduled_time: str, post_type: str, post_id: int, status: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE posts SET content = %s, scheduled_time =%s, post_type = %s, status = %s WHERE id = %s",
        (content, scheduled_time, post_type, status, post_id)
    )

    connection.commit()
    success = cursor.rowcount == 1
    cursor.close()
    connection.close()

    return success

def update_db_post_content(post_id: int, content: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE posts SET content = %s, status = 'pending' WHERE id = %s",
        (content, post_id)
    )

    connection.commit()
    success = cursor.rowcount == 1
    cursor.close()
    connection.close()

    return success

def update_db_post_status(post_id: int, status: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE posts SET status = %s WHERE id = %s",
        (status, post_id)
    )

    connection.commit()
    success = cursor.rowcount == 1
    cursor.close()
    connection.close()

    return success


def get_posts(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, content, scheduled_time, post_type, status FROM posts WHERE user_id = %s ORDER BY scheduled_time asc",
        (user_id,))

    posts = cursor.fetchall()
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

    cursor.execute("SELECT content FROM posts WHERE id = %s", (post_id,))

    post = cursor.fetchone()
    cursor.close()
    connection.close()

    return post['content'] if post else None


def get_ready_to_post_posts(pre_post_time: datetime = None) -> list:
    """Query the database for any pending posts that are scheduled to post now or earlier"""

    now = datetime.now()
    if pre_post_time is None:
        # Get time for 15 minutes after to now
        pre_post_time = now + timedelta(minutes=15)

    myprint(f"Pre-post time: {pre_post_time}")

    conn = get_db_connection()
    cursor = conn.cursor()
    # TODO: Need to get posts that have scheduled time in the next 15 minutes - move this to db.py function
    cursor.execute(
        """SELECT p.id, p.scheduled_time, p.user_id 
            FROM posts AS p
            WHERE status = 'approved' AND scheduled_time BETWEEN %s AND %s 
            ORDER BY scheduled_time ASC 
            """,
        (now - timedelta(days=1), pre_post_time))  # Get the first post that is scheduled to post now or earlier
    posts = cursor.fetchall()

    # Print the id's ready to post
    myprint(f"Posts ready to post: {[post[0] for post in posts]}")

    return posts


def get_user_password_pair_by_id(user_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT email, password FROM users WHERE id = %s", (user_id,))

    user_password_pair = cursor.fetchone()
    cursor.close()
    connection.close()

    if user_password_pair:
        return user_password_pair['email'], user_password_pair['password']
    else:
        return None, None


def get_user_password_pairs():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT email, password FROM users")
    user_password_pairs = cursor.fetchall()
    cursor.close()
    connection.close()

    return user_password_pairs


def add_linkedin_profile(profile: LinkedInProfile):
    connection = get_db_connection()
    cursor = connection.cursor()
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
    success = cursor.rowcount == 1
    cursor.close()
    connection.close()
    return success


def get_linked_in_profile_by_url(profile_url: str, updated_less_than_days_ago: int = 1):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT data FROM profiles WHERE profile_url = %s AND updated_at > NOW() - INTERVAL %s DAY", (profile_url, updated_less_than_days_ago))
    profile_data = cursor.fetchone()

    cursor.close()
    connection.close()

    return profile_data


def get_linked_in_profile_by_email(profile_email: str, updated_less_than_days_ago: int = 1):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT data FROM profiles WHERE email = %s AND updated_at > NOW() - INTERVAL %s DAY", (profile_email, updated_less_than_days_ago))
    profile_data = cursor.fetchone()

    cursor.close()
    connection.close()

    return profile_data


def remove_linked_in_profile_by_url(profile_url: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM profiles WHERE profile_url = %s", (profile_url,))
    connection.commit()

    cursor.close()
    connection.close()


def remove_linked_in_profile_by_email(profile_email: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM profiles WHERE email = %s", (profile_email,))
    connection.commit()

    cursor.close()
    connection.close()


def get_post_type_counts(user_id: int):
    """Query the database to get the count of each post_type in the 'posts' table for the given user id."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT post_type, COUNT(*) AS count FROM posts WHERE user_id = %s GROUP BY post_type", (user_id,))
    post_counts = {row['post_type']: row['count'] for row in cursor.fetchall()}

    cursor.close()
    connection.close()

    return post_counts


def get_planned_posts_for_current_week():
    """Query the database to get the planned content for the current week."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, post_type, buyer_stage FROM posts WHERE status = 'planning' AND WEEK(scheduled_time) = WEEK(NOW())")
    planned_content = cursor.fetchall()

    cursor.close()
    connection.close()

    return planned_content

def get_last_planned_post_date_for_user(user_id: int):
    """Query the database to get the last planned post date for the given user."""
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT MAX(scheduled_time) AS last_planned_date FROM posts WHERE user_id = %s AND status = 'planning'", (user_id,))
    last_planned_date = cursor.fetchone()

    cursor.close()
    connection.close()

    return last_planned_date[0] if last_planned_date else None