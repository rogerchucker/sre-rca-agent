from __future__ import annotations

from datetime import datetime, timezone

from providers.vcs.github import GitHubVCS
from core.models import ChangeQueryRequest, TimeRange


class DummyResponse:
    def __init__(self, json_data=None):
        self._json = json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        return None


class DummyClient:
    def __init__(self, json_data):
        self._json_data = json_data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        return DummyResponse(json_data=self._json_data)


def test_merged_prs_filters_by_window(monkeypatch):
    in_range = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    out_range = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    data = [
        {"number": 1, "title": "Fix", "merged_at": in_range, "user": {"login": "alice"}, "html_url": "u1"},
        {"number": 2, "title": "Old", "merged_at": out_range, "user": {"login": "bob"}, "html_url": "u2"},
    ]

    monkeypatch.setattr("providers.vcs.github.httpx.Client", lambda **kwargs: DummyClient(data))

    provider = GitHubVCS(
        "vcs_main",
        {"token_env": "VCS_TOKEN", "repo_map": {"payments": "example-org/payments"}},
    )

    tr = TimeRange(start="2024-01-01T10:00:00Z", end="2024-01-01T13:00:00Z")
    req = ChangeQueryRequest(subject="payments", environment="prod", time_range=tr, include_prs=True, include_commits=False, limit=10)
    ev = provider.list_changes(req)
    assert len(ev.top_signals["merged_prs"]) == 1
    assert ev.top_signals["merged_prs"][0]["number"] == 1
