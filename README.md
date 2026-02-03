uvicorn api.main:app --reload --port 8080

flowchart TB
  subgraph A[Global Tool Schema]
    S1["catalog/schema.yaml<br/>Defines categories + operations + contracts"]
    S2["schemas/instances.schema.json<br/>Validates instances.yaml structure"]
    S3["schemas/subjects.schema.json<br/>Validates subjects.yaml structure"]
  end

  subgraph B[Environment Catalog]
    I1["catalog/instances.yaml<br/>Concrete provider instances<br/>(id, category, type, ops, config)"]
  end

  subgraph C[Customer Onboarding]
    K1["kb/subjects.yaml<br/>Subjects + bindings + selectors + knowledge"]
  end

  subgraph D[Agent Core]
    G1["LangGraph RCA Workflow<br/>capability-driven nodes<br/>(logs, deploys, changes)"]
    R1["ProviderRegistry<br/>resolves bindings + enforces ops"]
    L1["LLM Hypothesizer<br/>vendor-neutral prompts"]
    SC["Deterministic Scorer<br/>ranks hypotheses"]
  end

  subgraph E[Adapters / Providers]
    P1["log_store adapter(s)<br/>intent → backend query"]
    P2["deploy_tracker adapter(s)<br/>deploy history + metadata"]
    P3["vcs adapter(s)<br/>change history"]
  end

  S2 --> I1
  S3 --> K1
  S1 --> I1

  I1 --> R1
  K1 --> R1

  R1 --> G1
  G1 --> P1
  G1 --> P2
  G1 --> P3
  P1 --> G1
  P2 --> G1
  P3 --> G1

  G1 --> L1 --> SC --> G1