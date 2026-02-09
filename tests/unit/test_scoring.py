from core.scoring import score_hypothesis, rank
from core.models import EvidenceItem, Hypothesis, TimeRange


def _evidence(eid: str, kind: str) -> EvidenceItem:
    return EvidenceItem(
        id=eid,
        kind=kind,
        source="test",
        time_range=TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z"),
        query="q",
        summary="s",
        samples=[],
        top_signals={"x": 1},
        pointers=[],
        tags=[],
    )


def test_score_hypothesis_coverage_and_contradictions():
    evidence = [
        _evidence("e1", "log"),
        _evidence("e2", "deployment"),
        _evidence("e3", "change"),
    ]
    h = Hypothesis(
        id="h1",
        statement="Specific hypothesis about a deploy related regression.",
        confidence=0.0,
        score_breakdown={},
        supporting_evidence_ids=["e1", "e2", "e3"],
        contradictions=["contradiction"],
        validations=[],
    )

    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    kb_slice = {
        "subject_cfg": {
            "known_failure_modes": [
                {"name": "deploy_regression", "indicators": ["deploy related regression"]}
            ]
        }
    }
    breakdown = score_hypothesis(h, evidence, tr, kb_slice)
    assert breakdown["coverage"] == 0.75
    assert breakdown["temporal_alignment"] == 1.0
    assert breakdown["kb_match"] == 1.0
    assert breakdown["deploy_signal"] == 0.8
    assert breakdown["contradiction_penalty"] > 0.0


def test_rank_sorts_by_confidence():
    evidence = [_evidence("e1", "log")]
    h1 = Hypothesis(
        id="h1",
        statement="Short",
        confidence=0.0,
        score_breakdown={},
        supporting_evidence_ids=["e1"],
        contradictions=[],
        validations=[],
    )
    h2 = Hypothesis(
        id="h2",
        statement="This statement is longer and should score higher.",
        confidence=0.0,
        score_breakdown={},
        supporting_evidence_ids=["e1"],
        contradictions=[],
        validations=[],
    )

    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    ranked = rank([h1, h2], evidence, tr, {"subject_cfg": {}})
    assert ranked[0].id == "h2"
