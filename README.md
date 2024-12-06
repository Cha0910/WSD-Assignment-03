
# WSD-2분반-202011745-차재현-3차과제


## 주요 기능
- **JWT 인증**: Flask-JWT-Extended를 사용한 사용자 인증 및 토큰 발급.
- **API 제공**: `swagger.yaml`로 정의된 API 문서를 기반으로 다양한 엔드포인트 제공.
- **크롤링**: `Crawling` 모듈을 사용하여 외부 데이터를 수집하고 CSV 파일로 변환.
- **데이터 처리**: CSV 데이터를 데이터베이스로 변환 및 처리.
- **데이터베이스 유틸리티**: `DB_Utils.py`를 사용하여 데이터베이스 관리.

---

## 설치 및 실행 방법

### 1. 의존성 설치
프로젝트를 실행하려면 먼저 Python 가상환경을 생성하고 패키지를 설치해야 합니다.

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 서버 실행
아래 명령어를 통해 Flask 서버를 실행합니다:

```bash
python main.py
```

서버가 실행된 후, 브라우저에서 로컬 서버 `http://127.0.0.1:3000/swagger` 또는 `http://113.198.66.75:13033/swagger/` 로 접속하여 Swwager 문서를 확인 및 API를 사용할 수 있습니다.


---
## 파일 구조
```
WSD-Assignment-03/
├── main.py                # 메인 실행 파일
├── requirements.txt       # 프로젝트 패키지 정의
├── app/
│   ├── swagger.yaml       # Swagger API 문서
│   ├── Crawling/          # 데이터 크롤링
│   ├── routes/            # Flask 라우트 정의
│   ├── utils/             # 유틸리티 모듈 (DB, JWT)
├── data/                  # CSV 데이터 파일
```

---