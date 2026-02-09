from __future__ import annotations

import os
import runpy
from pathlib import Path

import pytest

from core.config import settings
from core import db


def _reset_db_state():
    db.ENGINE = None
    db.SessionLocal = None


def test_render_ui_prompt(tmp_path: Path, monkeypatch):
    spec = {
        "inputs": {"name": "world"},
        "variables": {},
        "modules": {
            "hello": {"enabled": True, "content": "Hello {{ name }}"},
        },
        "render": {"order": ["hello"], "wrapper": {"header": "Start", "footer": "End"}},
    }
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        "inputs:\n  name: world\nmodules:\n  hello:\n    enabled: true\n    content: 'Hello {{ name }}'\nrender:\n  order: [hello]\n  wrapper:\n    header: Start\n    footer: End\n"
    )
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parents[2]))
    monkeypatch.setattr("sys.argv", ["render_ui_prompt", "--spec", str(spec_path)])
    with pytest.raises(SystemExit):
        runpy.run_module("scripts.render_ui_prompt", run_name="__main__")


def test_demo_trigger(monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    def _post(url, json=None, timeout=None):
        return DummyResponse()

    monkeypatch.setattr("httpx.post", _post)
    monkeypatch.setenv("RCA_API_URL", "http://example.invalid")
    runpy.run_module("scripts.demo_trigger", run_name="__main__")


def test_demo_reset(monkeypatch):
    _reset_db_state()
    monkeypatch.setattr(settings, "enable_persistence", True)
    monkeypatch.setattr(settings, "database_url", "postgresql://example.invalid/db")
    monkeypatch.setattr("core.db.init_db", lambda: None)
    monkeypatch.setattr("core.db.get_db", lambda: DummyDB())
    runpy.run_module("scripts.demo_reset", run_name="__main__")


class DummyDB:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def query(self, _model):
        return self

    def delete(self):
        return None
