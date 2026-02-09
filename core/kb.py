from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from core.environment import canonicalize_environment

@dataclass(frozen=True)
class KB:
    raw: Dict[str, Any]

    @staticmethod
    def load(path: str) -> "KB":
        data = yaml.safe_load(Path(path).read_text())
        if not isinstance(data, dict):
            raise ValueError("KB YAML must be a mapping/object at top level.")
        return KB(raw=data)

    def get_subject_config(self, subject: str, environment: str) -> Dict[str, Any]:
        """
        Returns the subject block, plus resolved bindings and provider instance ids.
        """
        subjects = self.raw.get("subjects", [])
        match = None
        env_norm = canonicalize_environment(environment)
        for s in subjects:
            if s.get("name") == subject:
                env_raw = s.get("environment")
                if env_raw:
                    env = canonicalize_environment(env_raw)
                else:
                    env = None
                if env and env_norm and env != env_norm:
                    continue
                match = s
                break
        if not match:
            raise ValueError(f"Subject not found in KB: {subject} (env={environment})")

        # Basic shape validation
        if "bindings" not in match:
            raise ValueError(f"KB subject '{subject}' missing 'bindings'")

        return match

    def get_provider_instances(self) -> Dict[str, Any]:
        providers = self.raw.get("providers", [])
        out: Dict[str, Any] = {}
        for p in providers:
            pid = p.get("id")
            if not pid:
                raise ValueError("Each provider must have an 'id'")
            out[pid] = p
        return out

    @staticmethod
    def load_providers(path: str) -> Dict[str, Any]:
        data = yaml.safe_load(Path(path).read_text())
        if not isinstance(data, dict):
            raise ValueError("Provider catalog YAML must be a mapping/object at top level.")
        providers = data.get("providers", [])
        out: Dict[str, Any] = {}
        for p in providers:
            pid = p.get("id")
            if not pid:
                raise ValueError("Each provider must have an 'id'")
            out[pid] = p
        if not out:
            raise ValueError(f"No providers found in catalog: {path}")
        return out
