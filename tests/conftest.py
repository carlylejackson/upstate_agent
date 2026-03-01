import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test_upstate_agent.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ADMIN_API_KEY"] = "test-admin-key"
    os.environ["ESCALATION_API_KEY"] = "test-escalation-key"
    os.environ["APP_ENV"] = "development"
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["TWILIO_VALIDATE_SIGNATURES"] = "false"
    os.environ["TWILIO_AUTH_TOKEN"] = "test-token"

    from app.core.config import get_settings
    from app.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
