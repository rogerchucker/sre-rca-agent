from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

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
        for s in subjects:
            if s.get("name") == subject:
                env = s.get("environment")
                if env and environment and env != environment:
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