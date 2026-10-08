# Interview walkthrough

## 90-second demonstration

Open Casework. Select CP-101 (Emma Chen, disputed $1,250 transaction) and assess it with Policy workflow + trained model. Inspect plan, retrieval IDs, database lookup, `ml_inference` probability, timing and the human-review gate. Explain that generation is deterministic in this mode but the trained coefficients are real. Open ML Model: baseline, chronological splits, precision/recall and false positives. Run Evaluation: 30 decision cases and separately 24 retrieval queries. Open Failure Analysis and demonstrate a missing order. Open Monitoring and show actual session latency and counters. Download Source & tests for reproducibility.

## Answers grounded in this implementation

**How did you build the agent workflow?** A persisted LangGraph state carries plan, retrieved documents, tool outputs, ML prediction, answer, validation and reviewer state. The hosted executor has explicit nodes and a bounded answer repair branch.

**Why LangGraph?** It makes conditional control and state inspectable and testable. A linear SDK call would not capture repairs and review gates as clearly. The graph ends at review preparation; the API controls the subsequent durable approval transaction.

**How does RAG work?** Policy and session-private uploads are ingested and chunked. Default mode uses a pinned open-source static retrieval embedding model, 128-dimensional Matryoshka truncation and per-token int8 quantization, WordPiece tokenization, mean pooling and cosine ranking. It runs inside the Worker without any model API; keyword ranking remains a comparison mode. Live mode uses provider embeddings, cached corpus vectors and query similarity. Mandatory trusted policies may subsequently be added for safety; they are not credited to independent retrieval ranking.

**How did you evaluate retrieval?** A frozen 24-query labelled set compares the raw top three with expected policy IDs, calculating hit rate, macro recall, precision and MRR. The benchmark is small and synthetic. Local semantic quality is measured separately against the original keyword baseline; provider semantic quality remains unverified without the key.

**How does it choose tools?** Live planning returns allowlisted names and explicit identifiers. The executor checks identifiers against the user's request and validates required tools for the intent. Rules mode supplies the deterministic baseline. Tools have narrow read/calculation contracts.

**What did MCP do?** The included Python stdio server exposes policy search and order/customer reads via real MCP JSON-RPC. Its client smoke test performs handshake, lists tools and calls them. The hosted /mcp endpoint exposes eight tools: complaint/customer/transaction/account lookup, two model scorers, policy search and the model card. The graph uses the same JSON-RPC dispatcher in process for linked record lookup and inference; it does not make a network round trip. An official Python SDK client verifies the Streamable HTTP endpoint locally, including authentication rejection. Production plugin connection is a separate user step.

**How do you prevent hallucination?** Require matching database records, authoritative verdicts, source IDs and structured schemas. Compare generated decision/amount to deterministic policy, repair or block. These controls reduce risk; citation presence alone is not full semantic grounding.

**How do you know it is good?** Separate operations assertions, retrieval labels and ML temporal test metrics. Do not collapse these into a single accuracy number. Check negative cases, concurrency, private sessions and artifact parity as well as happy paths.

**Failure cases?** Missing orders block; unknown model products abstain; classifier false positives are numerous; keyword retrieval misses paraphrases; provider outages fail honestly. View persisted failures and temporal model errors in the dashboard.

**Latency and cost?** Actual node and end-to-end duration plus provider-returned token counts. p50/p95 are calculated from this session's recorded runs. Dollar cost stays unmeasured until versioned price configuration is verified. Rules mode has no provider calls.

**Your own ML model?** Real CFPB data, a prior baseline, validation-selected LR versus forest, temporal test, saved joblib and portable JSON weights. The Agent invokes the real scorer for a supported complaint and records reviewer-priority context. It cannot authorise an action. A second, separate escalation experiment trains a Random Forest against a Logistic Regression baseline on 2,000 synthetic labelled rows. Its 1,200/400/400 split, artifact and held-out errors are reproducible; its metrics establish synthetic integration performance, not real escalation validity.

**Production deployment?** React and TypeScript workflow are packaged as Workers with D1 migrations and published to the existing Site. Python has a separate container recipe with the same artifact. Do not describe that container as deployed. CI configuration is included; GitHub execution requires a connected repository.

**Monitoring?** Persist statuses, node durations, latency, usage, required tool/source checks, review state and failure reasons. Current dashboard is session-scoped, not an operator-wide alerting platform. Production needs aggregate tenancy-safe alerts and drift feedback.

**Why human approval?** Financial recommendations and model errors have asymmetric consequences. Approval validates policy and context; revision control ensures exactly one internal action. The public demo performs no external transaction.

**Insufficient evidence?** Stop with `insufficient_evidence`, zero authorised amount and a blocked review endpoint. Request the correct record or investigate failures; never invent a customer or order.

## Truthful project bullets

UBS: Extended an auditable LangGraph operations agent with policy retrieval, allowlisted tools, validation and human approval; separated decision regression from retrieval evaluation and documented provider and governance limits.

Affinda: Integrated a reproducible scikit-learn response-delay model into an existing React/database workflow; implemented strict inference APIs, artifact parity checks, failure analysis and session monitoring.

Enexis: Packaged Python inference and training artifacts with chronological evaluation, container configuration and CI checks; deployed the existing Workers/D1 application and documented the boundary between hosted and local runtimes.

Do not claim live provider evaluation, hosted Python, connected production MCP client, GitHub CI execution or Docker runtime validation until those steps actually happen. This is AI-assisted implementation: only claim engineering ownership you can explain and reproduce yourself.
