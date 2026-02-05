from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import httpx

API_URL = os.getenv("RCA_API_URL", "http://localhost:8080")

payload = {
    "title": "Demo: Elevated error rate",
    "severity": "P1",
    "environment": "prod",
    "subject": "hn-backend-demo",
    "starts_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "ends_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "labels": {"demo": "true"},
    "annotations": {"runbook": "rbk-hn-backend-demo-deploy_regression"},
}

resp = httpx.post(f"{API_URL}/webhook/incident", json=payload, timeout=30)
resp.raise_for_status()
print(json.dumps(resp.json(), indent=2))
