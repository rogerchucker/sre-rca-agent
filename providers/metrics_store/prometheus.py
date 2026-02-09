from __future__ import annotations
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
import httpx

from core.models import EvidenceItem, MetricsQueryRequest, TimeRange

class PrometheusMetricsStore:
    """
    Adapter for a Prometheus-compatible metrics API.
    Config keys:
      - base_url_env: "METRICS_URL"
      - auth: { kind: "none" | "bearer_env", token_env: "METRICS_TOKEN" }
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.base_url = _env_required(config.get("base_url_env"))
        self.auth = config.get("auth", {"kind": "none"})

    def query_range(self, req: MetricsQueryRequest) -> EvidenceItem:
        tr = req.time_range
        query = req.query
        step = max(10, int(req.step_seconds))

        payload = self._query_range(query, tr, step)
        result = payload.get("data", {}).get("result", [])

        series_count = len(result)
        sample_count = sum(len(r.get("values", [])) for r in result)
        samples: List[str] = []
        for r in result[: min(5, series_count)]:
            metric = r.get("metric", {})
            values = r.get("values", [])[:3]
            samples.append(f"{metric} -> {values}")

        return EvidenceItem(
            id=_evidence_id("metrics", query + tr.start + tr.end),
            kind="metric",
            source=self.provider_id,
            time_range=tr,
            query=query,
            summary=f"Metrics query returned {series_count} series and {sample_count} samples.",
            samples=samples,
            top_signals={"series_count": series_count, "sample_count": sample_count},
            pointers=[],
            tags=["metrics"],
        )

    def _query_range(self, query: str, tr: TimeRange, step: int) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + "/api/v1/query_range"
        params = {
            "query": query,
            "start": _to_unix(tr.start),
            "end": _to_unix(tr.end),
            "step": step,
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
    if auth.get("kind") == "basic_env":
        import base64
        user_env = auth.get("username_env")
        token_env = auth.get("token_env")
        if user_env and token_env and user_env in os.environ and token_env in os.environ:
            raw = f"{os.environ[user_env]}:{os.environ[token_env]}".encode("utf-8")
            return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}
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
