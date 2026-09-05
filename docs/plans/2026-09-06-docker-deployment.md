# Docker 배포 구현 계획

**목표:** 과제 전용 OCI VM에 GitHub Actions로 ARM64 이미지를 배포하고 HTTPS로 검증한다.

**구조:** GitHub 제공 ARM64 runner가 테스트와 이미지 빌드를 수행한다. 과제 전용 SSH 키는 커밋 SHA를 지정한 배포 명령만 실행한다. 관리자 소유 Compose 설정이 비특권 앱과 영속 SQLite 경로를 고정한다. Caddy가 HTTPS를 제공한다.

**기술:** Docker, Compose, Python unittest, OpenSSH, Caddy, GitHub Actions.

1. `tests/test_deploy.py`에 다른 앱 이미지 태그·잘못된 SHA 거부 테스트 작성 후 실패 확인.
2. `Dockerfile`, `deploy/compose.yaml`, 배포 명령 구현 후 기존 DB 테스트와 신규 테스트 통과 확인.
3. VM에 전용 계정·키·관리자 소유 설정 설치. 일반 명령·포워딩 차단 확인.
4. feature 브랜치 push로 Actions 배포. HTTPS·정적 파일·SQLite 재배포 영속성 확인.
5. push 트리거를 main으로 제한하고 PR 생성. 미구현 인증·AI 기능에 대한 전체 검증은 #16 후속 항목으로 유지.

## 범위

- 서비스 주소: `https://www.aichat-sample.kro.kr` (현재 wildcard DNS 사용).
- 기존 Jenkins·Nginx 데이터는 유지한다.
- SSH 계정에 Docker 그룹·일반 sudo·대화형 셸 접근 권한을 부여하지 않는다.
- 컨테이너는 커널을 공유하며 별도 VM과 동등한 보안 경계를 보장하지 않는다.
- 운영 키나 앱 비밀값은 저장소에 커밋하지 않는다.
