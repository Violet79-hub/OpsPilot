# Runbook and handover

## Runtime and secrets

Deploy the existing Site project; never create a replacement. D1 migrations are in `drizzle`. Seed records are synthetic; model complaint replays are sanitised public historical records. Runtime configuration: OPENAI_API_KEY (secret), optional OPENAI_MODEL. Never place a key in frontend code, the archive, logs or a committed env file.

Run `/api/health` to inspect real runtime/database/model readiness. Missing model configuration returns 503 for Live runs and semantic evaluations. Rules, ML and baseline evaluation remain executable. Do not treat configured=true as proof the key works; execute provider probes and Live golden/retrieval evaluation before claiming integration success.

## Failures and operational limits

Runs persist in D1. Execute/review require the same anonymous session cookie, and cross-origin mutations are refused. Interrupted running states are marked failed after the timeout; resubmit deliberately rather than blindly retrying a financial action. Review CAS prevents duplicates. Session loss means its runs are inaccessible, not deleted. Public demo limits writes and evaluation counts; authenticated tenancy and retention are prerequisites for real deployment.

Monitoring is session-scoped. Inspect failed nodes and errors. The dashboard measures per-node and total latency; no configured provider pricing means no estimated dollars. Production work includes central alerts, idempotent queue delivery, audited RBAC, deletion/retention and cost budgets.

## Python packaging

`docker build -f backend/Dockerfile -t opspilot .` packages the Python service and the exported model. Run with a persistent `/app/storage` volume and explicit `DEMO_WRITES=true` only for a local demonstration. Container execution is not verified in the current environment because Docker is unavailable. Python service endpoints `/ml/predict` and `/ml/evaluation` are tested locally; the production Site exposes `/api/ml/predict` and `/api/ml/evaluation`.

## Releasing and rollback

Typecheck, D1 regression, Python tests, model parity, build and compiled Worker checks precede source push/version save/deployment. Do not include node_modules, credentials or local databases in source downloads. Keep a prior saved version for rollback via the same Site. Re-run the checks after changes; CI file creation alone is not evidence that GitHub CI ran.
