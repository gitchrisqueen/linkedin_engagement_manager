import os
from datetime import datetime, timedelta

import mysql.connector
from dotenv import load_dotenv

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

    if pre_post_time is None:
        now = datetime.now()
        # Get time for 15 minutes prior to now
        pre_post_time = now - timedelta(minutes=15)

    conn = get_db_connection()
    cursor = conn.cursor()
    # TODO: Need to get posts that have scheduled time in the next 15 minutes - move this to db.py function
    cursor.execute(
        """SELECT p.id, p.scheduled_time, p.user_id 
            FROM posts AS p
            WHERE status = 'approved' AND scheduled_time <= %s 
            ORDER BY scheduled_time ASC 
            LIMIT 1""",
        (pre_post_time,))  # Get the first post that is scheduled to post now or earlier
    posts = cursor.fetchall()

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
