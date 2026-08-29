# 협업 규칙

## 1. 브랜치 구성

이 프로젝트는 `main`과 Issue 단위 작업 브랜치만 사용하는 GitHub Flow를 적용합니다.

- `main`: 항상 실행·배포 가능한 상태를 유지합니다.
- `develop`: 사용하지 않습니다.
- 작업 브랜치: `feature/<issue-number>-<kebab-topic>`

예시:

```text
feature/12-login
feature/18-chat-history
```

빈 저장소를 만들기 위한 최초 bootstrap 커밋 이후에는 `main`에 직접 push하지 않습니다.

## 2. 작업 시작

1. GitHub에 작업 단위 Issue를 만듭니다.
2. 담당자가 없는 Issue 중 원하는 작업을 선택합니다.
3. 자신을 assignee로 지정하고 착수 댓글을 남깁니다.
4. 최신 `main`을 받은 뒤 Issue 번호가 포함된 브랜치를 만듭니다.

```bash
git switch main
git pull origin main
git switch -c feature/<issue-number>-<topic>
```

한 사람이 동시에 진행하는 주 작업 Issue는 1개를 원칙으로 합니다.

## 3. 커밋 메시지

```text
<type>(<scope>): <구체적인 변경 내용>
```

사용할 type:

- `feat`: 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `test`: 테스트 추가·수정
- `refactor`: 동작을 바꾸지 않는 구조 개선
- `chore`: 설정·도구 변경

예시:

```text
feat(auth): add login validation
test(chat): cover API timeout
docs: explain local setup
```

`update`, `fix`, `wip`, `final`처럼 변경 대상을 알 수 없는 메시지는 사용하지 않습니다. 평가 횟수를 채우기 위한 의미 없는 커밋 분할도 금지합니다.

## 4. Pull Request

작업이 끝나면 `main`을 대상으로 PR을 만듭니다.

- PR 하나는 Issue 하나의 범위에 집중합니다.
- 제목은 변경 내용을 구체적으로 작성합니다.
- 본문에 What, Why, How verified를 작성합니다.
- `Closes #<issue-number>`로 Issue를 연결합니다.
- 작성자가 아닌 팀원에게 리뷰를 요청합니다.
- 리뷰 의견에 답변하거나 수정 커밋으로 반영합니다.

## 5. 리뷰와 병합

병합 조건:

- 팀원 1명 이상의 승인
- `LGTM`만이 아닌 구체적인 리뷰 코멘트 1개 이상
- 모든 리뷰 대화 해결
- 준비된 자동 검사가 있다면 모두 통과

팀원별 유의미한 커밋 이력을 보존하기 위해 **Create a merge commit**만 사용합니다. Squash merge와 rebase merge는 사용하지 않습니다.

병합 후 작업 브랜치는 삭제합니다.

## 6. main 보호 규칙

GitHub에서 `main`에 다음 보호 규칙을 적용합니다.

- Pull Request를 통한 변경 필수
- 승인 1명 필수
- 새 커밋이 추가되면 이전 승인 무효화
- 병합 전 모든 대화 해결
- force push 금지
- 브랜치 삭제 금지
- 관리자도 규칙 우회 금지

CI가 실제로 동작하기 시작한 뒤에는 해당 상태 검사도 병합 조건에 추가합니다.

## 7. 금지 사항

- 팀 합의 없는 force push 또는 공유 브랜치 rebase
- 다른 팀원의 변경을 임의로 제거하는 충돌 해결
- API 키·비밀번호·세션 값 커밋
- 리뷰 없이 본인 PR을 직접 병합
