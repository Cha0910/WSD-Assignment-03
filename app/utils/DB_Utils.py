import pymysql

def get_db_connection():
    """
    데이터베이스 연결을 생성하는 함수.

    Returns:
        connection: pymysql 연결 객체
    """
    DB_CONFIG = {
        "host": "127.0.0.1",  # 클라우드 로컬 IP
        "port": 8080,  # 포트
        "user": "WSD_03",  # 사용자 이름
        "password": "03_Assignment",  # 비밀번호
        "database": "WSD_03_DB"  # 데이터베이스 이름
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