from dotenv import load_dotenv
import os
import mysql.connector

from cqc_lem.utilities.utils import myprint

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
