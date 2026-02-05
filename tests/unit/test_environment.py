from __future__ import annotations

import pytest
from core.environment import canonicalize_environment, environment_aliases


def test_environment_aliases_contains_prod():
    aliases = environment_aliases()
    assert aliases["prod"] == "prod"
    assert aliases["production"] == "prod"


def test_canonicalize_environment():
    assert canonicalize_environment("prod") == "prod"
    assert canonicalize_environment("Production") == "prod"
    assert canonicalize_environment("stg") == "staging"
    assert canonicalize_environment("dev") == "dev"


def test_canonicalize_environment_invalid():
    with pytest.raises(ValueError):
        canonicalize_environment("")
    with pytest.raises(ValueError):
        canonicalize_environment("unknown")
