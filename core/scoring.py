from __future__ import annotations
from typing import Dict, List
from core.models import EvidenceItem, Hypothesis, TimeRange

EVIDENCE_TYPES = {"log", "event", "deployment", "change", "build", "metric", "trace"}

def score_hypothesis(
    h: Hypothesis,
    evidence: List[EvidenceItem],
    incident_time_range: TimeRange | None = None,
    kb_slice: Dict | None = None,
) -> Dict[str, float]:
    ev = {e.id: e for e in evidence}
    used = [ev.get(eid) for eid in h.supporting_evidence_ids if eid in ev]

    kinds = {e.kind for e in used if e}
    coverage_types = kinds.intersection(EVIDENCE_TYPES)
    coverage = min(1.0, len(coverage_types) / 4.0)  # 4 distinct signal types => full score

    deploy_signal = 0.0
    for e in used:
        if e and e.kind in {"deployment", "build"} and e.top_signals:
            deploy_signal = 0.8
            break

    specificity = 0.2
    if len(h.statement) >= 80:
        specificity = 0.6
    elif len(h.statement) >= 40:
        specificity = 0.4

    temporal_alignment = 0.0
    if incident_time_range and used:
        start = incident_time_range.start
        end = incident_time_range.end
        aligned = 0
        for e in used:
            if not e or not e.time_range:
                continue
            if e.time_range.start <= end and e.time_range.end >= start:
                aligned += 1
        temporal_alignment = aligned / max(1, len(used))

    kb_match = 0.0
    if kb_slice:
        subject_cfg = (kb_slice or {}).get("subject_cfg", {})
        failure_modes = subject_cfg.get("known_failure_modes", [])
        indicators = []
        for fm in failure_modes:
            indicators.extend(fm.get("indicators") or [])
        stmt = h.statement.lower()
        if any(ind.lower() in stmt for ind in indicators if isinstance(ind, str)):
            kb_match = 1.0

    contradiction_penalty = min(0.6, 0.2 * len(h.contradictions))
    total = (
        0.25 * coverage
        + 0.20 * temporal_alignment
        + 0.20 * kb_match
        + 0.15 * deploy_signal
        + 0.20 * specificity
        - contradiction_penalty
    )
    total = max(0.0, min(1.0, total))

    return {
        "coverage": coverage,
        "temporal_alignment": temporal_alignment,
        "kb_match": kb_match,
        "deploy_signal": deploy_signal,
        "specificity": specificity,
        "contradiction_penalty": contradiction_penalty,
        "total": total,
    }

def rank(
    hypotheses: List[Hypothesis],
    evidence: List[EvidenceItem],
    incident_time_range: TimeRange | None = None,
    kb_slice: Dict | None = None,
) -> List[Hypothesis]:
    out: List[Hypothesis] = []
    for h in hypotheses:
        breakdown = score_hypothesis(h, evidence, incident_time_range, kb_slice)
        h.score_breakdown = breakdown
        h.confidence = breakdown["total"]
        out.append(h)
    out.sort(key=lambda x: x.confidence, reverse=True)
    return out
