from __future__ import annotations

import json

from core import orchestrator
from core.models import EvidenceItem, TimeRange


class StubLogProvider:
    def __init__(self, provider_id: str, config: dict):
        self.provider_id = provider_id

    def query(self, req):
        return EvidenceItem(
            id="logs_1",
            kind="logs",
            source=self.provider_id,
            time_range=req.time_range,
            query="q",
            summary="logs",
            samples=["line"],
            top_signals={},
            pointers=[],
            tags=[],
        )


class StubDeployProvider:
    def __init__(self, provider_id: str, config: dict):
        self.provider_id = provider_id

    def list_deployments(self, req):
        return EvidenceItem(
            id="deploy_1",
            kind="deploy",
            source=self.provider_id,
            time_range=req.time_range,
            query="q",
            summary="deploys",
            samples=[],
            top_signals={"deployment_refs": ["run:1"]},
            pointers=[],
            tags=[],
        )

    def get_deployment_metadata(self, deployment_ref: str):
        return EvidenceItem(
            id="deploy_meta_1",
            kind="deploy",
            source=self.provider_id,
            time_range=TimeRange(start="", end=""),
            query="q",
            summary="meta",
            samples=[],
            top_signals={},
            pointers=[],
            tags=[],
        )


class StubVCSProvider:
    def __init__(self, provider_id: str, config: dict):
        self.provider_id = provider_id

    def list_changes(self, req):
        return EvidenceItem(
            id="change_1",
            kind="change",
            source=self.provider_id,
            time_range=req.time_range,
            query="q",
            summary="changes",
            samples=["pr"],
            top_signals={},
            pointers=[],
            tags=[],
        )


class FakeChat:
    def __init__(self, content: str):
        self._content = content

    def create(self, **kwargs):
        class Choice:
            def __init__(self, content):
                class Msg:
                    def __init__(self, content):
                        self.content = content
                self.message = Msg(content)
        return type("Resp", (), {"choices": [Choice(self._content)]})


class FakeClient:
    def __init__(self, content: str):
        self.chat = type("Chat", (), {"completions": FakeChat(content)})()


def test_orchestrator_run_end_to_end(monkeypatch, kb_path, webhook_payload):
    monkeypatch.setattr(orchestrator.settings, "kb_path", kb_path)

    # Stub provider factories
    def _factory(cls):
        def create(provider_id: str, config: dict):
            return cls(provider_id=provider_id, config=config)
        return create

    stub_factories = {
        "log_store:loki": _factory(StubLogProvider),
        "deploy_tracker:github_actions": _factory(StubDeployProvider),
        "vcs:github": _factory(StubVCSProvider),
    }
    monkeypatch.setattr("providers.FACTORIES", stub_factories)

    hypotheses = {"hypotheses": [{"id": "h1", "statement": "Deploy caused errors", "supporting_evidence_ids": ["deploy_1"], "contradictions": [], "validations": []}]}
    monkeypatch.setattr(orchestrator, "client", FakeClient(json.dumps(hypotheses)))

    report = orchestrator.run(webhook_payload)
    assert report["top_hypothesis"]["id"] == "h1"
    assert report["evidence"][0]["kind"] == "alert"
