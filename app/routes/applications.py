import pymysql
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.utils.DB_Utils import get_db_connection
from app.utils.jwt_token import jwt_required

bp = Blueprint('applications', __name__, url_prefix='/applications')

@bp.route('/', methods=['POST'])
@jwt_required
def apply_for_job():
    data = request.json
    user_id = get_jwt_identity()  # JWT에서 사용자 ID 추출

    # 입력 데이터
    job_id = data.get('job_id')
    resume_link = data.get('resume_link', None)

    # 필수 필드 검증
    if not job_id:
        return jsonify({"status": "error", "message": "Job ID is required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # 유효한 공고인지 확인
        cursor.execute("SELECT id FROM Jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()
        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404

        # 중복 지원 체크
        cursor.execute("SELECT id FROM Applications WHERE user_id = %s AND job_id = %s", (user_id, job_id))
        existing_application = cursor.fetchone()
        if existing_application:
            return jsonify({"status": "error", "message": "You have already applied for this job"}), 400

        # 이력서 검색 또는 추가
        resume_id = None
        if resume_link:
            cursor.execute("SELECT id FROM Resumes WHERE user_id = %s AND content = %s", (user_id, resume_link))
            resume = cursor.fetchone()

            if resume:
                resume_id = resume['id']
            else:
                cursor.execute("INSERT INTO Resumes (user_id, content) VALUES (%s, %s)", (user_id, resume_link))
                connection.commit()
                resume_id = cursor.lastrowid

        # 지원 정보 저장
        cursor.execute("""
            INSERT INTO Applications (user_id, job_id, resume_id)
            VALUES (%s, %s, %s)
        """, (user_id, job_id, resume_id))
        connection.commit()

        return jsonify({"status": "success", "message": "Application submitted successfully"}), 201

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/', methods=['GET'])
@jwt_required
def get_applications():
    user_id = get_jwt_identity()  # JWT에서 사용자 ID 추출
    status = request.args.get('status', default=None, type=str)
    order = request.args.get('order', default='asc', type=str)  # 정렬 순서
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)

    # user_id가 없으면 에러 반환
    if not user_id:
        return jsonify({"status": "error", "message": "user_id is required"}), 400

    # 정렬 검증
    if order not in ['asc', 'desc']:
        return jsonify({"status": "error", "message": "Invalid order. Use 'asc' or 'desc'."}), 400

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        query = """
            SELECT a.id, a.user_id, a.job_id, j.title, a.resume_id, a.status, a.applied_at
            FROM Applications a
            JOIN Jobs j ON a.job_id = j.id
            WHERE a.user_id = %s
        """
        params = [user_id]

        # 상태별 필터링 추가
        if status:
            query += " AND a.status = %s"
            params.append(status)

        # 정렬 기준: created_at
        query += f" ORDER BY a.applied_at {order.upper()}"

        # 페이지네이션 추가
        query += " LIMIT %s OFFSET %s"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])

        # 쿼리 실행
        cursor.execute(query, tuple(params))
        applications = cursor.fetchall()

        # 결과 반환
        return jsonify({
            "status": "success",
            "data": applications,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_items": len(applications)
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/<int:application_id>', methods=['DELETE'])
@jwt_required
def cancel_application(application_id):
    user_id = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # 지원 항목 확인 및 상태 체크
        query = "SELECT id, status FROM Applications WHERE id = %s AND user_id = %s"
        cursor.execute(query, (application_id, user_id))
        application = cursor.fetchone()

        if not application:
            return jsonify({"status": "error", "message": "Application not found"}), 404

        if application['status'] != 'pending':
            return jsonify({"status": "error", "message": "Only pending applications can be canceled"}), 400

        # 상태 변경
        query = "UPDATE Applications SET status = 'canceled' WHERE id = %s"
        cursor.execute(query, (application_id,))
        connection.commit()

        return jsonify({"status": "success", "message": "Application status updated to 'canceled'"}), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()