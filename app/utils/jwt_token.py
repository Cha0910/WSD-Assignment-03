import jwt
import datetime

SECRET_KEY = "WSD_Assignment-03"
REFRESH_SECRET_KEY = "202011745-cjh"

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

def decode_token(token, secret_key):
    try:
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
