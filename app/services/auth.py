import re
import sqlite3
import string
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from pwdlib import PasswordHash

from app.database import DATABASE_PATH, get_connection


USERNAME_PATTERN = re.compile(r"^[a-z0-9_-]{5,20}$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 16
PASSWORD_ALLOWED_CHARACTERS = frozenset(
    string.ascii_letters + string.digits + string.punctuation
)

password_hash = PasswordHash.recommended()
# 존재하지 않는 아이디에도 Argon2 검증을 수행해, 응답 시간 차이로
# 사용자 존재 여부를 추측하기 어렵게 만든다. 실제 비밀번호나 비밀 값은 아니다.
DUMMY_PASSWORD = "dummy-password-for-timing-check"
DUMMY_PASSWORD_HASH = password_hash.hash(DUMMY_PASSWORD)


@dataclass(frozen=True, slots=True)
class User:
    id: int
    username: str
    created_at: str


class AuthValidationError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class DuplicateUsernameError(ValueError):
    pass


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> str:
    normalized_username = normalize_username(username)
    if not USERNAME_PATTERN.fullmatch(normalized_username):
        raise AuthValidationError(
            "username",
            "아이디는 영문 소문자, 숫자, 하이픈, 밑줄만 사용해 5~20자로 입력해 주세요.",
        )
    return normalized_username


def validate_password(password: str, password_confirmation: str) -> None:
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise AuthValidationError(
            "password",
            "비밀번호는 8~16자로 입력해 주세요.",
        )
    if any(character not in PASSWORD_ALLOWED_CHARACTERS for character in password):
        raise AuthValidationError(
            "password",
            "비밀번호에는 공백 없이 영문 대소문자, 숫자, 특수문자만 사용할 수 있습니다.",
        )
    if password.isdigit():
        raise AuthValidationError(
            "password",
            "비밀번호는 숫자로만 구성할 수 없습니다.",
        )
    if password != password_confirmation:
        raise AuthValidationError(
            "password_confirmation",
            "비밀번호와 비밀번호 확인이 일치하지 않습니다.",
        )


def register_user(
    username: str,
    password: str,
    password_confirmation: str,
    database_path: str | Path = DATABASE_PATH,
) -> User:
    normalized_username = validate_username(username)
    validate_password(password, password_confirmation)

    with closing(get_connection(database_path)) as connection:
        # 일반적인 중복 요청을 먼저 확인해 불필요한 비밀번호 해시 생성을 피하고,
        # 사용자에게 명확한 중복 아이디 오류를 반환한다.
        existing_user = connection.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()
        if existing_user is not None:
            raise DuplicateUsernameError("이미 사용 중인 아이디입니다.")

        hashed_password = password_hash.hash(password)
        try:
            # 사전 조회 이후 다른 요청이 같은 아이디를 먼저 등록할 수 있으므로,
            # DB의 UNIQUE 제약을 최종 방어선으로 사용한다.
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (normalized_username, hashed_password),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            if "UNIQUE constraint failed: users.username" in str(error):
                raise DuplicateUsernameError(
                    "이미 사용 중인 아이디입니다."
                ) from error
            raise

        user_row = connection.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    if user_row is None:
        raise RuntimeError("생성된 사용자 정보를 조회할 수 없습니다.")
    return _row_to_user(user_row)


def authenticate_user(
    username: str,
    password: str,
    database_path: str | Path = DATABASE_PATH,
) -> User | None:
    normalized_username = normalize_username(username)
    credentials_follow_policy = bool(
        USERNAME_PATTERN.fullmatch(normalized_username)
    ) and (
        PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
        and all(
            character in PASSWORD_ALLOWED_CHARACTERS for character in password
        )
        and not password.isdigit()
    )

    if not credentials_follow_policy:
        password_hash.verify(DUMMY_PASSWORD, DUMMY_PASSWORD_HASH)
        return None

    with closing(get_connection(database_path)) as connection:
        user_row = connection.execute(
            "SELECT id, username, password_hash, created_at "
            "FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()

    if user_row is None:
        password_hash.verify(DUMMY_PASSWORD, DUMMY_PASSWORD_HASH)
        return None

    if not password_hash.verify(password, user_row["password_hash"]):
        return None

    return _row_to_user(user_row)


def get_user_by_id(
    user_id: int,
    database_path: str | Path = DATABASE_PATH,
) -> User | None:
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        return None

    with closing(get_connection(database_path)) as connection:
        user_row = connection.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if user_row is None:
        return None
    return _row_to_user(user_row)


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        created_at=row["created_at"],
    )
