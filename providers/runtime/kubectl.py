from __future__ import annotations
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.models import EvidenceItem, EventQueryRequest, K8sLogQueryRequest, TimeRange

class KubectlRuntime:
    """
    Adapter that uses kubectl to collect logs and events.
    Config keys:
      - kubeconfig_env: "KUBECONFIG" (optional)
      - context: "cluster-context" (optional)
      - namespace_map: { "<subject>": "namespace" }
      - selector_map: { "<subject>": "app=foo,component=bar" }
      - container_map: { "<subject>": "container-name" }
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.kubeconfig_env = config.get("kubeconfig_env")
        self.context = config.get("context")
        self.namespace_map = config.get("namespace_map", {})
        self.selector_map = config.get("selector_map", {})
        self.container_map = config.get("container_map", {})

    def get_logs(self, req: K8sLogQueryRequest) -> EvidenceItem:
        ns = req.namespace or self.namespace_map.get(req.subject)
        selector = req.selector or self.selector_map.get(req.subject)
        container = req.container or self.container_map.get(req.subject)
        tr = req.time_range

        if not ns or not selector:
            return EvidenceItem(
                id=_evidence_id("k8s_logs_missing", req.subject + tr.start + tr.end),
                kind="logs",
                source=self.provider_id,
                time_range=tr,
                query="kubectl logs (missing namespace/selector)",
                summary="Skipped kubectl logs: missing namespace or selector for subject.",
                samples=[],
                top_signals={"namespace": ns, "selector": selector},
                pointers=[],
                tags=["k8s", "logs", "skipped"],
            )

        cmd = ["kubectl"]
        if self.context:
            cmd += ["--context", self.context]
        cmd += ["-n", ns, "logs", "-l", selector, "--since-time", tr.start, "--tail", str(req.limit)]
        if container:
            cmd += ["-c", container]

        out = _run(cmd, self.kubeconfig_env)
        lines = [line for line in out.splitlines() if line.strip()]

        return EvidenceItem(
            id=_evidence_id("k8s_logs", selector + tr.start + tr.end),
            kind="logs",
            source=self.provider_id,
            time_range=tr,
            query=" ".join(cmd),
            summary=f"Collected {len(lines)} kubectl log lines for the time window.",
            samples=lines[: req.limit],
            top_signals={"namespace": ns, "selector": selector, "container": container},
            pointers=[],
            tags=["k8s", "logs"],
        )

    def get_events(self, req: EventQueryRequest) -> EvidenceItem:
        ns = req.namespace or self.namespace_map.get(req.subject)
        selector = req.selector or self.selector_map.get(req.subject)
        tr = req.time_range

        if not ns:
            return EvidenceItem(
                id=_evidence_id("k8s_events_missing", req.subject + tr.start + tr.end),
                kind="event",
                source=self.provider_id,
                time_range=tr,
                query="kubectl get events (missing namespace)",
                summary="Skipped kubectl events: missing namespace for subject.",
                samples=[],
                top_signals={"namespace": ns, "selector": selector},
                pointers=[],
                tags=["k8s", "events", "skipped"],
            )

        cmd = ["kubectl"]
        if self.context:
            cmd += ["--context", self.context]
        cmd += ["-n", ns, "get", "events", "-o", "json"]
        if selector:
            if "=" in selector:
                cmd += ["-l", selector]
            else:
                cmd += ["--field-selector", f"involvedObject.name={selector}"]

        raw = _run(cmd, self.kubeconfig_env)
        data = json.loads(raw)
        items = data.get("items", [])

        start = _parse_time(tr.start)
        end = _parse_time(tr.end)
        filtered = []
        for ev in items:
            ts = ev.get("eventTime") or ev.get("lastTimestamp") or ev.get("firstTimestamp")
            if not ts:
                continue
            dt = _parse_time(ts)
            if dt and start <= dt <= end:
                filtered.append(ev)

        reasons: Dict[str, int] = {}
        types: Dict[str, int] = {}
        samples = []
        for ev in filtered[: req.limit]:
            reasons[ev.get("reason", "unknown")] = reasons.get(ev.get("reason", "unknown"), 0) + 1
            types[ev.get("type", "unknown")] = types.get(ev.get("type", "unknown"), 0) + 1
            msg = ev.get("message") or ""
            samples.append(msg)

        return EvidenceItem(
            id=_evidence_id("k8s_events", ns + tr.start + tr.end),
            kind="event",
            source=self.provider_id,
            time_range=tr,
            query=" ".join(cmd),
            summary=f"Found {len(filtered)} kubectl events in the time window.",
            samples=samples[: req.limit],
            top_signals={"reasons": reasons, "types": types, "namespace": ns},
            pointers=[],
            tags=["k8s", "events"],
        )


def _run(cmd: List[str], kubeconfig_env: Optional[str]) -> str:
    env = os.environ.copy()
    if kubeconfig_env and kubeconfig_env in env:
        env["KUBECONFIG"] = env[kubeconfig_env]
    out = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT)
    return out.decode("utf-8", errors="ignore")

def _parse_time(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def _evidence_id(prefix: str, content: str) -> str:
    import hashlib
    h = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{h}"
