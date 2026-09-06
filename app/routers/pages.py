from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_csrf_token, get_current_user


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    current_user = get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": "Codyssey 07-01",
            "current_user": current_user,
            "csrf_token": get_csrf_token(request) if current_user else None,
        },
    )
