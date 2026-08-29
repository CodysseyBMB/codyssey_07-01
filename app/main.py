from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import health, pages


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Codyssey 07-01",
    description="FastAPI와 Jinja2로 구성한 웹 기반 AI 챗봇 서비스",
    version="0.1.0",
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

app.include_router(pages.router)
app.include_router(health.router)
