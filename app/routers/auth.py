from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.auth import (
    clear_user_session,
    establish_user_session,
    get_csrf_token,
    get_current_user,
    is_valid_csrf_token,
)
from app.services.auth import (
    AuthValidationError,
    DuplicateUsernameError,
    authenticate_user,
    normalize_username,
    register_user,
)


PROJECT_NAME = "Codyssey 07-01"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _template_context(request: Request, **context: Any) -> dict[str, Any]:
    return {
        "request": request,
        "project_name": PROJECT_NAME,
        **context,
    }


def _csrf_error(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context=_template_context(
            request,
            status_code=403,
            title="요청을 확인할 수 없습니다",
            message="페이지를 새로고침한 뒤 다시 시도해 주세요.",
        ),
        status_code=403,
    )


@router.get("/signup", response_class=HTMLResponse, include_in_schema=False)
async def signup_page(request: Request) -> Response:
    if get_current_user(request) is not None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context=_template_context(
            request,
            csrf_token=get_csrf_token(request),
            username="",
            error=None,
        ),
    )


@router.post("/signup", response_class=HTMLResponse, include_in_schema=False)
async def signup(
    request: Request,
    username: str = Form(default=""),
    password: str = Form(default=""),
    password_confirmation: str = Form(default=""),
    csrf_token: str = Form(default=""),
) -> Response:
    if not is_valid_csrf_token(request, csrf_token):
        return _csrf_error(request)
    if get_current_user(request) is not None:
        return RedirectResponse(url="/", status_code=303)

    normalized_username = normalize_username(username)
    try:
        register_user(
            username,
            password,
            password_confirmation,
            request.app.state.database_path,
        )
    except AuthValidationError as error:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context=_template_context(
                request,
                csrf_token=get_csrf_token(request),
                username=normalized_username,
                error=error.message,
            ),
            status_code=400,
        )
    except DuplicateUsernameError as error:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context=_template_context(
                request,
                csrf_token=get_csrf_token(request),
                username=normalized_username,
                error=str(error),
            ),
            status_code=409,
        )

    return RedirectResponse(url="/login?registered=1", status_code=303)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request, registered: str | None = None) -> Response:
    if get_current_user(request) is not None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_template_context(
            request,
            csrf_token=get_csrf_token(request),
            username="",
            registered=registered == "1",
            error=None,
        ),
    )


@router.post("/login", response_class=HTMLResponse, include_in_schema=False)
async def login(
    request: Request,
    username: str = Form(default=""),
    password: str = Form(default=""),
    csrf_token: str = Form(default=""),
) -> Response:
    if not is_valid_csrf_token(request, csrf_token):
        return _csrf_error(request)
    if get_current_user(request) is not None:
        return RedirectResponse(url="/", status_code=303)

    user = authenticate_user(
        username,
        password,
        request.app.state.database_path,
    )
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=_template_context(
                request,
                csrf_token=get_csrf_token(request),
                username=normalize_username(username),
                registered=False,
                error="아이디 또는 비밀번호가 올바르지 않습니다.",
            ),
            status_code=401,
        )

    establish_user_session(request, user.id)
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout", response_class=HTMLResponse, include_in_schema=False)
async def logout(
    request: Request,
    csrf_token: str = Form(default=""),
) -> Response:
    if not is_valid_csrf_token(request, csrf_token):
        return _csrf_error(request)

    clear_user_session(request)
    return RedirectResponse(url="/", status_code=303)
