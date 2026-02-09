#!/usr/bin/env python3
"""
Trigger a simple incident webhook against a running API.

This is intentionally generic. For real demos, users should wire their own
alert triggers and call the webhook with realistic payloads.
"""

from __future__ import annotations

import os

import httpx


def main() -> int:
    api_url = os.environ.get("RCA_API_URL", "http://127.0.0.1:8080").rstrip("/")
    payload = {
        "title": "Synthetic alert: elevated error rate",
        "severity": "P2",
        "environment": "prod",
        "subject": "service_primary",
        "time_range": {"start": None, "end": None},
        "details": {"source": "demo_trigger"},
    }
    res = httpx.post(f"{api_url}/webhook/incident", json=payload, timeout=10)
    res.raise_for_status()
    print(res.json())
    return 0


if __name__ == "__main__":
    # Intentionally do not raise SystemExit; unit tests execute this module via runpy.
    main()
