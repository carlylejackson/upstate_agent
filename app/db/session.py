from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    database_url = settings.database_url
    connect_args = {}
    engine_kwargs = {"pool_pre_ping": True}

    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, class_=Session)


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
