import csv
import pymysql
import app.utils.DB_Utils

def insert_csv_to_tags(file_path):
    connection = app.utils.DB_Utils.get_db_connection()
    cursor = connection.cursor()

    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # 헤더 스킵

        for row in reader:
            tag_name = row[0]
            query = "INSERT INTO Tags (name) VALUES (%s)"
            try:
                cursor.execute(query, (tag_name,))
            except pymysql.IntegrityError:
                print(f"Duplicate entry skipped: {tag_name}")

    connection.commit()
    print("Tags data inserted successfully.")
    cursor.close()
    connection.close()

def insert_csv_to_locations(file_path):
    connection = app.utils.DB_Utils.get_db_connection()
    cursor = connection.cursor()

    # SQL 쿼리
    query = "INSERT INTO Locations (region, district) VALUES (%s, %s)"

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # 헤더 스킵

            for row in reader:
                region, district = row
                # 데이터 삽입
                cursor.execute(query, (region.strip(), district))

        # 커밋
        connection.commit()
        print("Locations 데이터 삽입 완료")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        cursor.close()
        connection.close()

# saramin 데이터 DB에 저장 하는 함수들
# Locations 테이블의 id를 메모리에 저장
def load_locations_to_memory(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT id, region, district FROM Locations")
    locations = { (row[1], row[2]): row[0] for row in cursor.fetchall() }
    cursor.close()
    return locations

# Tags 테이블의 id를 메모리에 저장
def load_tags_to_memory(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM Tags")
    tags = {row[1]: row[0] for row in cursor.fetchall()}
    cursor.close()
    return tags

# Tag id를 가져오거나 새로 생성
def get_or_create_tag_id(connection, tag_name, tags_ids):
    # 태그가 존재하는지 확인
    if tag_name in tags_ids:
        return tags_ids[tag_name]

    # 태그가 없으면 새로 삽입
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Tags (name) VALUES (%s)", (tag_name,))
    connection.commit()

    tag_id = cursor.lastrowid
    tags_ids[tag_name] = tag_id
    print("새로운 태그 추가: {}".format(tag_name))
    # 새로 삽입된 태그 ID 반환
    return tag_id

# 회사 정보를 Companies 테이블에 삽입
def insert_company(connection, location_id, company_name, company_link):
    # 중복 확인
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM Companies WHERE name = %s", (company_name,))
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("INSERT INTO Companies (location_id, name, link) VALUES (%s, %s, %s)", (location_id, company_name, company_link))
    connection.commit()
    return cursor.lastrowid

# 구인 공고 정보를 Jobs 테이블에 삽입
def insert_job(connection, job_data, company_id, location_id):
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO Jobs (title, company_id, location_id, career, education, employment, salary, register_date, deadline, link)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        job_data['title'], company_id, location_id, job_data['career'], job_data['education'],
        job_data['employment'], job_data['salary'], job_data['register_date'], job_data['deadline'], job_data['job_link']
    ))
    connection.commit()
    return cursor.lastrowid

# 구인 공고의 태그들을 JobTags 테이블에 삽입
def insert_job_tags(connection, job_id, tag_ids):
    cursor = connection.cursor()
    for tag_id in tag_ids:
        try:
            # 중복 확인
            cursor.execute(
                "INSERT INTO JobTags (job_id, tag_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE job_id=job_id",
                (job_id, tag_id)
            )
        except pymysql.IntegrityError:
            print(f"Duplicate JobTags entry skipped: job_id={job_id}, tag_id={tag_id}")
    connection.commit()

# csv 파일을 읽어 구인 공고 정보를 DB에 삽입
def insert_saramin_csv_to_db(file_path):
    connection = app.utils.DB_Utils.get_db_connection()
    locations_ids = load_locations_to_memory(connection)
    tags_ids = load_tags_to_memory(connection)

    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    # 1. 지역 ID 가져오기
                    parts = row['지역'].replace('서울전체', '서울 전체').replace('경기전체', '경기 전체').split()

                    region = parts[0]
                    district = ' '.join(parts[1:])
                    location_id = locations_ids.get((region, district))
                    if not location_id:
                        raise ValueError(f"지역 정보가 없습니다: {region}, {district}")

                    # 2. 회사 삽입
                    company_id = insert_company(connection, location_id, row['회사명'], row['회사 링크'])

                    # 3. 마감일 처리
                    if not row['마감일'] or row['마감일'].strip() == '':
                        deadline = None
                    elif row['마감일'] == '상시채용':
                        deadline = '9999-12-30'
                    elif row['마감일'] == '채용시':
                        deadline = '9999-12-31'
                    else:
                        deadline = row['마감일']  # 날짜 그대로 저장

                    # 4. 채용 공고 삽입
                    job_data = {
                        'title': row['채용 제목'],
                        'job_link' : row['채용 링크'],
                        'career': row['경력'],
                        'education': row['학력'],
                        'employment': row['고용형태'],
                        'salary': row['연봉'],
                        'register_date': row['등록일'],
                        'deadline': deadline    # 처리된 마감일
                    }

                    # 5. 채용 공고 삽입
                    job_id = insert_job(connection, job_data, company_id, location_id)

                    # 6. 태그 처리 및 JobTags 테이블에 삽입
                    tags = row['직무 분야'].split(', ')

                    if tags == ['']: # 비어있는 경우
                        tags = []    # 빈 리스트로 초기화

                    tag_ids = []
                    for tag_name in tags:
                        tag_id = get_or_create_tag_id(connection, tag_name, tags_ids)
                        tag_ids.append(tag_id)
                    insert_job_tags(connection, job_id, tag_ids)  # 태그 리스트를 전달

                except Exception as e:
                    print(f"에러 발생: {e}")

    finally:
        if connection:
            connection.close()