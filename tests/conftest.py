from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path for imports like core/, providers/, api/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LOG_STORE_URL", "https://loki.example.invalid")
    monkeypatch.setenv("METRICS_URL", "https://prom.example.invalid")
    monkeypatch.setenv("TRACE_URL", "https://jaeger.example.invalid")
    monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.invalid")
    monkeypatch.setenv("GRAFANA_TOKEN", "test-grafana")
    monkeypatch.setenv("GRAFANA_USER", "grafana-user")
    monkeypatch.setenv("VCS_TOKEN", "test-vcs")
    monkeypatch.setenv("DEPLOY_TOKEN", "test-deploy")
    monkeypatch.setenv("BUILD_TOKEN", "test-build")
    monkeypatch.setenv("ENABLE_PERSISTENCE", "false")
    monkeypatch.setenv("DATABASE_URL", "")

    # Sync settings object with test env without reloading ORM models.
    import importlib
    import core.config
    import core.orchestrator

    core.config.settings.openai_api_key = "test-key"
    core.config.settings.enable_persistence = False
    core.config.settings.database_url = None

    importlib.reload(core.orchestrator)


@pytest.fixture
def fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def kb_path(tmp_path: Path, fixture_dir: Path) -> str:
    src = fixture_dir / "kb.yaml"
    dst = tmp_path / "kb.yaml"
    dst.write_text(src.read_text())
    return str(dst)


@pytest.fixture
def webhook_payload(fixture_dir: Path) -> dict:
    return json.loads((fixture_dir / "webhook.json").read_text())
