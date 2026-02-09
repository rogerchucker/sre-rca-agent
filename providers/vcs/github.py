from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List
import hashlib
import httpx

from core.models import EvidenceItem, ChangeQueryRequest, TimeRange

GITHUB_API = "https://api.github.com"

class GitHubVCS:
    """
    Adapter for a VCS provider.
    Config:
      - token_env: "VCS_TOKEN"
      - repo_map: optional mapping subject->repo_full_name
    Subject->repo resolution is done via config, not core.
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.token = _env_required(config.get("token_env"))

        # Optional: map subject -> repo full name
        self.repo_map = config.get("repo_map", {})

    def list_changes(self, req: ChangeQueryRequest) -> EvidenceItem:
        repo = self._resolve_repo(req.subject)
        tr = req.time_range

        prs = []
        if req.include_prs:
            prs = self._merged_prs(repo, tr, limit=req.limit)

        summary = f"Found {len(prs)} merged change records in the buffered window."
        return EvidenceItem(
            id=_evidence_id("changes", repo + tr.start + tr.end),
            kind="change",
            source=self.provider_id,
            time_range=tr,
            query="merged_changes",
            summary=summary,
            samples=[f"#{p['number']} {p['title']}" for p in prs[:10]],
            top_signals={"merged_prs": prs},
            pointers=[{"title": "Repository", "url": f"https://github.com/{repo}"}],
            tags=["changes", "vcs"],
        )

    def _resolve_repo(self, subject: str) -> str:
        repo = self.repo_map.get(subject)
        if not repo:
            raise ValueError(
                f"VCS provider cannot resolve repo for subject '{subject}'. "
                f"Add repo_map in provider config or use a deploy tracker that supplies repo context."
            )
        return repo

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "sre-rca-agent",
        }

    def _merged_prs(self, repo_full_name: str, tr: TimeRange, limit: int) -> List[Dict[str, Any]]:
        owner, repo = repo_full_name.split("/", 1)
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"

        with httpx.Client(timeout=20.0, headers=self._headers()) as client:
            r = client.get(url, params={"state": "closed", "per_page": min(limit, 50), "sort": "updated", "direction": "desc"})
            r.raise_for_status()
            data = r.json()

        start_dt = datetime.fromisoformat(tr.start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(tr.end.replace("Z", "+00:00"))
        if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=timezone.utc)

        out = []
        for pr in data:
            merged_at = pr.get("merged_at")
            if not merged_at:
                continue
            mdt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
            if mdt < start_dt or mdt > end_dt:
                continue
            out.append({
                "number": pr["number"],
                "title": pr["title"],
                "merged_at": merged_at,
                "author": (pr.get("user") or {}).get("login"),
                "url": pr.get("html_url"),
            })
        return out[:limit]

# ---- helpers ----

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