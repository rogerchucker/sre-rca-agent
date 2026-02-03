from __future__ import annotations
from typing import Dict, List
from core.models import EvidenceItem, Hypothesis

def score_hypothesis(h: Hypothesis, evidence: List[EvidenceItem]) -> Dict[str, float]:
    ev = {e.id: e for e in evidence}
    used = [ev.get(eid) for eid in h.supporting_evidence_ids if eid in ev]

    kinds = {e.kind for e in used if e}
    coverage = min(1.0, len(kinds) / 3.0)  # logs + deploy + change ideal

    deploy_signal = 0.0
    for e in used:
        if e and e.kind == "deploy" and e.top_signals:
            deploy_signal = 0.8
            break

    specificity = 0.2
    if len(h.statement) >= 80:
        specificity = 0.6
    elif len(h.statement) >= 40:
        specificity = 0.4

    contradiction_penalty = min(0.6, 0.2 * len(h.contradictions))
    total = 0.40 * coverage + 0.35 * deploy_signal + 0.25 * specificity - contradiction_penalty
    total = max(0.0, min(1.0, total))

    return {
        "coverage": coverage,
        "deploy_signal": deploy_signal,
        "specificity": specificity,
        "contradiction_penalty": contradiction_penalty,
        "total": total,
    }

def rank(hypotheses: List[Hypothesis], evidence: List[EvidenceItem]) -> List[Hypothesis]:
    out: List[Hypothesis] = []
    for h in hypotheses:
        breakdown = score_hypothesis(h, evidence)
        h.score_breakdown = breakdown
        h.confidence = breakdown["total"]
        out.append(h)
    out.sort(key=lambda x: x.confidence, reverse=True)
    return out