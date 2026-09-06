import secrets

from fastapi import Request

from app.services.auth import User, get_user_by_id


USER_SESSION_KEY = "user_id"
CSRF_SESSION_KEY = "csrf_token"


def get_current_user(request: Request) -> User | None:
    user_id = request.session.get(USER_SESSION_KEY)
    if user_id is None:
        return None

    user = get_user_by_id(user_id, request.app.state.database_path)
    if user is None:
        request.session.clear()
    return user


def get_csrf_token(request: Request) -> str:
    csrf_token = request.session.get(CSRF_SESSION_KEY)
    if not isinstance(csrf_token, str):
        csrf_token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = csrf_token
    return csrf_token


def is_valid_csrf_token(request: Request, submitted_token: str) -> bool:
    session_token = request.session.get(CSRF_SESSION_KEY)
    return (
        isinstance(session_token, str)
        and bool(submitted_token)
        and secrets.compare_digest(session_token, submitted_token)
    )


def establish_user_session(request: Request, user_id: int) -> None:
    request.session.clear()
    request.session[USER_SESSION_KEY] = user_id
    request.session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)


def clear_user_session(request: Request) -> None:
    request.session.clear()
