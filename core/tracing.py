from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class NoopTracer:
    def emit(self, event: Dict[str, Any]) -> None:
        return None


class JSONLTracer:
    def __init__(self, path: str):
        self.path = path

    def emit(self, event: Dict[str, Any]) -> None:
        payload = dict(event)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")


def get_tracer(path: Optional[str]) -> NoopTracer | JSONLTracer:
    if not path:
        return NoopTracer()
    return JSONLTracer(path)
