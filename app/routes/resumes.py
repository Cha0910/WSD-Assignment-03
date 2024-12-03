import pymysql
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.DB_Utils import get_db_connection

bp = Blueprint('resumes', __name__, url_prefix='/resumes')

# 이력서 생성
@bp.route('/', methods=['POST'])
@jwt_required()
def create_resume():
    data = request.json
    user_id = get_jwt_identity()

    # 입력 데이터 검증
    resume_link = data.get('resume_link', None)

    if not resume_link:
        return jsonify({"status": "error", "message": "Resume Link is required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # DB에 이력서 저장
        cursor.execute("""
            INSERT INTO Resumes (user_id, content)
            VALUES (%s, %s)
        """, (user_id, resume_link))
        connection.commit()
        resume_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Resume created successfully",
            "resume_id": resume_id
        }), 201

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

# 이력서 조회
@bp.route('/', methods=['GET'])
@jwt_required()
def get_resumes():
    user_id = get_jwt_identity()
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)
    offset = (page - 1) * per_page

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # 이력서 목록 조회
        query = """
            SELECT id, content, created_at, updated_at
            FROM Resumes
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (user_id, per_page, offset))
        resumes = cursor.fetchall()

        if not resumes:
            return jsonify({"status": "success", "data": [], "message": "No resumes found"}), 200

        return jsonify({
            "status": "success",
            "data": resumes,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_items": len(resumes)
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

# 이력서 수정
@bp.route('/<int:resume_id>', methods=['PUT'])
@jwt_required()
def update_resume(resume_id):
    data = request.json
    user_id = get_jwt_identity()

    # 입력 데이터 검증
    resume_link = data.get('resume_link')

    # 업데이트할 데이터가 없으면 에러 반환
    if not resume_link:
        return jsonify({"status": "error", "message": "No fields to update provided"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 이력서 존재 여부 확인
        cursor.execute("SELECT id FROM Resumes WHERE id = %s AND user_id = %s", (resume_id, user_id))
        resume = cursor.fetchone()

        if not resume:
            return jsonify({"status": "error", "message": "Resume not found or unauthorized"}), 404

        # 업데이트 쿼리 실행
        cursor.execute("UPDATE Resumes SET content = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (resume_link, resume_id))
        connection.commit()

        return jsonify({"status": "success", "message": "Resume updated successfully"}), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
