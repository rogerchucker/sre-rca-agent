from __future__ import annotations

from core import db
from core.config import settings
import pytest


def _reset_db_state():
    db.ENGINE = None
    db.SessionLocal = None


def test_normalize_db_url_postgres():
    assert db._normalize_db_url("postgresql://user@host/db") == "postgresql+psycopg://user@host/db"


def test_normalize_db_url_other():
    assert db._normalize_db_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_make_engine_none(monkeypatch):
    _reset_db_state()
    monkeypatch.setattr(settings, "database_url", None)
    assert db._make_engine() is None


def test_init_db_no_engine(monkeypatch):
    _reset_db_state()
    monkeypatch.setattr(settings, "database_url", None)
    db.init_db()


def test_get_db_raises_without_url(monkeypatch):
    _reset_db_state()
    monkeypatch.setattr(settings, "database_url", None)
    with pytest.raises(RuntimeError):
        with db.get_db():
            pass


def test_init_db_and_get_db(monkeypatch):
    _reset_db_state()
    monkeypatch.setattr(settings, "database_url", "sqlite:///:memory:")
    monkeypatch.setattr(db, "create_engine", lambda *args, **kwargs: object())
    monkeypatch.setattr(db.Base.metadata, "create_all", lambda bind=None: None)
    monkeypatch.setattr(db, "sessionmaker", lambda *args, **kwargs: lambda: DummySession())
    db.init_db()
    with db.get_db() as session:
        session.execute("select 1")


class DummySession:
    def execute(self, _stmt):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def test_get_db_rollback_on_error(monkeypatch):
    _reset_db_state()
    monkeypatch.setattr(settings, "database_url", "sqlite:///:memory:")
    monkeypatch.setattr(db, "create_engine", lambda *args, **kwargs: object())
    monkeypatch.setattr(db, "sessionmaker", lambda *args, **kwargs: lambda: ErrorSession())
    monkeypatch.setattr(db.Base.metadata, "create_all", lambda bind=None: None)
    db.init_db()
    with pytest.raises(RuntimeError):
        with db.get_db():
            raise RuntimeError("boom")


class ErrorSession(DummySession):
    def commit(self):
        raise RuntimeError("commit failed")
