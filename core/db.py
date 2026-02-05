from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _make_engine():
    if not settings.database_url:
        return None
    return create_engine(_normalize_db_url(settings.database_url), pool_pre_ping=True)


ENGINE = None
SessionLocal = None


def init_db() -> None:
    global ENGINE, SessionLocal
    if ENGINE is None:
        ENGINE = _make_engine()
    if ENGINE is None:
        return
    if SessionLocal is None:
        SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)
    from core import persistence_models  # noqa: F401

    Base.metadata.create_all(bind=ENGINE)


@contextmanager
def get_db() -> Generator:
    global ENGINE, SessionLocal
    if ENGINE is None:
        ENGINE = _make_engine()
    if ENGINE is None:
        raise RuntimeError("database_url is not configured")
    if SessionLocal is None:
        SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
