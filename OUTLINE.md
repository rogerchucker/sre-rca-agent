Below is a concrete “from-the-ground-up” blueprint for an Investigation + Root Cause Analysis (RCA)-only SRE agent built with LangGraph and OpenAI tool-calling, fed by a webhook and backed by a static onboarding YAML knowledge base.


## 1. System goals and non-goals

Goals
	•	Accept an incident/alert webhook payload (PagerDuty, Alertmanager, Datadog, etc.).
	•	Determine a time window anchored to the alert/incident.
	•	Gather temporal evidence from the right sources (logs, events, deploys, commits, builds).
	•	Combine evidence with a static knowledge base (YAML).
	•	Produce ranked hypotheses with confidence + “why” + next validations to run.
	•	Output one recommendation: the top hypothesis with highest confidence.

Non-goals (for this v1)
	•	Auto-remediation / writing to prod systems.
	•	Long-term KB ingestion beyond YAML (vector DB, doc loaders).
	•	Full “multi-agent org”—you can do this in one graph cleanly.

## 2. Architecture at a glance

Components
	1.	Webhook Ingest API (FastAPI/Flask)
	2.	KB Loader (reads YAML at startup or per request)
	3.	Evidence Adapters (Loki / CloudWatch / Splunk / kubectl / GitHub / CI / CD)
	4.	LangGraph Orchestrator (state machine + conditional routing)  ￼
	5.	LLM Correlator (OpenAI tool-calling for structured outputs & tool selection)  ￼
	6.	Store/Trace (optional but strongly recommended): LangGraph persistence + tracing/eval loop  ￼

Key idea
	•	Treat evidence gathering as a bounded, typed process. Don’t “dump logs into the model”.
	•	Your tools should return summaries + representative samples + pointers (links/query strings), not megabytes.

## 3. Knowledge base YAML (static onboarding) — a practical schema

This YAML should answer:
	•	What services exist, what they depend on
	•	What telemetry/logging stack is used where
	•	How to fetch evidence (tool mapping + auth references)
	•	Runbooks and known failure modes
	•	Past incidents / common RCAs patterns (lightweight)

This YAML should be able to give the agent  enough structure to:
	•	pick the right evidence sources
	•	understand what “normal” queries/selectors look like
	•	interpret evidence in context

## 4. Evidence model: what to collect, and how to keep it LLM-friendly

Evidence types (normalize everything into a common shape)
	•	Logs (Loki / CloudWatch / Splunk / kubectl logs)
	•	Kubernetes events (kubectl get events)
	•	Deployments (ArgoCD / Spinnaker / Helm history)
	•	Builds (CI runs + artifacts)
	•	Changes (GitHub commits/PRs + file diffs + owners)
	•	Service graph (from YAML deps)
	•	Runbook + known failure modes (from YAML)

Evidence payload format (what each adapter returns)

For each query, return:
	•	source (e.g., loki-prod)
	•	time_range
	•	query
	•	summary (LLM-ready)
	•	top_signals (structured counts, error signatures, pods affected)
	•	samples (small, representative excerpts; cap hard)
	•	pointers (links to dashboards/log explorer or the raw query to reproduce)

This is the easiest way to avoid token blowups while still being actionable.

## 5. LangGraph workflow design (RCA-only)

LangGraph’s core pieces (State / Nodes / Edges) map perfectly here.

State (minimal but sufficient)
	•	incident: parsed webhook + derived fields (service, env, start/end)
	•	kb: loaded YAML slice relevant to the service
	•	plan: what evidence to collect (ordered list)
	•	evidence: collected evidence objects (normalized)
	•	hypotheses: list with confidence + rationale + missing validations
	•	final_recommendation: the top hypothesis + next steps
	•	iteration: to bound loops

Graph nodes (recommended)
	1.	ParseWebhook
	    - Normalize alert/incident payload → incident + time_window.
	2.	LoadKB
	    - Load YAML; extract relevant service + alert config + deps + tooling map.
	3.	PlanEvidence
	    - LLM produces a tool plan (structured) for what to fetch first.
	4.	CollectEvidence
	    - Executes adapters in priority order (logs/events/deploys/changes).
	5.	SummarizeEvidence
	    - Compress raw results into stable summaries + signatures + pointers.
	6.	CorrelateAndHypothesize
	    - LLM generates multiple hypotheses, each tied to specific evidence.
	7.	RankAndDecide
	    - Apply a deterministic scoring pass (see below) + pick the top.
	8.	StopCondition / Iterate
	    - If confidence too low, collect targeted missing evidence (bounded).
	9.	GenerateRCAReport
	    - Final output: top hypothesis + supporting evidence + validations.

    Control flow
	•	Conditional edge: after RankAndDecide
	•	if confidence >= threshold OR iteration >= max_iter → report
	•	else → targeted PlanEvidence (only for missing validations) → CollectEvidence

## 6. OpenAI integration approach (tool-calling + structured outputs)

Use OpenAI tool-calling so the model can:
	•	produce a typed evidence plan
	•	call internal “fetch” tools (your adapters)
	•	emit structured hypotheses

Tools you expose to the model (examples)
	•	query_logs(provider_ref, query, start, end, limit)
	•	get_k8s_events(cluster, namespace, start, end)
	•	get_kubectl_logs(namespace, selector, start, end, limit)
	•	get_deploy_history(app, env, start, end)
	•	get_build_history(repo, branch, start, end)
	•	get_github_changes(repo, start, end, paths=None)
	•	get_runbook(url) (optional; can be preloaded from YAML)

Important design choice
	•	Make tools purely read-only and bounded (time range + limit + sampling).

## 7. Hypothesis ranking: Use hybrid scoring

Use deterministic scoring to makes demos (and real-world reviews) much more credible.

For each hypothesis:
	•	Evidence coverage (0–3): how many evidence types support it? (logs + events + deploy + changes)
	•	Temporal alignment (0–3): do indicators start after the triggering event?
	•	Specificity (0–2): names concrete component/version/error signature
	•	KB match (0–2): aligns with known failure modes or incident patterns in YAML
	•	Contradictions (-0–3): evidence that directly conflicts

Total score → normalize to 0–1 confidence.

LLM’s role
	•	Generate hypotheses + cite which evidence items support each.
	•	Call out missing validations that would raise/lower the score.
	•	But final confidence = your scorer, not just the model.

## 8. Recommended Build Order

    1.	Define YAML schema + loader
	2.	Webhook parser for 1 alert source (Alertmanager or PagerDuty)
	3.	Implement 2 evidence adapters first
	    - kubectl events/logs (works everywhere in K8s)
	    - one logging backend (Loki OR CloudWatch OR Splunk)
	4.	Implement deploy history (ArgoCD/Helm)
	5.	Implement GitHub changes (commits/PRs + diff summary)
	6.	LangGraph graph with bounded iteration + persistence  ￼
	7.	Scoring + final RCA report
	8.	Add tracing/eval harness (Langfuse or equivalent) so you can replay incidents  ￼


## 9. Recommended output format for Agent

A good “SRE-readable” final payload:
	•	Top hypothesis (one sentence)
	•	Confidence (0–1) + score breakdown
	•	Supporting evidence (bulleted, with pointers)
	•	What changed (deploy/build/commit summary)
	•	Impact scope (pods/nodes/regions/users)
	•	Next validations (read-only checks to confirm)
	•	Fallback hypotheses (top 2–3)
