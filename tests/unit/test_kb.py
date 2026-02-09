from __future__ import annotations

from pathlib import Path
import pytest
from core.kb import KB


def test_kb_load_invalid(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("- not a map")
    with pytest.raises(ValueError):
        KB.load(str(path))


def test_kb_subject_config_missing_bindings(tmp_path: Path):
    path = tmp_path / "kb.yaml"
    path.write_text("subjects:\n  - name: svc\n    environment: prod\n")
    kb = KB.load(str(path))
    with pytest.raises(ValueError):
        kb.get_subject_config("svc", "prod")


def test_kb_subject_env_mismatch(tmp_path: Path):
    path = tmp_path / "kb.yaml"
    path.write_text("subjects:\n  - name: svc\n    environment: prod\n    bindings: {log_store: l1}\n")
    kb = KB.load(str(path))
    with pytest.raises(ValueError):
        kb.get_subject_config("svc", "staging")


def test_kb_subject_ok(tmp_path: Path):
    path = tmp_path / "kb.yaml"
    path.write_text("subjects:\n  - name: svc\n    environment: production\n    bindings: {log_store: l1}\n")
    kb = KB.load(str(path))
    out = kb.get_subject_config("svc", "prod")
    assert out["name"] == "svc"


def test_kb_get_provider_instances_empty(tmp_path: Path):
    path = tmp_path / "kb.yaml"
    path.write_text("subjects: []\nproviders: []\n")
    kb = KB.load(str(path))
    assert kb.get_provider_instances() == {}


def test_kb_get_provider_instances_requires_id(tmp_path: Path):
    path = tmp_path / "kb.yaml"
    path.write_text("providers:\n  - {category: log_store}\n")
    kb = KB.load(str(path))
    with pytest.raises(ValueError):
        kb.get_provider_instances()


def test_load_providers_invalid(tmp_path: Path):
    path = tmp_path / "providers.yaml"
    path.write_text("- not a map")
    with pytest.raises(ValueError):
        KB.load_providers(str(path))


def test_load_providers_missing_ids(tmp_path: Path):
    path = tmp_path / "providers.yaml"
    path.write_text("providers:\n  - {category: log_store}\n")
    with pytest.raises(ValueError):
        KB.load_providers(str(path))


def test_load_providers_ok(tmp_path: Path):
    path = tmp_path / "providers.yaml"
    path.write_text("providers:\n  - {id: p1, category: log_store}\n")
    out = KB.load_providers(str(path))
    assert out["p1"]["category"] == "log_store"


def test_load_providers_empty(tmp_path: Path):
    path = tmp_path / "providers.yaml"
    path.write_text("providers: []\n")
    with pytest.raises(ValueError):
        KB.load_providers(str(path))
