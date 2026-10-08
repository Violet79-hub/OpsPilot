# JD → project evidence mapping (2026-10-07)

Priority: UBS Graduate AI Engineer > Affinda entry-level AI Solutions Engineer > Enexis Junior MLOps. Main positioning: Applied / Agentic AI. P0: two-day core; P1: strongly recommended; P2: only with time. A = directly emphasised in retrieved JD; B = useful supporting evidence, not an explicit universal requirement; — = not a primary requirement. User-requested keywords do not automatically become verbatim JD claims.

Sources: [UBS official](https://jobs.ubs.com/TGnewUI/Search/Home/Home?PageType=JobDetails&jobid=336641&partnerid=25008&siteid=5131), [Affinda official](https://affindagroup.applytojob.com/apply/clEg4nAyZU/Affinda-Group-AI-Solutions-Engineer), [Enexis official](https://werkenbij.enexis.nl/vacatures/mlops-engineer-16389). UBS official indexed responsibilities were read; its dynamic page did not expose complete qualifications, so same-title mirrored qualifications were secondary evidence, not fully verified official text. Affinda direct page returned 410; its full official indexed JD was read. Enexis full official current text was read; title includes Junior/medior. These retrieval limits must remain visible.

| JD Requirement | UBS | Affinda | Enexis | Current OpsPilot Evidence | Gap | Priority | Planned Implementation |
|---|---|---|---|---|---|---|---|
| AI agents / agentic platform | A | A | — | Existing real LangGraph + D1 workflow | Provider generation not configured | P0 | Preserve graph; add trained ML node; real provider validation pending key |
| GenAI / business applications | A | A | B | Operations review UI and rule baseline | No real generation evidence | P0 | Structured planner/answer with real provider key; explicitly blocked meanwhile |
| LangGraph / agentic frameworks | A | A | — | TypeScript graph with repair and state | Explain design choices | P0 | CASE_STUDY and node timings |
| RAG / knowledge retrieval | A | A | — | Policy ingestion and keyword/semantic code | Semantic behaviour not verified | P0 | Independent ranking benchmark; provider semantic run pending key |
| Embeddings | A | B | — | Provider vector path and cache | Only mock contract verified | P0 | Verify real embedding requests once key accessible |
| Enterprise APIs / tool integration | A | A | B | Strict database record tools | Need inspectable custom inference | P0 | Hosted prediction tool/API; Python API parity |
| Databases | A | A | B | Durable D1 records, reviews and batches | Need concurrency/isolation regression | P0 | Real D1 tests and unique approval transaction |
| Evaluation pipeline | A | A | B | 30 synthetic decision cases | Retrieval scores previously confounded by policy completion | P0 | Separate 24-query raw ranking benchmark, ML temporal test |
| Quality / reliability / safety | A | A | A | Policy checks, review CAS | Need negative cases and limits | P0 | Evidence block, OOD abstention, injection and concurrency tests |
| Responsible AI / governance | A | A | B | Human review, untrusted uploads | No production certification | P0 | Shadow model, failure display, explicit boundaries |
| AI / model lifecycle | A | A | A | Model-provider configuration | No trained artifact lineage | P0 | Sanitised real data, hashes, splits, model card, saved artifacts |
| Custom ML integration | B | B | A | None in original Site | Needs legitimate outcome and actual call | P0 | CFPB response-delay model integrated into graph |
| Python backend | B | A | A | Existing separate FastAPI backend | Not hosted; model endpoint absent | P0 | Bring same source into project; strict model endpoint and tests |
| React/frontend | B | A | — | Existing console | Recruiter evidence difficult to find | P0 | Project Overview, ML, Failure Analysis, Monitoring |
| Deployment / production engineering | A | A | A | Existing published Worker and D1 | Current changes not yet published | P0 | Build compiled Worker, save/publish same Site |
| Monitoring | A | A | A | Saved run state | Aggregate actual latency/failure evidence | P0 | Session p50/p95, node duration, usage and recorded failures |
| Continuous improvement | A | A | A | Golden regression | No visible failure feedback loop | P0 | Actual model errors/retrieval misses and next-step notes |
| Project explanation / handover | B | A | B | Source exists | Interview and runtime boundary unclear | P0 | Source archive, runbook, case study, truthful role bullets |
| MCP | A | A | — | Python stdio plus hosted HTTP endpoint, official SDK test; workflow reuses JSON-RPC dispatcher | Production plugin client not connected | P1 | Four read-only tools; identity checks; in-process workflow bridge |
| Background jobs | B | A | B | Local Python thread-pool executor | Hosted execute is synchronous, no durable queue | P1 | Durable job queue and cancellation later |
| Cost awareness | B | A | B | Provider token usage | No verified versioned price config | P1 | Expose actual usage and unmeasured cost; configure prices later |
| Security / compliance | A | A | A | Session isolation, trusted policy, CSRF | Auth/RBAC/retention and audit certification missing | P0/P1 | Core tests now; production security review later |
| CI/CD / Git | B | B | A | Site Git source, local verification | No connected GitHub execution | P1 | CI file with reproducible commands; do not claim run status |
| Containerisation | — | B | A | Python Dockerfile | Docker runtime unavailable | P1 | Package same model; document unverified container execution |
| Reproducibility | B | A | A | Locked JS dependencies | Model data/pipeline missing originally | P0 | Retained data/provenance, seed, requirements, artifacts and parity |
| Cloud/platform specialisation | — | B | A | Workers/D1 deployment | No AWS/Azure/Kubernetes experience proved | P2 | Do not transform project into DevOps platform |

## Shared requirements

All three value reliable delivery, testing, deployment, Python/software competence, lifecycle thinking and explainable engineering. RAG, embeddings and MCP are primarily the UBS/Affinda fit; they are not all three's explicit common requirements.

## Low-value single-role additions

A Kubernetes cluster, cloud-specific infrastructure replica or complex platform operator would mainly serve Enexis and dilute the applied AI story. A deep neural model without suitable data would serve none. MCP is more important for UBS/Affinda, so a real small protocol integration is worth preserving rather than decorating the UI with a label.

## Original evidence

The existing v2 already proved a hosted LangGraph graph, D1 persistence, tools, deterministic policy validation, human approval and a React console. It did not prove real provider quality, independent retrieval quality, custom model training or production compliance. The separate Python/MCP source must not be described as the hosted runtime.

## Largest gaps and coverage leverage

The remaining major gap is real LLM generation and embeddings with independent Live evaluation; configuration is blocked by unavailable approved key setup. A trained model plus artifact inference covers lifecycle, Python, APIs, evaluation and reliability across the three roles. An independent retrieval benchmark covers UBS/Affinda and prevents misleading retrieval claims. Persisted timings/failures cover all three without replacing the product with infrastructure work. Recruiter-facing evidence and reproducible handover connect those features to a project that can be explained in detail.

P0 must not be declared complete while real provider calls and semantic quality remain unverified. Docker, connected production MCP client, durable queues, GitHub CI execution, operator-wide monitoring and production auth are also not completed by adding source configuration alone.

## Local semantic retrieval update

Open-source English static embeddings now run in the hosted Worker without provider credentials. The frozen 24-query comparison has keyword Recall@3 0.9375 / MRR@6 0.770833 and local semantic Recall@3 0.958333 / MRR@6 0.90625. See verification/semantic.json for all results. Real generative LLM execution remains a separate unverified gap. No expected-source injection is used in this retrieval measurement.

## v8 capability evidence and remaining gaps

| Requirement | Project evidence | Status |
|---|---|---|
| Agentic workflow | Typed LangGraph state, bounded repair, tool/evidence checks, human gate | Implemented; default planner is deterministic; real LLM execution pending |
| RAG / embeddings | Local 128-dimensional static model, chunk IDs/sections, cosine ranking, 24-query independent benchmark | Implemented for English; small corpus; no deployed pgvector |
| MCP | Eight read-only hosted tools; linked record access checks; official SDK HTTP tests | Implemented; external production client connection separate |
| Python | FastAPI inference service, sklearn training, pytest | Implemented locally; Python service not hosted |
| APIs / database | Worker API and D1, customer/transaction/account queries, session isolation | Implemented; synthetic enterprise records, not connected bank APIs |
| Custom ML | Real CFPB response-delay model and separately labelled synthetic escalation forest | Saved artifacts and real inference; synthetic metrics not real-world risk evidence |
| Evaluation | 30 financial complaint cases, 30 legacy refund cases, independent retrieval and held-out model reports | Implemented; no real-provider evaluation |
| Human review / governance | Evidence revisions, original/edited answer separation, atomic review, audit timestamps | Implemented; no regulatory certification |
| Model lifecycle | Data hashes, parity, quality gate, local package rollback exercise | Implemented locally; no production model rollback test |
| Docker | Non-root backend image recipe, health check and GitHub build/run job | Not executed: current runtime lacks Docker and usable user namespaces |
| GitHub CI | Fail-fast workflow with lint, typecheck, tests, build, models and container job | Not executed: no OpsPilot repository found in connected Violet79-hub account |
| Deployment | Existing Site, Worker and durable D1 bindings | Published via Sites, not via GitHub CI |
| Cost / monitoring | Node and total latency, recorded tokens, zero provider calls in local mode | Hosting cost and real-provider cost unmeasured |
| Browser QA | Populated initial HTML and compiled Worker flow tests | Interactive browser validation unavailable in this environment |
| Kubernetes / advanced auth | None | Not implemented; lower priority than live-provider and release verification |

UBS / Affinda remain the primary fit through workflow, retrieval, tools and evaluation. Enexis evidence is partial: Docker and CI execution need completing before claiming verified MLOps delivery. Stronger real-world escalation data is more valuable than inflating synthetic performance; Kubernetes would not close the central gaps.
