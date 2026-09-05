# Docker 배포

## 구성

- 서비스: `https://www.aichat-sample.kro.kr`
- DNS: 해당 호스트의 A 레코드를 과제 VM 공인 IP에 연결한다. `*.aichat-sample.kro.kr`은 기본 도메인 자체를 포함하지 않는다.
- GitHub 제공 ARM64 runner에서 테스트 후 이미지를 빌드한다.
- 전용 SSH 계정 `codyssey-deploy`에 이미지 압축 파일과 커밋 SHA를 전달한다.
- 서버는 관리자 소유 설정으로 앱을 교체하고 Docker healthcheck 통과를 기다린다. 실패하면 직전 성공 이미지가 있을 때 복원한다.
- Caddy가 HTTPS를 종료하고 `127.0.0.1:18000`의 앱으로 전달한다.
- 현재 앱은 기본 화면과 DB 초기화 단계다. 인증·실제 AI 채팅 등 #16의 전체 기능 검증은 선행 Issue 완료 후 수행한다.

## 최초 설치 (VM 관리자)

`deploy/compose.yaml`, `deploy/deploy.py`, `deploy/ssh-gate.sh`, `deploy/proxy.yaml`, `deploy/Caddyfile`을 `/opt/codyssey-aichat`에 설치한다. 이 디렉터리와 파일은 root 소유이며 배포 계정에 쓰기 권한을 주지 않는다. `ssh-gate.sh`는 실행 가능해야 한다.

- `/var/lib/codyssey-aichat`: 앱 UID/GID `10001:10001` 소유, 권한 `700`. SQLite 저장 위치.
- `/opt/codyssey-aichat/app.env`: root 소유, 권한 `600`. 현재 필수 환경 변수 없음. 이후 실제 앱이 지원하는 AI·인증 설정을 여기에 추가한다.
- `/var/lib/codyssey-caddy/data`, `/var/lib/codyssey-caddy/config`: 인증서 영속 저장 위치.
- `/opt/codyssey-aichat/proxy.env`: root 소유 `600`, `ACME_EMAIL=인증서 관리자 이메일` 설정. `kro.kr`의 Let's Encrypt 공유 도메인 발급 한도를 피하기 위해 ZeroSSL ACME를 사용한다. Caddy가 이메일로 EAB 등록을 처리한다.
- 별도 사용자 `codyssey-deploy` 생성. Docker 그룹이나 일반 sudo 권한은 부여하지 않는다.
- 전용 SSH 키를 생성하고 공개키만 서버에 등록한다. 계정 홈과 `.ssh`는 root 소유 `755`, `authorized_keys`는 root 소유 `644`로 SSH가 읽을 수 있게 한다. 개인키는 서버에 복사하지 않는다.

`/etc/ssh/sshd_config.d/65-codyssey-deploy.conf`:

```text
Match User codyssey-deploy
    AuthenticationMethods publickey
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    DisableForwarding yes
    PermitTTY no
    PermitUserRC no
    ForceCommand /opt/codyssey-aichat/ssh-gate.sh
Match all
```

`/etc/sudoers.d/codyssey-deploy` (root 소유, `440`):

```text
codyssey-deploy ALL=(root) NOPASSWD: /usr/bin/python3 /opt/codyssey-aichat/deploy.py *
```

`visudo -cf`와 `sshd -t` 검증 후 SSH를 reload한다. 배포 스크립트는 SHA 형식과 이미지 태그를 검증하며, 업로드는 512MiB로 제한한다.

```bash
sudo docker compose -f /opt/codyssey-aichat/proxy.yaml up -d
```

OCI 네트워크와 호스트 방화벽에서 TCP 80/443을 허용한다. SSH는 Actions runner가 접근할 수 있어야 한다. 임의의 Compose 파일이나 배포 스크립트를 Actions에서 서버로 덮어쓰지 않는다. 해당 파일 변경은 관리자가 검토 후 설치한다.

## GitHub Actions Secrets

| 이름 | 내용 |
|---|---|
| `DEPLOY_HOST` | 과제 VM 주소 |
| `DEPLOY_SSH_KEY` | 과제 전용 SSH 개인키 |
| `DEPLOY_KNOWN_HOSTS` | 관리자 접속에서 확인한 SSH 호스트 키 |

개인키와 운영 환경 파일은 팀원 개발용 `.env`에 포함하지 않는다. 팀 저장소의 workflow 수정자는 배포 키를 사용할 수 있으므로 키 유출 시에도 해당 앱 배포만 가능하도록 서버 측 제한을 유지한다. 컨테이너는 호스트 커널을 공유하며, 본 구성은 별도 VM 수준의 격리나 모든 내부망 통신 차단을 제공하지 않는다.

## 검증과 운영

PR에서는 테스트·빌드만 수행하며 배포 Secret을 사용하지 않는다. main push에서 배포한다.

```bash
curl --fail https://www.aichat-sample.kro.kr/health
curl --fail https://www.aichat-sample.kro.kr/
curl --fail https://www.aichat-sample.kro.kr/static/css/style.css
sudo docker compose -f /opt/codyssey-aichat/proxy.yaml logs --tail 50
sudo docker logs --tail 50 codyssey-aichat-app-1
```

앱 재시작·조회 시 이미지 변수가 필요하다.

```bash
sudo env APP_IMAGE="$(sudo cat /opt/codyssey-aichat/current-image)" \
  docker compose -f /opt/codyssey-aichat/compose.yaml restart app
```

SQLite는 `/var/lib/codyssey-aichat/codyssey.db`에 보존된다. DB 백업은 SQLite backup API 또는 앱 정지 후 파일 복사로 수행한다. 실행 중인 DB 파일만 단순 복사하지 않는다. 이미지 롤백은 DB 스키마를 되돌리지 않으므로 이후 스키마 변경은 별도 검토한다.

이전 이미지는 롤백을 위해 남겨 둔다. 관리자가 `codyssey-aichat` 이미지 중 현재·직전 성공 배포 이외의 불필요한 태그만 정리한다. 기존 Jenkins 등 다른 서비스 이미지를 일괄 정리하지 않는다.
