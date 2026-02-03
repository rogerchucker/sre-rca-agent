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
    monkeypatch.setenv("VCS_TOKEN", "test-vcs")
    monkeypatch.setenv("DEPLOY_TOKEN", "test-deploy")
    monkeypatch.setenv("BUILD_TOKEN", "test-build")


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
