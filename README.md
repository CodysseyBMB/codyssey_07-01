# Codyssey 07-01

FastAPI, Jinja2, SQLite 기반 웹 AI 챗봇 팀 프로젝트입니다.

현재 FastAPI 애플리케이션, Jinja2 기본 화면, 정적 파일 제공 및 상태 확인
엔드포인트까지 구성되어 있습니다. 인증, 채팅, AI API, SQLite 연동은 후속
Issue에서 구현할 예정입니다.

## 기술 스택

- Python
- FastAPI
- Jinja2
- SQLite (구현 예정)

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

## 과제 원문

- [Term Project 요구사항](docs/subject.pdf)
