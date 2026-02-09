from __future__ import annotations
import hashlib
import io
import re
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from core.models import EvidenceItem, DeployQueryRequest, TimeRange

GITHUB_API = "https://api.github.com"

class GitHubActionsDeployTracker:
    """
    Adapter that treats CI workflow runs as a deployment tracker.
    Config:
      - token_env: "DEPLOY_TOKEN" (or reuse VCS_TOKEN)
      - repo_map: { "<subject>": "<owner>/<repo>" }
      - workflow_path_map: { "<subject>": ".github/workflows/deploy.yml" }
      - markers: { environment: "...", service: "...", sha: "...", ... }
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.token = _env_required(config.get("token_env"))

        self.repo_map = config.get("repo_map", {})
        self.workflow_path_map = config.get("workflow_path_map", {})
        self.markers = config.get("markers", {})

    def list_deployments(self, req: DeployQueryRequest) -> EvidenceItem:
        repo = self._resolve_repo(req.subject)
        workflow_paths = self._resolve_workflows(req.subject)
        tr = req.time_range
        branch_allowlist = self.config.get("branch_allowlist") or []

        runs = []
        for workflow_path in workflow_paths:
            runs.extend(self._list_runs(repo, workflow_path, tr, limit=req.limit, branch_allowlist=branch_allowlist))

        # Provide deployment refs as "run:<id>"
        refs = [f"run:{r['run_id']}" for r in runs]

        return EvidenceItem(
            id=_evidence_id("deploy_runs", repo + workflow_path + tr.start + tr.end),
            kind="deployment",
            source=self.provider_id,
            time_range=tr,
            query=f"deploy_runs:{workflow_path}",
            summary=f"Found {len(runs)} deployment run candidates in the time window.",
            samples=[],
            top_signals={"deployment_refs": refs, "runs": runs},
            pointers=[{"title": "Repository", "url": f"https://github.com/{repo}"}],
            tags=["deploy", "runs"],
        )

    def get_deployment_metadata(self, deployment_ref: str) -> EvidenceItem:
        # deployment_ref format: "run:<id>"
        if not deployment_ref.startswith("run:"):
            raise ValueError(f"Unsupported deployment_ref: {deployment_ref}")
        run_id = int(deployment_ref.split(":", 1)[1])

        # We need repo to fetch logs; safest is to store repo in run refs in v2.
        # In v1 we require the caller (KB binding) to have a single-repo subject mapping.
        # We'll choose the first mapping if ambiguous.
        repo = self._infer_single_repo()
        metadata = self._extract_markers_from_run_logs(repo, run_id, self.markers)

        return EvidenceItem(
            id=_evidence_id("deploy_meta", repo + str(run_id)),
            kind="deployment",
            source=self.provider_id,
            time_range=TimeRange(start="", end=""),
            query=f"deploy_run_logs:{run_id}",
            summary="Extracted deployment metadata markers from deployment run logs.",
            samples=[],
            top_signals={"deployment_ref": deployment_ref, "metadata": metadata},
            pointers=[{"title": "Run", "url": f"https://github.com/{repo}/actions/runs/{run_id}"}],
            tags=["deploy", "metadata"],
        )

    # ---- internal helpers ----

    def _resolve_repo(self, subject: str) -> str:
        repo = self.repo_map.get(subject)
        if not repo:
            raise ValueError(f"Deploy tracker cannot resolve repo for subject '{subject}'. Provide repo_map.")
        return repo

    def _resolve_workflows(self, subject: str) -> List[str]:
        wf = self.workflow_path_map.get(subject)
        if not wf:
            raise ValueError(f"Deploy tracker cannot resolve workflow path for subject '{subject}'. Provide workflow_path_map.")
        if isinstance(wf, list):
            return wf
        return [wf]

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "sre-rca-agent",
        }

    def _list_runs(self, repo_full_name: str, workflow_path: str, tr: TimeRange, limit: int, branch_allowlist: List[str]) -> List[Dict[str, Any]]:
        owner, repo = repo_full_name.split("/", 1)
        url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/workflows/{workflow_path}/runs"

        with httpx.Client(timeout=20.0, headers=self._headers()) as client:
            r = client.get(url, params={"per_page": min(50, max(10, limit))})
            r.raise_for_status()
            data = r.json()

        start_dt = datetime.fromisoformat(tr.start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(tr.end.replace("Z", "+00:00"))
        if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=timezone.utc)

        out = []
        for run in data.get("workflow_runs", []):
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if created < start_dt or created > end_dt:
                continue
            if branch_allowlist:
                if run.get("head_branch") not in branch_allowlist:
                    continue
            out.append({
                "run_id": run["id"],
                "created_at": run["created_at"],
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "url": run.get("html_url"),
                "head_sha": run.get("head_sha"),
                "head_branch": run.get("head_branch"),
            })

        # Sort by time desc, cap
        out.sort(key=lambda r: r["created_at"], reverse=True)
        return out[:limit]

    def _extract_markers_from_run_logs(self, repo_full_name: str, run_id: int, markers: Dict[str, str]) -> Dict[str, str]:
        owner, repo = repo_full_name.split("/", 1)
        logs_url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"

        with httpx.Client(timeout=30.0, headers=self._headers()) as client:
            r = client.get(logs_url)
            r.raise_for_status()
            zip_bytes = r.content

        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        texts = []
        for name in zf.namelist():
            if name.lower().endswith(".txt"):
                texts.append(zf.read(name).decode("utf-8", errors="ignore"))
        blob = "\n".join(texts)

        extracted: Dict[str, str] = {}
        for k, prefix in markers.items():
            m = re.search(re.escape(prefix) + r"([^\r\n]+)", blob)
            if m:
                extracted[k] = m.group(1).strip()
        return extracted

    def _infer_single_repo(self) -> str:
        # v1: if multiple repos exist, pick first (better: encode repo into deployment_ref)
        repos = list(self.repo_map.values())
        if not repos:
            raise ValueError("Deploy tracker repo_map is empty.")
        return repos[0]

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
