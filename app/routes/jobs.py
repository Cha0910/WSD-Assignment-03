import pymysql
from flask import Blueprint, request, jsonify
from app.utils.DB_Utils import get_db_connection
from ..utils.DB_Ids import locations, tags

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/', methods=['GET'])
def get_jobs():
    page = request.args.get('page', default=1, type=int)  # 기본값 1
    page_size = request.args.get('page_size', default=20, type=int)  # 기본값 20

    offset = (page - 1) * page_size # 페이지네이션 계산

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    try:
        query = """
            SELECT j.id, j.title, c.name AS company_name, j.salary, j.deadline
            FROM Jobs j
            JOIN Companies c ON j.company_id = c.id
            ORDER BY j.id ASC  -- ID 순으로 정렬
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (page_size, offset))
        jobs = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": jobs,
            "pagination": {
                "current_page": page,
                "per_page": page_size,
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@bp.route('/search', methods=['GET'])
def search_jobs():
    keyword = request.args.get('keyword', default=None, type=str)
    page = request.args.get('page', default=1, type=int) # 기본 값 1
    page_size = request.args.get('page_size', default=20, type=int)  # 기본값 20

    if not keyword:
        return jsonify({"status": "error", "message": "Keyword is required for search"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # 키워드 검색 쿼리
        search_query = """
            SELECT j.id, j.title, c.name AS company_name, j.salary, j.deadline
            FROM Jobs j
            JOIN Companies c ON j.company_id = c.id
            WHERE j.title LIKE %s OR c.name LIKE %s
            LIMIT %s OFFSET %s
        """

        like_keyword = f"%{keyword}%"  # SQL에서 부분 일치를 위한 키워드 포맷
        offset = (page - 1) * page_size  # 페이지네이션 계산

        cursor.execute(search_query, (like_keyword, like_keyword, page_size, offset))
        jobs = cursor.fetchall()

        if not jobs:
            return jsonify({"status": "success", "data": [], "message": "No jobs found for the given keyword"}), 200

        return jsonify({
            "status": "success",
            "data": jobs,
            "pagination": {
                "current_page": page,
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/filter', methods=['GET'])
def filter_jobs():
    query_locations = request.args.getlist('location')  # 여러 개의 location 값 처리
    query_tags = request.args.getlist('tag')  # 여러 개의 tag 값 처리
    page = request.args.get('page', default=1, type=int)  # 기본 값 1
    page_size = request.args.get('page_size', default=20, type=int)  # 기본값 20

    # 최소 하나의 location 또는 tag가 입력되지 않으면 에러
    if not query_locations and not query_tags:
        return jsonify({
            "status": "error",
            "message": "At least one location or tag must be provided."
        }), 400

    # Location id
    location_ids = set()
    for user_input in query_locations:
        if ' ' in user_input:  # 입력이 'region district' 형태일 때
            region, district = user_input.split(maxsplit=1)
        else:  # 입력이 'region' 형태일 때
            region, district = user_input, None

        # 메모리 데이터에서 필터링
        for (mem_region, mem_district), location_id in locations.items():
            if mem_region == region and (district is None or mem_district == district):
                location_ids.add(location_id)

    # Tag id
    tag_ids = [
        tag_id for tag_name, tag_id in tags.items()
        if tag_name in query_tags
    ]

    if not location_ids or not tag_ids:
        return jsonify({
            "status": "success",
            "data": [],
            "message": "No jobs found with the given filters."
        }), 200

    # Database connection
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # query
        query = """
            SELECT DISTINCT j.id, j.title, c.name AS company_name, j.salary, j.deadline
            FROM Jobs j
            JOIN Companies c ON j.company_id = c.id
            LEFT JOIN JobTags jt ON j.id = jt.job_id
            WHERE 
        """

        # 조건 작성
        conditions = []

        # location 필터링 조건 추가
        if location_ids:
            location_placeholders = ', '.join(['%s'] * len(location_ids))
            conditions.append(f"j.location_id IN ({location_placeholders})")

        # tag 필터링 조건 추가
        if tag_ids:
            tag_placeholders = ', '.join(['%s'] * len(tag_ids))
            conditions.append(f"jt.tag_id IN ({tag_placeholders})")

        # 조건 결합
        query += " AND ".join(conditions)

        # 페이지네이션 추가
        query += " LIMIT %s OFFSET %s"
        offset = (page - 1) * page_size
        params = list(location_ids) + tag_ids + [page_size, offset]

        cursor.execute(query, tuple(params))
        jobs = cursor.fetchall()

        if not jobs:
            return jsonify({"status": "success", "data": [], "message": "No jobs found with the given filters."}), 200

        return jsonify({
            "status": "success",
            "data": jobs,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_items": len(jobs)
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/sort', methods=['GET'])
def sort_jobs():
    order = request.args.get('order', default='asc')  # 정렬 순서 (asc 또는 desc)
    page = request.args.get('page', default=1, type=int)  # 기본 값 1
    page_size = request.args.get('page_size', default=20, type=int)  # 기본값 20

    # 정렬 순서 확인
    if order not in ['asc', 'desc']:
        return jsonify({
            "status": "error",
            "message": "Invalid order. Valid values are 'asc' or 'desc'."
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # query
        query = f"""
            SELECT j.id, j.title, c.name AS company_name, j.salary, j.deadline
            FROM Jobs j
            JOIN Companies c ON j.company_id = c.id
            ORDER BY j.deadline {order.upper()}
            LIMIT %s OFFSET %s
        """
        offset = (page - 1) * page_size
        params = [page_size, offset]

        cursor.execute(query, params)
        jobs = cursor.fetchall()

        if not jobs:
            return jsonify({"status": "success", "data": [], "message": "No jobs found."}), 200

        return jsonify({
            "status": "success",
            "data": jobs,
            "pagination": {
                "current_page": page,
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/', methods=['POST'])
def create_job():
    data = request.json

    # 입력 데이터
    title = data.get('title')
    company_name = data.get('company')
    company_link = data.get('company_link', None)
    location = data.get('location')
    salary = data.get('salary')
    career = data.get('career')
    education = data.get('education')
    employment = data.get('employment')
    deadline = data.get('deadline')
    input_tags = data.get('tags', [])  # List of tags, default empty
    job_link = data.get('link', None)

    # 필수 입력 항목이 없으면
    if not title or not company_name or not location:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # Locaion id
        location_parts = location.split()
        region = location_parts[0]
        district = ''.join(location_parts[1:]) if len(location_parts) > 1 else '전체'
        location_id = locations.get((region, district))

        if not location_id:
            return jsonify({"status": "error", "message": f"Invalid location: {location}"}), 400

        # Company id 검색 혹은 추가
        cursor.execute("SELECT id FROM Companies WHERE name = %s", (company_name,))
        company = cursor.fetchone()

        if company:
            company_id = company['id']
        else:
            cursor.execute("INSERT INTO Companies (name, location_id, link) VALUES (%s, %s, %s)", (company_name, location_id, company_link))
            connection.commit()
            company_id = cursor.lastrowid

        # 공고 등록
        cursor.execute("""
            INSERT INTO Jobs (title, company_id, location_id, salary, career, education, employment, deadline, link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (title, company_id, location_id, salary, career, education, employment, deadline, job_link))
        connection.commit()
        job_id = cursor.lastrowid

        # 태그 등록
        tag_ids = []
        for tag in input_tags:
            tag_id = tags.get(tag)
            if not tag_id:
                cursor.execute("INSERT INTO Tags (name) VALUES (%s)", (tag,))
                connection.commit()
                tag_id = cursor.lastrowid
                tags[tag] = tag_id
            tag_ids.append(tag_id)

        for tag_id in tag_ids:
            cursor.execute("INSERT INTO JobTags (job_id, tag_id) VALUES (%s, %s)", (job_id, tag_id))
        connection.commit()

        return jsonify({"status": "success", "message": "Job created successfully", "Job_id": job_id }), 201

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    data = request.json

    # 입력 데이터
    title = data.get('title')
    company_name = data.get('company')
    company_link = data.get('company_link', None)
    location = data.get('location')
    salary = data.get('salary')
    career = data.get('career')
    education = data.get('education')
    employment = data.get('employment')
    deadline = data.get('deadline')
    tags = data.get('tags', [])  # List of tags, default empty
    job_link = data.get('link', None)

    # 최소 하나는 있어야 함
    if not any([title, company_name, location, salary, career, education, employment, deadline, tags, job_link]):
        return jsonify({"status": "error", "message": "No fields provided for update"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Update fields dynamically
        update_fields = []
        params = []

        if title:
            update_fields.append("title = %s")
            params.append(title)

        if location:
            location_parts = location.split()
            region = location_parts[0]
            district = ' '.join(location_parts[1:]) if len(location_parts) > 1 else '전체'
            location_id = locations.get((region, district))

            if not location_id:
                return jsonify({"status": "error", "message": f"Invalid location: {location}"}), 400
            update_fields.append("location_id = %s")
            params.append(location_id)

        if company_name:
            cursor.execute("SELECT id FROM Companies WHERE name = %s", (company_name,))
            company = cursor.fetchone()

            if company:
                company_id = company['id']
            else:
                cursor.execute("INSERT INTO Companies (name, location_id, link) VALUES (%s, %s, %s)", (company_name, location_id, company_link))
                connection.commit()
                company_id = cursor.lastrowid
            update_fields.append("company_id = %s")
            params.append(company_id)

        if salary:
            update_fields.append("salary = %s")
            params.append(salary)

        if career:
            update_fields.append("career = %s")
            params.append(career)

        if education:
            update_fields.append("education = %s")
            params.append(education)

        if employment:
            update_fields.append("employment = %s")
            params.append(employment)

        if deadline:
            update_fields.append("deadline = %s")
            params.append(deadline)

        if job_link:
            update_fields.append("link = %s")
            params.append(job_link)

        # 업데이트 되는 요소 작성
        if update_fields:
            params.append(job_id)  # Add job_id for WHERE clause
            query = f"UPDATE Jobs SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, tuple(params))
            connection.commit()

        # 태그 업데이트
        if tags:
            # 태그 초기화
            cursor.execute("DELETE FROM JobTags WHERE job_id = %s", (job_id,))
            connection.commit()

            # 새로운 태그 추가
            tag_ids = []
            for tag in tags:
                tag_id = tags.get(tag)
                if not tag_id:
                    cursor.execute("INSERT INTO Tags (name) VALUES (%s)", (tag,))
                    connection.commit()
                    tag_id = cursor.lastrowid
                    tags[tag] = tag_id
                tag_ids.append(tag_id)

            for tag_id in tag_ids:
                cursor.execute("INSERT INTO JobTags (job_id, tag_id) VALUES (%s, %s)", (job_id, tag_id))
            connection.commit()

        return jsonify({"status": "success", "message": "Job updated successfully"}), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 삭제할 공고
        cursor.execute("SELECT id FROM Jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()

        if not job:
            return jsonify({"status": "error", "message": "Job not found."}), 404

        # 다른 테이블에 있는 해당 공고의 데이터 삭제
        cursor.execute("DELETE FROM Favorites WHERE job_id = %s", (job_id,))
        connection.commit()

        cursor.execute("DELETE FROM Applications WHERE job_id = %s", (job_id,))
        connection.commit()

        cursor.execute("DELETE FROM JobTags WHERE job_id = %s", (job_id,))
        connection.commit()

        # 삭제
        cursor.execute("DELETE FROM Jobs WHERE id = %s", (job_id,))
        connection.commit()

        return jsonify({"status": "success", "message": "Job deleted successfully."}), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/<int:job_id>', methods=['GET'])
def get_job_detail(job_id):
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # Jobs, Companies
        query_job = """
            SELECT j.id, j.title, j.salary, j.career, j.education, j.employment, j.deadline, j.link, j.views,
                   c.name AS company_name, c.link AS company_link,
                   l.region, l.district
            FROM Jobs j
            JOIN Companies c ON j.company_id = c.id
            JOIN Locations l ON j.location_id = l.id
            WHERE j.id = %s
        """
        cursor.execute(query_job, (job_id,))
        job = cursor.fetchone()

        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404

        # 조회수 증가
        cursor.execute("UPDATE Jobs SET views = views + 1 WHERE id = %s", (job_id,))
        connection.commit()

        # Updated views fetch
        job['views'] += 1

        # JobTags
        query_tags = """
            SELECT t.name
            FROM JobTags jt
            JOIN Tags t ON jt.tag_id = t.id
            WHERE jt.job_id = %s
        """
        cursor.execute(query_tags, (job_id,))
        tags = [tag['name'] for tag in cursor.fetchall()]

        # 반환 데이터
        job_detail = {
            "id": job['id'],
            "title": job['title'],
            "salary": job['salary'],
            "career": job['career'],
            "education": job['education'],
            "employment": job['employment'],
            "deadline": job['deadline'],
            "link": job['link'],
            "company": {
                "name": job['company_name'],
                "link": job['company_link']
            },
            "location": {
                "region": job['region'],
                "district": job['district']
            },
            "views": job['views'],
            "tags": tags
        }

        return jsonify({"status": "success", "data": job_detail}), 200

    except Exception as e:
        print(f"Error processing job_id={job_id}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
