from __future__ import annotations

import importlib
import os
from pathlib import Path

import core.config as config


def test_env_local_overrides_env(tmp_path: Path, monkeypatch):
    env_path = tmp_path / ".env"
    env_local_path = tmp_path / ".env.local"

    env_path.write_text(
        "OPENAI_API_KEY=env-key\n"
        "OPENAI_MODEL=env-model\n"
        "ENABLE_PERSISTENCE=false\n"
        "DATABASE_URL=postgresql://env\n"
    )
    env_local_path.write_text(
        "OPENAI_API_KEY=local-key\n"
        "OPENAI_MODEL=local-model\n"
        "ENABLE_PERSISTENCE=true\n"
        "DATABASE_URL=postgresql://local\n"
    )

    monkeypatch.setenv("OPENAI_API_KEY", "os-key")
    monkeypatch.delenv("ENABLE_PERSISTENCE", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)

    importlib.reload(config)

    settings = config.settings
    assert settings.openai_api_key == "os-key"
    assert settings.openai_model == "local-model"
    assert settings.enable_persistence is True
    assert settings.database_url == "postgresql://local"
