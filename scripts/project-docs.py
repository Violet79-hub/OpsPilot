"""Generate portfolio documents from measured artifacts, never illustrative scores."""
from pathlib import Path
import json,shutil
r=Path(__file__).resolve().parents[1];b=json.loads((r/'lib/agent/benchmark-summary.json').read_text());m=json.loads((r/'ml/artifacts/evaluation.json').read_text());s=json.loads((r/'ml/escalation/evaluation.json').read_text());fin=b['suites'][1];retr=b['retrieval'];url='https://opspilot-evaluated-demo.alexis707199.chatgpt.site/'
architecture='''```mermaid
flowchart TD
 U[Complaint UI] --> API[Worker API]
 API --> G[LangGraph state workflow]
 G --> R[Local semantic retrieval]
 G --> T[Validated MCP tools]
 G --> M[Two saved ML models]
 R --> P[Synthetic policy chunks]
 T --> DB[D1 complaint and financial records]
 M --> A[Recommendation]
 P --> A
 DB --> A
 A --> E[Evaluator: one bounded repair]
 E --> H[Human review or evidence block]
 H --> L[Versioned audit records]
```'''
metrics=f"Financial regression: {fin['passed']}/{fin['cases']} cases. Expected decision match {fin['decision']:.1%}; required citation coverage {fin['citations']:.1%}; expected tool coverage {fin['tool_coverage']:.1%}. These are deterministic policy regressions, not LLM accuracy or autonomous tool-choice scores. Mean local test latency {fin['mean_latency_ms']} ms. Local semantic Recall@3 {retr['recall']:.1%}; MRR@6 {retr['mrr']:.3f} on 24 labelled queries. Historical response-delay test F1 {m['test']['f1']:.3f}, ROC-AUC {m['test']['roc_auc']:.3f}. Synthetic escalation test F1 {s['test']['f1']:.3f}, ROC-AUC {s['test']['roc_auc']:.3f}; synthetic results do not establish real escalation performance. Local mode makes no provider calls; hosting costs excluded."
readme=f'''# OpsPilot
Evaluated financial complaint workflows with semantic retrieval, bounded tools, two saved ML models and human-controlled recommendations.

Built by Hanxi Li (Alex), with AI-assisted implementation.

[Live Demo]({url}) · [Architecture](#architecture) · [Evaluation Results](#evaluation-results) · [Design decisions](docs/design-decisions.md) · [Resume versions](docs/resume-bullets.md)

GitHub repository: https://github.com/Violet79-hub/OpsPilot. Source is also versioned in Sites. See GitHub Actions for the actual cloud verification status; local test reports are not proof of a cloud pass.

## Problem and why this project
Financial complaints combine incomplete evidence, disputed facts and asymmetric consequences. A reviewer needs an inspectable recommendation and an audit trail. OpsPilot demonstrates that workflow using synthetic business records, without issuing payments or contacting customers.

## Architecture
{architecture}

Actual hosted stack: React/Vinext, TypeScript LangGraph, Cloudflare Worker, D1, local static embeddings, portable scikit-learn model exports and a stateless MCP endpoint. Python FastAPI is a separate included service, not the hosted Worker. PostgreSQL, pgvector, Kubernetes and a hosted Python container are not required by the running Site and are not claimed as deployed.

## Demo guide
The initial HTML contains 12 synthetic cases with customer, transaction, account, amount, date, evidence and labelled prior history. Initial reviewed/review-pending statuses are synthetic fixtures, never fabricated user actions. Run Demo Case executes CP-101: Emma Chen disputes $1,250 while merchant and customer evidence conflict. The graph reads linked records, computes model signals, retrieves policy and escalates for a human. Missing evidence case CP-110 blocks approval. Five historical public CFPB replays remain separately labelled.

## Agent workflow and tool calling
Typed state contains plan, original retrieval results, tool outputs, financial records, model outputs, recommendation, evaluator checks, system version and timings. Nodes cover planning, retrieval, business tools, ML inference, answer and evaluation; approval is a subsequent atomic database transaction. The default plan and answer use deterministic policy logic. Provider-assisted planning/generation exists but has not been run with a real key. Do not describe default execution as autonomous LLM reasoning.

## RAG
A pinned Apache-2.0 pretrained static embedding table runs inside the Worker at 128 dimensions after per-token int8 quantization. WordPiece tokenization, normalized pooled embeddings, 1,600-character chunks with 200-character overlap and cosine ranking support English search. Evidence shows document ID, section, chunk ID, offsets, text and score. Exact authoritative policy lookup may supplement retrieval and is traced separately; it receives no credit in independent ranking metrics. This is a small in-memory vector search, not a deployed vector database. [Reproduction](docs/SEMANTIC_RETRIEVAL.md).

## Custom ML models
The historical response-delay classifier uses 20,000 real CFPB structured records and chronological 12,000/4,000/4,000 splits. Logistic regression was selected against alternatives using validation results. It predicts historical timely=No, not fraud or refund entitlement. Poor precision and unsupported-category abstention are displayed.

The separate escalation experiment uses 2,000 explicitly synthetic labelled examples with disjoint 1,200/400/400 splits. The label-generating mechanism is published in `ml/escalation/train.py`. Validation average precision selects Random Forest versus scaled Logistic Regression; validation selects the threshold. Saved joblib and JSON artifacts are checked against independent Python/TypeScript inference. These scores measure synthetic mechanism recovery only. Customer vulnerability and fraud flags come from fixtures, never inferred from identity. Both models are shadow-only and cannot authorise money movement.

## Evaluation results
{metrics}

All displayed metrics are derived by `scripts/benchmark-summary.py` from saved test executions. Run Evaluation in the Site for a new session-owned batch. Inspect per-case failures rather than a single aggregate score. Retrieval misses are independent of mandatory policy lookup. Citation coverage checks expected IDs, not full semantic entailment.

## Failure analysis
Persist failed execution states, missing records, unsupported ML inputs, citation checks and provider errors. Show the genuine held-out errors for both models and retrieval misses. Do not manufacture an LLM failure before live-provider execution exists. A failed evaluator can trigger one answer repair in live mode; further failure blocks approval.

## Human review and auditability
Reviewer edits are stored separately from the original generated/template answer. Approval/rejection and timestamps are recorded, with one action per run enforced transactionally. Evidence revisions invalidate old recommendations, and requests for information pause progress. Initial sample history is visibly distinct from new user actions. Session data is isolated via opaque HttpOnly cookies; it is not enterprise authentication.

## MCP
`POST /mcp` supports initialization, discovery and read-only tools: get_complaint, get_customer, get_transaction, get_account, predict_response_delay, predict_escalation_risk, search_company_policy and get_model_card. Linked business tools accept a case ID and validate access through that complaint. Sites supplies identity at the hosting boundary. The graph reuses the JSON-RPC dispatcher in process; SDK HTTP tests verify transport separately. The Python stdio server is a separate local example. Run `node tests/mcp.integration.mjs /path/to/backend/python` and `PYTHONPATH=backend /path/to/backend/python scripts/mcp_smoke.py`. A production plugin connection requires the user's connection step.

## Testing and local release pipeline
Install JavaScript dependencies with `bash scripts/install-pnpm.sh`. Install `backend/requirements.txt` and `ml/requirements.txt` in separate Python environments. Run:

```sh
python scripts/release-pipeline.py --backend-python /path/to/backend/python --model-python /path/to/model/python
```

The fail-fast pipeline runs ESLint, type checking, model parity and reproducibility, API/D1/LangGraph regressions, Python tests, client session initialization, retrieval evaluation, official MCP SDK checks, production build and compiled-Worker end-to-end checks. Logs and measured durations are in `verification/`. Browser visual interaction remains unverified where the required browser tooling is unavailable.

## CI/CD and Docker
`.github/workflows/verify.yml` runs the same gates plus a Docker build/start/health-check job when the source is placed in an authorised GitHub repository. It is configuration, not evidence of a completed cloud run. Current environment lacks Docker/Podman and user namespaces; no local container runtime pass is claimed.

```sh
docker build -t opspilot-backend -f backend/Dockerfile .
docker run --rm -p 8000:8000 opspilot-backend
```

## Deployment and lifecycle
The existing public Site serves the Worker with durable D1 bindings. Native Sites publication, not GitHub Actions, currently deploys it. Background execution uses Worker waitUntil, not a durable queue with guaranteed retries. Artifact hashes, shadow quality gates and a local rollback drill are implemented; local rollback uses two packages of the same model and is not a production rollback test.

## Cost, limitations and future work
Node and total durations are measured. Provider tokens are recorded when returned; no real provider execution or verified provider pricing is available. Local mode has zero provider calls. Hosting costs are not measured. Remaining gaps: real provider evaluation, connected GitHub CI, executed Docker, independent browser QA, enterprise identity, durable job recovery, larger external retrieval labels and validation on actual escalation outcomes. Kubernetes is deliberately not prioritised.

## AI usage disclosure
AI assisted code, test and documentation development. Claims must be backed by this source and reproducible reports. Interview ownership should reflect engineering choices the author can explain and reproduce, not imply unaided implementation or production financial deployment.
'''
(r/'README.md').write_text(readme)
design='''# Design decisions

Financial complaints expose evidence conflict and review consequences while allowing safe synthetic business data. Human review remains mandatory, including for a positive refund recommendation. Writes create internal actions only.

LangGraph provides typed state, explicit nodes and one bounded repair branch. Default execution uses deterministic planning; a graph alone does not establish autonomous LLM behaviour. RAG separates retrieved evidence from generated wording. Local static embeddings avoid provider setup while preserving actual vector inference; the small corpus does not justify a vector database. D1 is the deployed relational store; pgvector/PostgreSQL would be a future scale decision, not a label to add now.

The real-data delay experiment selected Logistic Regression using validation evidence. The synthetic escalation experiment selected Random Forest over a Logistic Regression baseline; LightGBM/XGBoost were not used because a reproducible portable forest already meets the small experiment's purpose. Synthetic escalation labels are not evidence of real predictive validity. The LLM is not the sole decision mechanism: authoritative policy, linked records, model abstention and human controls remain independent.

Evaluation separates retrieval ranking, expected tool coverage, deterministic decisions and ML held-out metrics. Synthetic complaints make the public demonstration usable without personal data. Tests deliberately include missing evidence, attacks and unknown records. One repair avoids unbounded execution and cost. No claimed confidence is derived merely from the fraction of checks passed.
''';(r/'docs/design-decisions.md').write_text(design)
bullets=f'''# Truthful résumé versions

AI-assisted implementation. Use only claims you can explain and reproduce. These bullets do not claim real LLM generation, cloud CI execution, Docker runtime validation or production financial use.

## Applied AI / Agentic AI
- Built a LangGraph financial-complaint workflow integrating local semantic retrieval, validated MCP tools, saved ML inference, evidence checks and versioned human approval.
- Implemented {fin['cases']} complaint regression cases and a separate 24-query retrieval benchmark, measuring {retr['recall']:.1%} Recall@3 while retaining failure evidence and limitations.

## MLOps
- Packaged and served versioned scikit-learn artifacts in Python and a deployed TypeScript Worker; verified inference parity, dataset hashes and held-out metrics.
- Automated local test/build/model gates and rehearsed artifact activation, corruption rejection and local rollback; supplied Docker and GitHub Actions configurations with execution gaps explicitly documented.

## AI Solutions
- Developed a persistent financial complaint casework application with linked customer/transaction/account tools, evidence inspection, reviewer edits and isolated session records.
- Delivered a one-click synthetic conflict-evidence demonstration, model validation reports, API documentation and reproducible handover source.

## Data Science
- Trained a chronological CFPB response-delay classifier on 20,000 structured records, achieving test ROC-AUC {m['test']['roc_auc']:.3f} and F1 {m['test']['f1']:.3f}; documented severe class imbalance, false positives and out-of-domain abstention.
- Compared Logistic Regression and Random Forest on a separately labelled 2,000-row synthetic escalation experiment (test F1 {s['test']['f1']:.3f}); explicitly limited claims to synthetic data and integrated the saved model into the application workflow.
''';(r/'docs/resume-bullets.md').write_text(bullets)
case=f'''# Portfolio case study — OpsPilot

## Problem
A financial operations reviewer must reconcile disputed evidence before recommending an action. An opaque answer is insufficient.

## System and architecture
{architecture}

## Workflow, RAG and custom models
A flagship synthetic complaint links a customer, account and $1,250 transaction. The workflow retrieves policy excerpts, reads records, calls the real-data response-delay model and synthetic escalation forest, validates the policy recommendation and pauses for review. Local semantic inference requires no provider API. The two models have different targets and datasets and are never presented as interchangeable risk estimates.

## Evaluation and results
{metrics}

## Failure analysis and governance
Missing evidence blocks approval. Disputed evidence, vulnerability and fraud flags trigger specialist review. Low model precision, retrieval misses and synthetic-label limitations are visible. Original recommendations, edited replies, source references and versioned evidence are retained. The system never issues a payment.

## My contribution
Workflow orchestration, typed tool contracts, model integration, evaluation harness, casework experience, review concurrency, source packaging and deployment were developed with AI assistance. Python service and hosted Worker boundaries are documented. Cloud CI and Docker runtime verification remain pending.

## What I learned
A graph is only useful when its state and failures are inspectable. Retrieval metrics must be measured before policy supplementation. Synthetic labels can test integration but cannot substantiate real predictive capability. Honest model limitations and blocked actions are product behaviour, not footnotes.
''';(r/'docs/portfolio-case-study.md').write_text(case)
public=r/'public/project';public.mkdir(parents=True,exist_ok=True)
for src in [r/'README.md',r/'docs/design-decisions.md',r/'docs/resume-bullets.md',r/'docs/portfolio-case-study.md',r/'docs/JD_MAPPING.md',r/'docs/ACCEPTANCE.md',r/'docs/INTERVIEW.md',r/'docs/RECRUITER_DEMO.md']:shutil.copy2(src,public/src.name)
print('README, design decisions, four résumé versions and case study generated from reports')
