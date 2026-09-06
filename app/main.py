import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import DATABASE_PATH, init_db
from app.routers import auth, health, pages


BASE_DIR = Path(__file__).resolve().parent
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8


def _resolve_session_secret(session_secret: str | None) -> str:
    resolved_secret = session_secret or os.getenv("SESSION_SECRET", "")
    if len(resolved_secret) < 32:
        raise RuntimeError("SESSION_SECRET은 32자 이상으로 설정해야 합니다.")
    return resolved_secret


def _resolve_https_only(session_https_only: bool | None) -> bool:
    if session_https_only is not None:
        return session_https_only

    configured_value = os.getenv("SESSION_HTTPS_ONLY", "false").strip().lower()
    if configured_value in {"true", "1", "yes", "on"}:
        return True
    if configured_value in {"false", "0", "no", "off"}:
        return False
    raise RuntimeError("SESSION_HTTPS_ONLY는 true 또는 false로 설정해야 합니다.")


def create_app(
    database_path: str | Path = DATABASE_PATH,
    session_secret: str | None = None,
    session_https_only: bool | None = None,
) -> FastAPI:
    resolved_database_path = Path(database_path)
    resolved_session_secret = _resolve_session_secret(session_secret)
    resolved_https_only = _resolve_https_only(session_https_only)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db(resolved_database_path)
        yield

    application = FastAPI(
        title="Codyssey 07-01",
        description="FastAPI와 Jinja2로 구성한 웹 기반 AI 챗봇 서비스",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database_path = resolved_database_path
    application.add_middleware(
        SessionMiddleware,
        secret_key=resolved_session_secret,
        session_cookie="codyssey_session",
        max_age=SESSION_MAX_AGE_SECONDS,
        same_site="lax",
        https_only=resolved_https_only,
    )

    application.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "static")),
        name="static",
    )

    application.include_router(pages.router)
    application.include_router(auth.router)
    application.include_router(health.router)
    return application


load_dotenv()
app = create_app()
