"""Run against an isolated PostgreSQL database after setting DATABASE_URL."""

import json
from sqlalchemy import text
from app.db.repository import init_db, engine, get_run
from app.db.seed import seed
from app.rag.retriever import search_knowledge
from app.agent.runner import create_run, execute_run
from app.schemas import RunRequest

assert engine.dialect.name == "postgresql", "Set DATABASE_URL to PostgreSQL"
init_db()
seed()
with engine.connect() as conn:
    version = conn.execute(
        text("SELECT extversion FROM pg_extension WHERE extname='vector'")
    ).scalar()
    assert version
results = search_knowledge("Gold customer return extension", 3)
assert results[0]["document_id"] == "vip"
rid = create_run(RunRequest(task="Review refund for order NS-1042.", top_k=8))
execute_run(rid)
run = get_run(rid)
assert run["status"] == "pending_review", run["state"]
assert run["state"]["draft_answer"]["amount"] == 899
print(
    json.dumps(
        {
            "database": "postgresql",
            "pgvector_version": version,
            "retrieval": "passed",
            "agent": "passed",
            "run_id": rid,
        },
        indent=2,
    )
)
