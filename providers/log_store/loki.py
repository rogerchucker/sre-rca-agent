from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import httpx

from core.models import EvidenceItem, LogQueryRequest, TimeRange

class LokiLogStore:
    """
    Adapter for a specific log backend.
    Config keys (examples):
      - base_url_env: "LOG_STORE_URL"
      - auth: { kind: "none" | "bearer_env", token_env: "LOG_STORE_TOKEN" }
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.base_url = _env_required(config.get("base_url_env"))
        self.auth = config.get("auth", {"kind": "none"})

    def query(self, req: LogQueryRequest) -> EvidenceItem:
        # Build backend-specific query from intent
        if req.intent == "signature_counts":
            logql = self._build_signature_counts(req)
            mode = "top_signatures"
            limit = min(req.limit, 200)
        else:
            logql = self._build_samples(req)
            mode = "samples"
            limit = min(req.limit, 200)

        payload = self._query_range(logql, req.time_range, limit=limit)
        tr = req.time_range

        if mode == "samples":
            lines = _extract_log_lines(payload, limit=limit)
            return EvidenceItem(
                id=_evidence_id("logs_samples", logql + tr.start + tr.end),
                kind="log",
                source=self.provider_id,
                time_range=tr,
                query=logql,
                summary=f"Collected {len(lines)} log samples for the time window.",
                samples=lines,
                top_signals={},
                pointers=[],
                tags=["logs", "samples"],
            )

        sigs = _extract_signature_series(payload)
        return EvidenceItem(
            id=_evidence_id("logs_sigs", logql + tr.start + tr.end),
                kind="log",
            source=self.provider_id,
            time_range=tr,
            query=logql,
            summary="Top error signatures computed over the time window.",
            samples=[],
            top_signals={"signatures": sigs},
            pointers=[],
            tags=["logs", "signatures"],
        )

    # ---- backend-specific query builders ----

    def _build_label_selector(self, selectors: Dict[str, str]) -> str:
        if not selectors:
            return "{}"
        parts = [f'{k}="{v}"' for k, v in selectors.items()]
        return "{" + ",".join(parts) + "}"

    def _build_signature_counts(self, req: LogQueryRequest) -> str:
        selectors = self._build_label_selector(req.stream_selectors)
        parse = req.parse or {}
        fmt = parse.get("format", "json")
        fields = parse.get("fields", {})

        # We expect keys "err_type" and "err_msg" as logical names if configured.
        err_type_path = fields.get("err_type")
        err_msg_path = fields.get("err_msg")
        env_path = fields.get("env")

        # Fallback to generic: signature is just raw line
        if fmt != "json" or not err_msg_path:
            return f'topk(10, sum(count_over_time({selectors}[5m])))'

        # Loki JSON stage: map logical labels for aggregation
        # Example: | json err_type="attributes.error.type", err_msg="attributes.error.message"
        json_stage_parts = []
        if env_path:
            json_stage_parts.append(f'env="{env_path}"')
        if err_type_path:
            json_stage_parts.append(f'err_type="{err_type_path}"')
        json_stage_parts.append(f'err_msg="{err_msg_path}"')

        json_stage = " | json " + ", ".join(json_stage_parts)

        # Filter by environment if provided
        env_filter = ""
        if req.environment and env_path:
            env_filter = f' | env="{req.environment}"'

        # 5m buckets for signatures
        return (
            "topk(10, "
            "sum by (err_type, err_msg) ("
            f"count_over_time({selectors}{json_stage}{env_filter}[5m])"
            ")"
            ")"
        )

    def _build_samples(self, req: LogQueryRequest) -> str:
        selectors = self._build_label_selector(req.stream_selectors)
        parse = req.parse or {}
        fmt = parse.get("format", "json")
        fields = parse.get("fields", {})

        if fmt != "json":
            return selectors

        # Extract a few useful fields if present
        json_stage_parts = []
        for logical, path in fields.items():
            # only include a subset for readability
            if logical in ("env", "version", "err_type", "err_msg", "route", "status", "trace_id"):
                json_stage_parts.append(f'{logical}="{path}"')

        json_stage = ""
        if json_stage_parts:
            json_stage = " | json " + ", ".join(json_stage_parts)

        env_filter = ""
        if req.environment and fields.get("env"):
            env_filter = f' | env="{req.environment}"'

        # If caller provided a filter like status=500 or err_type=...
        extra_filters = ""
        for k, v in (req.filters or {}).items():
            # Loki label filters after json stage
            extra_filters += f' | {k}="{v}"'

        # Format the line in a compact way if we have extracted fields
        line_fmt = ""
        if any(k in fields for k in ("err_msg", "err_type", "route", "status", "version")):
            line_fmt = ' | line_format "env={{.env}} v={{.version}} route={{.route}} status={{.status}} type={{.err_type}} err={{.err_msg}} trace={{.trace_id}}"'

        return f"{selectors}{json_stage}{env_filter}{extra_filters}{line_fmt}"

    # ---- HTTP ----

    def _headers(self) -> Dict[str, str]:
        kind = (self.auth or {}).get("kind", "none")
        if kind == "bearer_env":
            token = _env_required((self.auth or {}).get("token_env"))
            return {"Authorization": f"Bearer {token}"}
        if kind == "basic_env":
            import base64
            user_env = (self.auth or {}).get("username_env")
            token_env = (self.auth or {}).get("token_env")
            if user_env and token_env:
                user = _env_required(user_env)
                token = _env_required(token_env)
                raw = f"{user}:{token}".encode("utf-8")
                return {"Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}"}
        return {}

    def _query_range(self, logql: str, tr: TimeRange, limit: int) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + "/loki/api/v1/query_range"
        params = {
            "query": logql,
            "start": str(_to_ns(tr.start)),
            "end": str(_to_ns(tr.end)),
            "limit": str(limit),
            "direction": "BACKWARD",
        }
        with httpx.Client(timeout=20.0, headers=self._headers()) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            return r.json()

# ---- helpers ----

def _env_required(env_name: str | None) -> str:
    import os
    if not env_name:
        raise ValueError("Missing required env var name in provider config.")
    val = os.getenv(env_name)
    if not val:
        raise ValueError(f"Environment variable '{env_name}' is not set.")
    return val

def _to_ns(rfc3339: str) -> int:
    dt = datetime.fromisoformat(rfc3339.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000_000)

def _evidence_id(prefix: str, content: str) -> str:
    h = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{h}"

def _extract_log_lines(payload: Dict[str, Any], limit: int) -> List[str]:
    result = payload.get("data", {}).get("result", [])
    lines: List[str] = []
    for stream in result:
        for _, line in stream.get("values", []):
            lines.append(line)
            if len(lines) >= limit:
                return lines
    return lines

def _extract_signature_series(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = payload.get("data", {}).get("result", [])
    sigs = []
    for series in result:
        metric = series.get("metric", {})
        values = series.get("values") or []
        total = 0.0
        for _, v in values:
            try:
                total += float(v)
            except Exception:
                pass
        sigs.append({
            "err_type": metric.get("err_type", ""),
            "err_msg": metric.get("err_msg", ""),
            "count": total,
        })
    sigs.sort(key=lambda x: x["count"], reverse=True)
    return sigs[:10]
