# OpsPilot: evidence-driven operations review

OpsPilot extends the existing React operations console and persisted LangGraph/D1 workflow. A request becomes a structured plan, independent policy retrieval, allowlisted database lookups, an optional trained risk-model call, an answer, validation and human review. Approval records an internal action. It never transfers money or sends customer messages.

## Implementation boundaries

The public Site hosts TypeScript LangGraph and D1. Rules mode is an executable deterministic baseline; it is not a language model. Live mode contains provider structured generation and embedding retrieval, but refuses execution without a server API key. Real provider quality has not been verified. Provider contract tests use an explicit mock and do not measure model quality.

The repository also includes Python/FastAPI, SQLAlchemy, local task execution and a real stdio MCP server. These are reproducible local components, not a hosted Python service. Python model inference and hosted inference use the same trained JSON artifact. Python also contains the original operations backend rather than a replacement frontend.

## Model decision

Predict historical financial-complaint response delay (`timely=No`) using CFPB public data. This is a measurable outcome with a plausible manual follow-up use case. It is not an invented escalation label, fraud label or refund eligibility label. Retail orders are outside the training domain. A complaint replay uses only pre-response public categories; the Agent actually calls `predict_response_delay` and logs its score. The score influences suggested reviewer priority in the explanation, never the approve/escalate policy.

20,000 historical convenience-sampled records: 12,000 train, 4,000 validation, 4,000 later temporal test. One-hot categories fit only on train. Compare a prior baseline, three Logistic Regression settings and a shallow Random Forest. Select by validation average precision; select the threshold on validation F1. The final model is Logistic Regression C=10. Test ROC-AUC 0.881, average precision 0.141, precision 0.0968, recall 0.711, F1 0.170. There are 597 false positives and 26 false negatives; the low precision rules out automated prioritisation. The historical data and sampling rule rule out claiming current production calibration.

A recent-data pilot had just 66 positive examples in 16,000 rows and was rejected. An exploratory v1 report is retained. After inspecting v1, add a company category known before response and reserve the previously unused 2017 window as final test. No response, resolution, narrative, customer identity, or test-derived categories enter the features. The company category is a hash of a public company name, not anonymisation of personal data.

## Evaluation

30 synthetic golden operations cases check decision, amount, required citations, expected tools and guardrails. A separate 24-query labelled corpus benchmark measures Hit@3, Recall@3, Precision@3 and MRR over the returned ranking before mandatory policy completion. MRR uses the full returned list, up to six results. Keyword results are baseline results; semantic results must be generated with a real provider key. Retrieval labels are manually authored and small; add business-user labels and held-out paraphrases before production acceptance.

Model evaluation uses the temporal held-out outcome set. The artifact verifier reproduces held-out metrics without refitting and checks 50 raw scikit-learn predictions against exported coefficients at tolerance 1e-12. Both inference APIs also test supported-vector parity and abstention on unsupported vectors. Out-of-domain requests abstain and injected outcome fields are rejected. Run timing, token counts, errors, evidence blocks and reviewer actions are persisted; provider prices are not configured, so the dashboard reports cost as unmeasured rather than inventing dollar values.

## Reliability choices

LangGraph makes node boundaries, conditional repair, state and audit events explicit. A model may propose a plan but cannot invent identifiers, invent tools, bypass deterministic policy or execute money movement. Private uploads remain untrusted reference material. The trusted policy corpus supplies authoritative checks. Missing records, missing citations or failed checks block approval. Review uses a revision compare-and-swap and a transactional action insert to prevent duplicate approvals.

Before production: configure and evaluate real provider calls; label representative retrieval queries; test tenancy with authenticated users; add calibrated current-domain ML data, security review, retention controls, queue durability, bounded retries and operational alerts. The existing demo supports no claim of regulatory certification.
