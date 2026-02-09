from __future__ import annotations

from typing import Dict

_CANONICAL = {
    "prod": "prod",
    "production": "prod",
    "prd": "prod",
    "staging": "staging",
    "stage": "staging",
    "stg": "staging",
    "dev": "dev",
    "development": "dev",
}


def canonicalize_environment(value: str) -> str:
    if value is None:
        raise ValueError("environment is required")
    raw = value.strip().lower()
    if not raw:
        raise ValueError("environment is required")
    env = _CANONICAL.get(raw)
    if not env:
        raise ValueError(f"unknown environment '{value}'")
    return env


def environment_aliases() -> Dict[str, str]:
    return dict(_CANONICAL)
