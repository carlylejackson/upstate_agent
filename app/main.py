from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, chat, escalation, health, sms, voice
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.init_db import init_db
from app.db.session import get_session_factory


@asynccontextmanager
async def lifespan(_: FastAPI):
    session = get_session_factory()()
    try:
        init_db(session)
        yield
    finally:
        session.close()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Upstate Agent API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(escalation.router)
    app.include_router(admin.router)
    app.include_router(sms.router)
    app.include_router(voice.router)

    app.mount("/widget", StaticFiles(directory="app/web"), name="widget")
    widget_test_path = Path("app/web/test.html")

    @app.get("/", tags=["root"])
    def root() -> dict:
        return {
            "name": "Upstate Agent API",
            "status": "ok",
            "health": "/v1/health",
            "docs": "/docs",
        }

    @app.get("/chat-test", response_class=HTMLResponse, tags=["root"])
    def chat_test() -> str:
        if widget_test_path.exists():
            return widget_test_path.read_text(encoding="utf-8")
        return "<h1>Chat test page not found</h1>"

    return app


app = create_app()
