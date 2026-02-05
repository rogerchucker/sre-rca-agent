**1) High-Level Portal Overview**  
The Operations Portal is a calm, evidence-first control plane that unifies awareness, investigation, and safe action execution across environments, with AI assistance that is always explainable and gated by human approval.

- Promise: Reduce time-to-triage with a single, narrative-driven investigation surface.  
- Promise: Tie every action to evidence, approvals, and an auditable chain of reasoning.  
- Promise: Keep signal density high and noise low in all operational modes.  
- Promise: Enable safe, reversible actions with explicit blast-radius previews.  
- Promise: Make AI helpful but never opaque, always citing sources and uncertainty.

**2) Page / Surface Breakdown**  
- Command / Home: purpose: global awareness and prioritization, primary actions: open investigation, acknowledge alert, view summary, primary signals: health summary, active incidents, attention queue, navigation placement: top-level left nav as default.  
- Signals Explorer: purpose: cross-signal exploration and correlation, primary actions: filter timeline, pivot by service, pin evidence, primary signals: metrics, logs, traces, events, navigation placement: top-level left nav.  
- Incident / Investigation View: purpose: guided RCA and decision support, primary actions: add evidence, compare hypotheses, request approval, primary signals: evidence timeline, deploys, config changes, alerts, navigation placement: contextual from alerts/incidents.  
- Action Center: purpose: safe operational execution, primary actions: dry-run, request approval, execute scoped action, primary signals: policy gates, blast radius, rollback status, navigation placement: top-level left nav.  
- Knowledge & History: purpose: institutional learning and reuse, primary actions: open runbook, compare incident patterns, create learning note, primary signals: past incidents, recurring patterns, runbooks, navigation placement: top-level left nav.

**3) Key Components Per Page**  
Command / Home  
- `header`: `GlobalSearchBar`, `EnvironmentSelector`, `ModeToggle`, `UserTrustBadge`  
- `body`: `SystemHealthSummary`, `AttentionNowQueue`, `ActiveIncidentsList`, `AISituationalBrief`  
- `side_panels`: `AlertPeekPanel`, `QuickEvidencePanel`  
- `footer`: `RealtimeStatusTicker`, `AuditTrailShortcut`

Signals Explorer  
- `header`: `SignalTypeSwitcher`, `TimeRangePicker`, `CorrelationModeToggle`  
- `body`: `UnifiedTimeline`, `SignalCorrelationGraph`, `PinnedEvidenceTray`  
- `side_panels`: `SignalFacetPanel`, `EntityContextPanel`  
- `footer`: `StreamLatencyIndicator`, `ExportEvidenceButton`

Incident / Investigation View  
- `header`: `IncidentMetaHeader`, `SeverityBadge`, `ApprovalStateChip`  
- `body`: `EvidenceTimeline`, `HypothesisStack`, `RelatedChangeList`, `ActionRecommendations`  
- `side_panels`: `AIReasoningPanel`, `StakeholderNotesPanel`  
- `footer`: `PolicyGateSummary`, `InvestigationAuditLog`

Action Center  
- `header`: `ActionCategoryTabs`, `EnvironmentScopeSelector`, `RiskLevelBanner`  
- `body`: `ActionCatalog`, `BlastRadiusPreview`, `DryRunResults`  
- `side_panels`: `ApprovalWorkflowPanel`, `RollbackPlanPanel`  
- `footer`: `RateLimitStatus`, `ExecutionAuditLog`

Knowledge & History  
- `header`: `KnowledgeSearch`, `PatternFilterBar`, `TimeHorizonSelector`  
- `body`: `IncidentArchive`, `RecurringPatternBoard`, `RunbookLibrary`  
- `side_panels`: `SimilarityInsightPanel`, `PostmortemSummaryPanel`  
- `footer`: `LearningBacklog`, `ExportKnowledgePack`

**4) Example User Flows**  
- Steady State flow: open `Command / Home` -> scan `AttentionNowQueue` -> open `AISituationalBrief` -> pin a weak signal in `Signals Explorer` -> file a hygiene note.  
- Investigation flow: alert fires -> open `Incident / Investigation View` -> add logs and traces to `EvidenceTimeline` -> review `HypothesisStack` -> request approval for a scoped rollback in `Action Center`.  
- Incident/Threat Response flow: critical alert -> jump to `Incident / Investigation View` -> validate blast radius in `Action Center` -> run dry-run remediation -> obtain human approval -> execute and monitor rollback status.

**5) AI Interaction Examples**  
AI summaries  
- Summary: “Elevated 5xx started at 02:12–02:18 UTC, correlated with deploy `v2026.02.03.4` and new error signatures in Loki for service `payments-api`.” Confidence: 0.71. Evidence: `Loki logs 02:12–02:18 UTC`, `GitHub Actions deploy 02:10 UTC`, `Tempo trace errors 02:13 UTC`.  
- Summary: “Latency regression likely confined to `us-west-2` due to increased p95 in Prometheus and no corresponding errors elsewhere.” Confidence: 0.64. Evidence: `Prometheus p95 01:40–02:20 UTC`, `Grafana regional panel`, `Loki logs show no global errors`.  
- Summary: “Config drift in Terraform apply at 01:55 UTC coincides with new auth failures in Kubernetes events.” Confidence: 0.58. Evidence: `Terraform apply history 01:55 UTC`, `Kubernetes events 01:56–02:05 UTC`, `Loki auth error logs 01:57 UTC`.

AI recommended next-steps  
- Next step: “Compare error rates before and after deploy `v2026.02.03.4` in Signals Explorer.” Why: establishes causal window alignment with deployment evidence.  
- Next step: “Run dry-run rollback for `payments-api` with blast-radius preview in Action Center.” Why: offers reversible mitigation with explicit impact analysis.  
- Next step: “Pull recent config diffs from Terraform and annotate evidence timeline.” Why: validates drift hypothesis and clarifies scope of change.

**6) Optional Future Extensions**  
- Value: Faster handoffs across shifts. Implementation hint: add `ShiftHandoffComposer` with auto-summarized evidence and approvals.  
- Value: Safer autonomous actions. Implementation hint: policy engine for `autonomous_limited` with scoped allowlists.  
- Value: Better exec visibility. Implementation hint: `ExecutiveSummaryView` with outcome metrics and risk posture.  
- Value: Improved anomaly precision. Implementation hint: integrate adaptive baselines per service in `SignalCorrelationGraph`.  
- Value: Stronger incident patterning. Implementation hint: `SimilarityInsightPanel` using embedding-based incident search.  
- Value: Clearer simulation mode. Implementation hint: `SimulationBanner` and sandbox action labels in `ActionCatalog`.  
- Value: Faster approvals. Implementation hint: `ApprovalWorkflowPanel` with Slack or email approvals.  
- Value: More reliable evidence. Implementation hint: evidence capture with immutable `EvidenceSnapshotStore`.  
- Value: Reduced cognitive load. Implementation hint: `AttentionNowQueue` with prioritized intents and confidence.  
- Value: Better runbook adoption. Implementation hint: contextual `RunbookRecommendation` tied to hypotheses.