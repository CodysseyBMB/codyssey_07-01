# Codyssey 07-01

FastAPI, Jinja2, SQLite 기반 웹 AI 챗봇 팀 프로젝트입니다.

현재 FastAPI 애플리케이션, Jinja2 기본 화면, 정적 파일 제공 및 상태 확인
엔드포인트와 사용자 테이블 초기화까지 구성되어 있습니다. 인증, 채팅과 AI API
연동은 후속 Issue에서 구현할 예정입니다.

## 기술 스택

- Python
- FastAPI
- Jinja2
- SQLite

## 로컬 실행 방법

저장소 루트에서 다음 명령을 순서대로 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

서버가 시작되면 다음 주소를 확인할 수 있습니다.

- 기본 화면: <http://127.0.0.1:8000/>
- 상태 확인: <http://127.0.0.1:8000/health>
- API 문서: <http://127.0.0.1:8000/docs>

서버를 종료할 때는 실행 중인 터미널에서 `Ctrl+C`를 누릅니다.

## 로컬 테스트 방법

데이터베이스 자동 테스트를 먼저 실행합니다.

```bash
python3 -m unittest discover -s tests
```

서버가 실행 중인 상태에서 별도의 터미널을 열고 다음 명령을 실행합니다.

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/static/css/style.css
git check-ignore .env
```

예상 결과:

- `/health`: `{"status":"ok"}`
- 기본 화면과 CSS 요청: 각각 HTTP `200`
- `git check-ignore .env`: `.env` 출력

## 데이터베이스

애플리케이션을 시작하면 프로젝트 루트의 `data/codyssey.db`가 자동으로
생성됩니다. 초기화는 반복 실행해도 기존 데이터를 삭제하지 않습니다.

### 초기화 방식

데이터베이스 초기화에는 `app/schema.sql`과 `app/database.py`를 사용합니다.

1. FastAPI가 시작되면 `app/main.py`의 lifespan이 `init_db()`를 호출합니다.
2. `init_db()`는 `data` 디렉터리를 준비하고 `app/schema.sql`을 읽습니다.
3. `sqlite3.connect()`가 `data/codyssey.db`에 연결하며, 파일이 없으면 새로
   생성합니다.
4. `executescript()`가 스키마 SQL을 실행해 필요한 테이블과 제약조건을
   생성합니다.

현재 스키마 SQL에는 `CREATE TABLE IF NOT EXISTS users`만 정의되어 있으므로
실제 DB에도 애플리케이션 테이블은 `users` 하나만 생성됩니다. DB가 이미 있으면
같은 파일을 사용하며, `IF NOT EXISTS`에 의해 기존 테이블과 데이터는 유지됩니다.

서버를 실행하지 않고 DB만 초기화하려면 저장소 루트에서 다음 명령을 실행합니다.

```bash
python3 -c "from app.database import init_db; init_db()"
```

생성 결과는 SQLite 명령으로 확인할 수 있습니다.

```bash
sqlite3 data/codyssey.db ".tables"
sqlite3 data/codyssey.db ".schema users"
```

현재 `users` 테이블은 다음 정보를 저장합니다.

- 자동 생성되는 사용자 식별자
- 중복이 허용되지 않는 로그인 아이디
- 평문이 아닌 비밀번호 해시
- UTC 기준 계정 생성 시각

DB 스키마는 기본키, 필수값, 로그인 아이디 고유성과 생성 시각 기본값처럼
데이터 무결성에 필요한 제약만 담당합니다. 로그인 아이디의 길이·허용 문자와
비밀번호 정책 및 해시 생성·검증은 후속 인증 서비스에서 처리합니다.

로컬 SQLite DB와 관련 임시 파일은 Git 추적 대상에서 제외됩니다.

기본 화면이 보이지 않거나 요청에 실패한다면 다음 항목을 확인합니다.

- 명령을 저장소 루트에서 실행했는지 확인합니다.
- 터미널 프롬프트에 `(.venv)`가 표시되는지 확인합니다.
- `pip install -r requirements.txt`가 오류 없이 완료됐는지 확인합니다.
- `8000` 포트를 사용하는 다른 프로그램이 있는지 확인합니다.

## 환경 변수 관리

현재 스캐폴딩 단계에서 필수 환경 변수는 없습니다. 이후 AI API 키와 같은
민감정보가 필요해지면 `.env.example`의 키 이름을 참고해 `.env`에 실제 값을
작성합니다. `.env`는 Git에 포함하지 않습니다.

## 브랜치 전략

- `main`: 항상 실행 가능한 상태를 유지하는 기본 브랜치
- `feature/<issue-number>-<topic>`: Issue 단위 작업 브랜치
- `main` 직접 push 금지
- 모든 변경은 Pull Request를 통해 병합
- 팀원별 커밋 이력을 보존하기 위해 merge commit 사용

자세한 작업 절차는 [협업 규칙](docs/CONTRIBUTING.md)을 확인합니다.

## 운영 배포

Docker·GitHub Actions 배포 절차는 [배포 문서](docs/DEPLOYMENT.md)를 참고합니다.

## 과제 원문

- [Term Project 요구사항](docs/subject.pdf)
