from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from core.kb import KB


def test_kb_load_requires_mapping(tmp_path: Path):
    p = tmp_path / "kb.yaml"
    p.write_text("- item1\n- item2\n")
    with pytest.raises(ValueError):
        KB.load(str(p))


def test_kb_subject_resolution_and_bindings(tmp_path: Path):
    data = {
        "subjects": [
            {"name": "payments", "environment": "prod", "bindings": {"log_store": "loki_main"}},
        ],
        "providers": [
            {"id": "loki_main", "category": "log_store", "type": "loki"},
        ],
    }
    p = tmp_path / "kb.yaml"
    p.write_text(yaml.safe_dump(data))

    kb = KB.load(str(p))
    subject = kb.get_subject_config("payments", "prod")
    assert subject["bindings"]["log_store"] == "loki_main"


def test_kb_subject_missing_bindings(tmp_path: Path):
    data = {"subjects": [{"name": "payments"}]}
    p = tmp_path / "kb.yaml"
    p.write_text(yaml.safe_dump(data))

    kb = KB.load(str(p))
    with pytest.raises(ValueError):
        kb.get_subject_config("payments", "prod")
