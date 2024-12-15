import pymysql
import base64
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity, get_jwt
)
from app.utils.DB_Utils import get_db_connection
from app.utils.jwt_token import create_refresh_token, decode_refresh_token, REFRESH_SECRET_KEY, jwt_required
bp = Blueprint('auth', __name__, url_prefix='/auth')

# 회원가입
@bp.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password or not name:
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

    # 비밀번호 인코딩
    encoded_password = base64.b64encode(password.encode()).decode()

    # DB 저장
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO Users (email, password, name) VALUES (%s, %s, %s)",
            (email, encoded_password, name)
        )
        connection.commit()

        cursor.execute("SELECT id, email, name, created_at, updated_at FROM Users WHERE email = %s", (email,))
        new_user = cursor.fetchone()

        # refresh_token 저장
        user_id = new_user[0]
        refresh_token = create_refresh_token(user_id)
        cursor.execute("INSERT INTO RefreshTokens (user_id, token) VALUES (%s, %s)", (user_id, refresh_token))
        connection.commit()

        return jsonify({"status": "success",
                        "message": "User registered successfully.,",
                        "data": new_user,
                        "refresh_token": refresh_token.decode('utf-8')
        }), 201
    except pymysql.IntegrityError:
        return jsonify({"status": "error", "message": "Email already exists."}), 400
    finally:
        cursor.close()
        connection.close()

# 로그인
@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

    decoded_password = base64.b64encode(password.encode()).decode()

    # 사용자 인증
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT id FROM Users WHERE email = %s AND password = %s",
            (email, decoded_password)
        )
        user = cursor.fetchone()
        if user:
            user_id = user[0]
            # LoginHistory에 기록 추가
            cursor.execute(
                "INSERT INTO LoginHistory (user_id) VALUES (%s)",
                 (user_id,)
            )
            connection.commit()

            new_access_token = create_access_token(identity=str(user_id))
            new_refresh_token = create_refresh_token(user_id)

            # Refresh Token을 데이터베이스에 저장 (기존 토큰 무효화)
            cursor.execute("REPLACE INTO RefreshTokens (user_id, token) VALUES (%s, %s)", (user_id, new_refresh_token))
            connection.commit()

            return jsonify({"status": "success",
                            "message": "Login successful.",
                            "new_refresh_token": new_refresh_token.decode('utf-8'),
                            "new_access_token": new_access_token.decode('utf-8')}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid credentials."}), 401
    finally:
        cursor.close()
        connection.close()

# 토큰 refresh
@bp.route('/refresh', methods=['POST'])
def refresh_token():
    data = request.json
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"status": "error", "message": "Refresh token is required"}), 400

    try:
        # Refresh Token 검증
        decoded = decode_refresh_token(refresh_token, REFRESH_SECRET_KEY)
        user_id = decoded.get("user_id")

        # 데이터베이스에 Refresh Token이 존재하는지 확인
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM RefreshTokens WHERE token = %s AND user_id = %s", (refresh_token, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Invalid refresh token"}), 401

        # 새로운 Access Token 발급
        new_access_token = create_access_token(identity=str(user_id))
        return jsonify({"status": "success", "access_token": new_access_token}), 200

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 401

    finally:
        cursor.close()
        connection.close()



@bp.route('/profile', methods=['PUT'])
@jwt_required  # JWT 인증 필요
def update_profile():
    data = request.json
    user_id = get_jwt_identity()  # 현재 로그인된 사용자의 ID

    # 입력된 데이터 가져오기
    new_password = data.get('password')
    new_name = data.get('name')

    # 수정할 데이터가 없으면 에러 반환
    if not new_password and not new_name:
        return jsonify({"status": "error", "message": "Invalid refresh token"}), 400

    # 데이터베이스 연결
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 수정 쿼리 작성
        update_fields = []
        params = []

        if new_password:
            encoded_password = base64.b64encode(new_password.encode()).decode()
            update_fields.append("password = %s")
            params.append(encoded_password)

        if new_name:
            update_fields.append("name = %s")
            params.append(new_name)

        # 수정할 데이터가 존재할 경우에만 실행
        if update_fields:
            params.append(user_id)  # WHERE 절의 사용자 ID 추가
            query = f"UPDATE Users SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, tuple(params))
            connection.commit()

        return jsonify({"status": "success", "message": "User information has been successfully updated."}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


@bp.route('/info', methods=['GET'])
@jwt_required  # JWT 인증 필요
def get_info():
    user_id = get_jwt_identity()  # 현재 로그인된 사용자의 ID

    # 데이터베이스 연결
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 사용자 정보 조회
        cursor.execute(
            "SELECT id, email, name, created_at, updated_at FROM Users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "error", "message": "User not found."}), 404

        # 최근 로그인 기록 조회
        cursor.execute(
            "SELECT login_time FROM LoginHistory WHERE user_id = %s ORDER BY login_time DESC LIMIT 1",
            (user_id,)
        )
        last_login = cursor.fetchone()

        # 응답 데이터 생성
        user_data = {
            "id": user[0],
            "email": user[1],
            "name": user[2],
            "created_at": user[3],
            "updated_at": user[4],
            "last_login": last_login[0] if last_login else None,  # 최근 로그인 시간
        }
        return jsonify({"status": "success", "data": user_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@bp.route('/delete', methods=['DELETE'])
@jwt_required  # JWT 인증 필요
def delete_account():
    user_id = get_jwt_identity()  # 현재 로그인된 사용자의 ID

    # 데이터베이스 연결
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM Resumes WHERE user_id = %s", (user_id,))
        connection.commit()

        cursor.execute("DELETE FROM Applications WHERE user_id = %s", (user_id,))
        connection.commit()

        cursor.execute("DELETE FROM Favorites WHERE user_id = %s", (user_id,))
        connection.commit()

        cursor.execute("DELETE FROM Resumes WHERE user_id = %s", (user_id,))
        connection.commit()

        # 사용자 데이터 삭제
        cursor.execute("DELETE FROM Users WHERE id = %s", (user_id,))
        connection.commit()

        return jsonify({"status": "success", "message": "Account has been successfully deleted."}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()