from __future__ import annotations

import sys
from pathlib import Path
import yaml
import pytest

from scripts.validate_kb import main


def _write_yaml(path: Path, data: dict):
    path.write_text(yaml.safe_dump(data))


def test_validate_kb_ok(tmp_path: Path, monkeypatch):
    subjects = {
        "subjects": [
            {
                "name": "payments",
                "bindings": {"log_store": "loki_main"},
                "log_evidence": {"parse": {"format": "json", "fields": {"env": "e", "err_msg": "m"}}},
            }
        ]
    }
    catalog = {"providers": [{"id": "loki_main"}]}

    s_path = tmp_path / "subjects.yaml"
    c_path = tmp_path / "catalog.yaml"
    _write_yaml(s_path, subjects)
    _write_yaml(c_path, catalog)

    monkeypatch.setattr(sys, "argv", ["validate_kb.py", str(s_path), str(c_path)])
    assert main() == 0


def test_validate_kb_missing_provider(tmp_path: Path, monkeypatch):
    subjects = {"subjects": [{"name": "payments", "bindings": {"log_store": "missing"}}]}
    catalog = {"providers": [{"id": "loki_main"}]}

    s_path = tmp_path / "subjects.yaml"
    c_path = tmp_path / "catalog.yaml"
    _write_yaml(s_path, subjects)
    _write_yaml(c_path, catalog)

    monkeypatch.setattr(sys, "argv", ["validate_kb.py", str(s_path), str(c_path)])
    with pytest.raises(SystemExit):
        main()
