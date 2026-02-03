from __future__ import annotations
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
import httpx

from core.models import EvidenceItem, TraceQueryRequest, TimeRange

class JaegerTraceStore:
    """
    Adapter for a Jaeger-compatible query API.
    Config keys:
      - base_url_env: "TRACE_URL"
      - auth: { kind: "none" | "bearer_env", token_env: "TRACE_TOKEN" }
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.base_url = _env_required(config.get("base_url_env"))
        self.auth = config.get("auth", {"kind": "none"})

    def search_traces(self, req: TraceQueryRequest) -> EvidenceItem:
        tr = req.time_range
        service = req.service_name or req.subject
        payload = self._search(service, tr, limit=req.limit)

        traces = payload.get("data", []) or []
        trace_ids = [t.get("traceID") for t in traces if t.get("traceID")]
        return EvidenceItem(
            id=_evidence_id("traces", service + tr.start + tr.end),
            kind="trace",
            source=self.provider_id,
            time_range=tr,
            query=f"traces(service={service})",
            summary=f"Found {len(trace_ids)} traces in the time window.",
            samples=trace_ids[:10],
            top_signals={"trace_ids": trace_ids[: req.limit]},
            pointers=[],
            tags=["trace"],
        )

    def _search(self, service: str, tr: TimeRange, limit: int) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + "/api/traces"
        params = {
            "service": service,
            "start": int(_to_unix(tr.start) * 1_000_000),
            "end": int(_to_unix(tr.end) * 1_000_000),
            "limit": min(100, max(1, limit)),
        }
        headers = _auth_headers(self.auth)
        with httpx.Client(timeout=20.0, headers=headers) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            return r.json()

def _to_unix(ts: str) -> float:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()

def _auth_headers(auth: Dict[str, Any]) -> Dict[str, str]:
    if auth.get("kind") == "bearer_env":
        token_env = auth.get("token_env")
        if token_env and token_env in os.environ:
            return {"Authorization": f"Bearer {os.environ[token_env]}"}
    return {}

def _env_required(env_name: str | None) -> str:
    import os
    if not env_name:
        raise ValueError("Missing required env var name in provider config.")
    val = os.getenv(env_name)
    if not val:
        raise ValueError(f"Environment variable '{env_name}' is not set.")
    return val

def _evidence_id(prefix: str, content: str) -> str:
    h = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{h}"
