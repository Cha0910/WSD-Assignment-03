import pymysql
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


# Database Configuration

def get_db_connection():
    """
    데이터베이스 연결을 생성하는 함수.

    Returns:
        connection: pymysql 연결 객체
    """
    DB_CONFIG = {
        "host": os.getenv('DB_HOST'),
        "port": int(os.getenv('DB_PORT')),
        "user": os.getenv('DB_USER'),
        "password": os.getenv('DB_PASSWORD'),
        "database": os.getenv('DB_NAME')
    }
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("Database connection established.")
        return connection
    except pymysql.MySQLError as e:
        print(f"Error connecting to the database: {e}")
        raise

def load_locations_to_memory():
    """Load Locations data into memory."""
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, region, district FROM Locations")
    locations = { (row[1], row[2]): row[0] for row in cursor.fetchall() }
    cursor.close()
    connection.close()
    return locations

def load_tags_to_memory():
    """Load Tags data into memory."""
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM Tags")
    tags = { row[1]: row[0] for row in cursor.fetchall() }
    cursor.close()
    connection.close()
    return tags
