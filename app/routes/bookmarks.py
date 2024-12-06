import pymysql
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.utils.DB_Utils import get_db_connection
from app.utils.jwt_token import jwt_required

bp = Blueprint('bookmarks', __name__, url_prefix='/bookmarks')

# 북마크 추가/제거
@bp.route('/', methods=['POST'])
@jwt_required
def toggle_bookmark():
    user_id = get_jwt_identity()
    data = request.json
    job_id = data.get('job_id')

    if not job_id:
        return jsonify({"status": "error", "message": "Job ID is required"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # 북마크 존재 여부 확인
        cursor.execute(
            "SELECT id FROM Favorites WHERE user_id = %s AND job_id = %s",
            (user_id, job_id)
        )
        bookmark = cursor.fetchone()

        if bookmark:
            # 북마크 제거
            cursor.execute(
                "DELETE FROM Favorites WHERE id = %s",
                (bookmark['id'],)
            )
            connection.commit()
            return jsonify({"status": "success", "message": "Bookmark removed"}), 200
        else:
            # 북마크 추가
            cursor.execute(
                "INSERT INTO Favorites (user_id, job_id) VALUES (%s, %s)",
                (user_id, job_id)
            )
            connection.commit()
            return jsonify({"status": "success", "message": "Bookmark added"}), 201

    except Exception as e:
        connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/', methods=['GET'])
@jwt_required
def get_bookmarks():
    user_id = get_jwt_identity()  # JWT에서 사용자 ID 추출
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)

    if not user_id:
        return jsonify({"status": "error", "message": "User ID is required"}), 400

    offset = (page - 1) * per_page

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # 북마크 목록 조회 쿼리 (최신순으로 정렬)
        query = """
            SELECT f.id AS bookmark_id, f.user_id, j.id AS job_id, j.title, c.name AS company_name, j.salary, j.deadline
            FROM Favorites f
            JOIN Jobs j ON f.job_id = j.id
            JOIN Companies c ON j.company_id = c.id
            WHERE f.user_id = %s
            ORDER BY f.favorited_at DESC
            LIMIT %s OFFSET %s
        """
        params = (user_id, per_page, offset)

        cursor.execute(query, params)
        bookmarks = cursor.fetchall()

        if not bookmarks:
            return jsonify({
                "status": "success",
                "data": [],
                "message": "No bookmarks found."
            }), 200

        return jsonify({
            "status": "success",
            "data": bookmarks,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_items": len(bookmarks)
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
