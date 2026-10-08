# OpsPilot v8 acceptance evidence

Scope: local production-build tests and saved execution reports. Publication is checked separately using Sites deployment status. Browser visual interaction and production HTTP behaviour have not been independently verified here.

| Requirement | Result | Evidence / limitation |
|---|---|---|
| Public page with demo data | Implemented; local compiled page verified | Initial HTML includes 12 synthetic complaints; production browser check pending |
| Nonempty dashboard | Verified locally | Counts derive from fixtures and session runs; sample reviewed statuses explicitly labelled |
| Flagship demo | Passed locally | CP-101: Emma Chen, $1,250, conflicting evidence; compiled Worker flow |
| Agent trace | Implemented and tested | Persisted LangGraph nodes, outputs, durations; no private chain of thought |
| Real RAG | Passed with measured misses | Local pretrained embeddings; 24 frozen queries; two queries miss required sources |
| Real citations | Passed required-ID coverage | Original chunk text, offsets, section and document ID; not a semantic-entailment score |
| Tools and database | Passed | D1 linked records; typed read-only MCP contracts and ownership checks |
| Custom trained ML | Passed | Real CFPB delay model plus separate 2,000-row synthetic escalation experiment |
| Loaded model and agent inference | Passed | Saved JSON weights, Python/TypeScript parity and workflow outputs |
| Evaluation metrics | Passed | Computed reports plus session evaluation; no illustrative scores |
| Golden dataset | Passed | 30 financial complaint cases and 30 legacy regression cases |
| Failure analysis | Implemented | Retrieval misses, held-out ML errors, execution/evidence failures; no invented live-LLM failures |
| Human review | Passed | Approve/reject/edit, atomic action creation, stale evidence rejection |
| Audit records | Passed | Original and edited response, evidence revision, timings, model/system versions |
| Cost tracking | Partial | Real usage fields implemented; default provider spend zero; live pricing and hosting costs unmeasured |
| Latency tracking | Passed | Actual node/run durations and session aggregates |
| MCP | Passed locally | Official SDK HTTP and Python stdio checks; production plugin connection pending |
| Docker build and run | Blocked | Recipe and CI container job exist; no Docker/Podman or permitted user namespaces here |
| Tests | Passed | All 16 local release gates; 53 Python tests; compiled Worker end-to-end checks |
| GitHub CI | Blocked | Workflow ready; no OpsPilot GitHub repository found for connected account; no cloud run claimed |
| README and Engineering | Updated | Actual stack and metrics, four résumé versions, design decisions and case study |
| Honest claims | Explicit boundaries | Default deterministic orchestration is not autonomous LLM reasoning; synthetic ML is not real risk validation |

## Remaining priority

1. Connect a dedicated OpsPilot GitHub repository and execute the existing workflow, including its Docker job. Do not publish to an unrelated repository.
2. Independently run the browser demonstration against the published site when supported browser tooling is available.
3. For stronger UBS/Affinda GenAI evidence, configure a real provider through trusted secret setup and evaluate that mode separately. The current usable local mode requires no paid API.
4. Keep enterprise identity, durable queue recovery and larger external validation as future work. Kubernetes is not a priority for this portfolio scope.
