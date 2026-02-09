from __future__ import annotations
import hashlib
from typing import Any, Dict, List
import httpx

from core.models import EvidenceItem, AlertQueryRequest, TimeRange

class GrafanaAlerting:
    """
    Adapter for Grafana Alerting / Alertmanager API.
    Config keys:
      - base_url_env: "GRAFANA_URL"
      - auth: { kind: "bearer_env" | "basic_env", token_env: "GRAFANA_TOKEN", username_env: "GRAFANA_USER" }
      - alerts_path: optional override (default /api/alertmanager/grafana/api/v2/alerts)
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.base_url = _env_required(config.get("base_url_env"))
        self.auth = config.get("auth", {"kind": "bearer_env"})
        self.alerts_path = config.get("alerts_path") or "/api/alertmanager/grafana/api/v2/alerts"

    def list_alerts(self, req: AlertQueryRequest) -> EvidenceItem:
        tr = req.time_range
        payload = self._list_alerts(req)

        alerts = _extract_alerts(payload)
        count = len(alerts)
        by_severity: Dict[str, int] = {}
        by_state: Dict[str, int] = {}
        samples: List[str] = []

        for a in alerts[: min(10, count)]:
            lbl = a.get("labels") or {}
            sev = lbl.get("severity") or "unknown"
            by_severity[sev] = by_severity.get(sev, 0) + 1

            st = (a.get("status") or {}).get("state") or "unknown"
            by_state[st] = by_state.get(st, 0) + 1

            name = lbl.get("alertname") or lbl.get("alert") or "alert"
            samples.append(f"{name} ({sev}, {st})")

        return EvidenceItem(
            id=_evidence_id("alerts", tr.start + tr.end + str(req.label_filters)),
            kind="alert",
            source=self.provider_id,
            time_range=tr,
            query=f"GET {self.alerts_path}",
            summary=f"Found {count} alerts from Grafana Alerting.",
            samples=samples,
            top_signals={"by_severity": by_severity, "by_state": by_state, "count": count},
            pointers=[{"title": "Grafana", "url": self.base_url}],
            tags=["alerts", "grafana"],
        )

    def _list_alerts(self, req: AlertQueryRequest) -> Any:
        url = self.base_url.rstrip("/") + self.alerts_path
        params = {}
        for expr in req.label_filters or []:
            if "=" in expr:
                k, v = expr.split("=", 1)
                params.setdefault("filter", []).append(f"{k.strip()}={v.strip()}")
        headers = _auth_headers(self.auth)
        with httpx.Client(timeout=20.0, headers=headers) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            return r.json()


def _extract_alerts(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], list):
            return payload["data"]
        if "alerts" in payload and isinstance(payload["alerts"], list):
            return payload["alerts"]
    return []


def _auth_headers(auth: Dict[str, Any]) -> Dict[str, str]:
    if auth.get("kind") == "bearer_env":
        token_env = auth.get("token_env")
        import os
        if token_env and token_env in os.environ:
            return {"Authorization": f"Bearer {os.environ[token_env]}"}
    if auth.get("kind") == "basic_env":
        import os
        import base64
        user_env = auth.get("username_env")
        token_env = auth.get("token_env")
        if user_env and token_env and user_env in os.environ and token_env in os.environ:
            user = os.environ[user_env]
            token = os.environ[token_env]
            raw = f"{user}:{token}".encode("utf-8")
            return {"Authorization": f"Basic {base64.b64encode(raw).decode('ascii')}"}
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
