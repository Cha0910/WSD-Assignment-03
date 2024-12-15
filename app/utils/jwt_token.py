import jwt
import datetime
from app.utils.DB_Utils import get_db_connection
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import (
    get_jwt_identity, verify_jwt_in_request, decode_token
)
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
REFRESH_SECRET_KEY = os.getenv('REFRESH_SECRET_KEY')

def create_access_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),  # 유효기간: 15분
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),  # 유효기간: 7일
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, REFRESH_SECRET_KEY, algorithm="HS256")

def decode_refresh_token(token, secret_key):
    try:
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # JWT 검증
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            if not user_id:
                return jsonify({"status": "error", "message": "User not authenticated"}), 401

            # 정상적인 access token인 경우
            return func(*args, **kwargs)

        except Exception as e:
            # 만료된 access token 처리
            expired_token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not expired_token:
                return jsonify({"status": "error", "message": "Token is missing"}), 401

            try:
                decoded_token = decode_token(expired_token, allow_expired=True)
                user_id = decoded_token.get('sub')

                if not user_id:
                    return jsonify({"status": "error", "message": "Invalid token: user ID not found"}), 401

                # Refresh token 확인
                connection = get_db_connection()
                cursor = connection.cursor()
                try:
                    cursor.execute("SELECT token FROM RefreshTokens WHERE user_id = %s", (user_id,))
                    refresh_token_entry = cursor.fetchone()
                finally:
                    cursor.close()
                    connection.close()

                if not refresh_token_entry:
                    return jsonify({
                        "status": "error",
                        "message": "Refresh token not found. Please re-authenticate."
                    }), 401

                # 클라이언트에게 refresh token으로 새 access token 발급 요청 안내
                return jsonify({
                    "status": "error",
                    "message": "Access token expired. Use the provided refresh token to obtain a new access token.",
                    "refresh_token": refresh_token_entry[0]
                }), 401

            except Exception as inner_e:
                return jsonify({"status": "error", "message": str(inner_e)}), 401

    return wrapper