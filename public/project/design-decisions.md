# Design decisions

Financial complaints expose evidence conflict and review consequences while allowing safe synthetic business data. Human review remains mandatory, including for a positive refund recommendation. Writes create internal actions only.

LangGraph provides typed state, explicit nodes and one bounded repair branch. Default execution uses deterministic planning; a graph alone does not establish autonomous LLM behaviour. RAG separates retrieved evidence from generated wording. Local static embeddings avoid provider setup while preserving actual vector inference; the small corpus does not justify a vector database. D1 is the deployed relational store; pgvector/PostgreSQL would be a future scale decision, not a label to add now.

The real-data delay experiment selected Logistic Regression using validation evidence. The synthetic escalation experiment selected Random Forest over a Logistic Regression baseline; LightGBM/XGBoost were not used because a reproducible portable forest already meets the small experiment's purpose. Synthetic escalation labels are not evidence of real predictive validity. The LLM is not the sole decision mechanism: authoritative policy, linked records, model abstention and human controls remain independent.

Evaluation separates retrieval ranking, expected tool coverage, deterministic decisions and ML held-out metrics. Synthetic complaints make the public demonstration usable without personal data. Tests deliberately include missing evidence, attacks and unknown records. One repair avoids unbounded execution and cost. No claimed confidence is derived merely from the fraction of checks passed.
