from app.Crawling import CSV_to_DB
from flask import Flask
from app.routes import auth, jobs, applications, bookmarks, resumes
from flask_swagger_ui import get_swaggerui_blueprint
from flask_jwt_extended import JWTManager

SWAGGER_URL = '/swagger'
API_URL = '/swagger.yaml'

app = Flask(__name__)


swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

app.config['JWT_SECRET_KEY'] = 'WSD_Assignment-03'  # JWT 서명 키
app.config['JWT_TOKEN_LOCATION'] = ['headers']  # 토큰을 받는 위치
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 15 * 60  # 15분

jwt = JWTManager(app)

app.register_blueprint(auth.bp, url_prefix='/auth')
app.register_blueprint(jobs.bp, url_prefix='/jobs')
app.register_blueprint(applications.bp, url_prefix='/applications')
app.register_blueprint(bookmarks.bp, url_prefix='/bookmarks')
app.register_blueprint(resumes.bp, url_prefix='/resumes')

@app.route('/swagger.yaml')
def swagger_spec():
    with open('app/swagger.yaml', 'r') as file:
        return file.read()

# 스크립트를 실행하려면 여백의 녹색 버튼을 누릅니다.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

