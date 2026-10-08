import asyncio
from pathlib import Path
from app.ml import ComplaintFeatures, predict_response_delay
import json
import logging
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, text
from app.config import AS_OF, MAX_UPLOAD
from app.db.repository import init_db, Session, get_run, row_dict, engine
from app.db.seed import seed
from app.db.models import AgentRun, Document, Chunk, EvalBatch, HumanReview, SupportAction
from app.schemas import RunRequest, ReviewRequest
from app.agent.runner import create_run, execute_run
from app.evaluation.harness import GOLDEN, create_batch, execute_batch
from app.services.review import review_run
from app.tools.registry import schemas
from app.rag.ingestion import ingest
from app.rag.retriever import search_knowledge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
pool = ThreadPoolExecutor(max_workers=4)
slots = BoundedSemaphore(4)


@asynccontextmanager
async def lifespan(app):
    init_db()
    seed()
    # This release has a single-process worker. Preserve evidence and mark interrupted jobs honestly.
    with Session.begin() as s:
        for run in s.scalars(select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))):
            run.status = "failed"
            run.state = {**run.state, "error": "Server restarted during execution; submit again."}
        for batch in s.scalars(
            select(EvalBatch).where(EvalBatch.status.in_(["queued", "running"]))
        ):
            batch.status = "failed"
    yield
    pool.shutdown(wait=True)


app = FastAPI(title="OpsPilot API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


def admin(authorization: str | None = Header(default=None)):
    token = os.getenv("OPSPILOT_ADMIN_TOKEN")
    if (
        not token
        or not authorization
        or not secrets.compare_digest(authorization, "Bearer " + token)
    ):
        raise HTTPException(403, "Configure an admin token and provide it in Settings")


def demo_write(authorization: str | None = Header(default=None)):
    if os.getenv("DEMO_WRITES", "true").lower() != "true":
        admin(authorization)


def submit(fn, identifier):
    def work():
        try:
            fn(identifier)
        finally:
            slots.release()

    pool.submit(work)


@app.get("/health")
def health():
    with Session() as s:
        s.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": engine.dialect.name,
        "vector_store": "pgvector"
        if engine.dialect.name == "postgresql"
        else "SQLite + NumPy cosine",
        "embedding_model": "hashing-512-v1 (lexical)",
        "live_available": bool(os.getenv("OPENAI_API_KEY")),
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "synthetic_as_of": AS_OF,
        "mcp": "standalone stdio module; not connected to this graph",
        "demo_writes": os.getenv("DEMO_WRITES", "true").lower() == "true",
    }


@app.post("/api/runs", status_code=202, dependencies=[Depends(demo_write)])
def start_run(request: RunRequest, authorization: str | None = Header(default=None)):
    if request.mode == "live":
        admin(authorization)
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(503, "Live mode is not configured")
    if not slots.acquire(blocking=False):
        raise HTTPException(429, "All four execution slots are busy. Try again shortly.")
    try:
        rid = create_run(request)
        submit(execute_run, rid)
    except Exception:
        slots.release()
        raise
    return {"id": rid, "status": "queued"}


@app.get("/api/runs")
def runs():
    with Session() as s:
        return [
            row_dict(r)
            for r in s.scalars(
                select(AgentRun)
                .where(AgentRun.purpose == "interactive")
                .order_by(AgentRun.created_at.desc())
                .limit(100)
            )
        ]


@app.get("/api/runs/{rid}")
def run_detail(rid: str):
    result = get_run(rid)
    if not result:
        raise HTTPException(404, "Run not found")
    with Session() as s:
        result["reviews"] = [
            row_dict(r)
            for r in s.scalars(
                select(HumanReview)
                .where(HumanReview.run_id == rid)
                .order_by(HumanReview.reviewed_at)
            )
        ]
        result["actions"] = [
            row_dict(r) for r in s.scalars(select(SupportAction).where(SupportAction.run_id == rid))
        ]
    return result


@app.get("/api/runs/{rid}/events")
async def stream_events(rid: str):
    if not get_run(rid):
        raise HTTPException(404, "Run not found")

    async def generate():
        last = 0
        for _ in range(600):
            run = get_run(rid)
            for event in run["events"]:
                if event["id"] > last:
                    yield "event: trace\ndata: " + json.dumps(event) + "\n\n"
                    last = event["id"]
            if run["status"] not in {"queued", "running"}:
                yield "event: complete\ndata: " + json.dumps({"status": run["status"]}) + "\n\n"
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/runs/{rid}/review", dependencies=[Depends(demo_write)])
def review(rid: str, request: ReviewRequest, authorization: str | None = Header(default=None)):
    run = get_run(rid)
    if run and run["mode"] == "live":
        admin(authorization)
    return review_run(rid, request)


@app.get("/api/dashboard")
def dashboard():
    with Session() as s:
        rows = list(s.scalars(select(AgentRun).where(AgentRun.purpose == "interactive")))
        completed = [r for r in rows if r.status not in {"queued", "running"}]
        evaluated = [r for r in completed if "evaluation" in r.state]
        costs = [r.estimated_cost for r in completed if r.estimated_cost is not None]
        return {
            "total_runs": len(rows),
            "pending": sum(r.status == "pending_review" for r in rows),
            "approval_rate": sum(r.status == "approved" for r in completed) / len(completed)
            if completed
            else None,
            "evaluation_pass_rate": sum(r.state["evaluation"]["passed"] for r in evaluated)
            / len(evaluated)
            if evaluated
            else None,
            "average_latency_ms": sum(r.latency for r in completed) / len(completed)
            if completed
            else None,
            "average_cost": sum(costs) / len(costs) if costs else None,
            "total_cost": sum(costs),
            "cost_known_runs": len(costs),
            "total_tokens": sum(r.token_usage.get("total_tokens", 0) or 0 for r in rows),
            "documents": s.scalar(select(func.count(Document.id))),
            "chunks": s.scalar(select(func.count(Chunk.id))),
        }


@app.get("/api/documents")
def documents():
    with Session() as s:
        return [
            {
                **row_dict(d),
                "chunks": s.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == d.id)),
                "embedding_status": "indexed",
            }
            for d in s.scalars(select(Document).order_by(Document.name))
        ]


@app.get("/api/documents/{did}")
def document(did: str):
    with Session() as s:
        if not s.get(Document, did):
            raise HTTPException(404, "Document not found")
        return [
            {k: v for k, v in row_dict(c).items() if k != "embedding"}
            for c in s.scalars(select(Chunk).where(Chunk.document_id == did))
        ]


@app.post("/api/documents", dependencies=[Depends(admin)])
async def upload(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD + 1)
    try:
        return ingest(file.filename or "upload.txt", data)
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise HTTPException(422, str(exc)) from exc
        raise HTTPException(422, "Document could not be extracted") from exc


@app.get("/api/search")
def search(q: str, top_k: int = 6):
    if not q.strip() or len(q) > 2000 or not 1 <= top_k <= 12:
        raise HTTPException(422, "Query or top_k is invalid")
    return search_knowledge(q, top_k)


@app.get("/api/tools")
def tools():
    return schemas()


@app.get("/api/evaluations/dataset")
def dataset():
    return GOLDEN


@app.post("/api/evaluations", status_code=202, dependencies=[Depends(demo_write)])
def start_eval():
    if not slots.acquire(blocking=False):
        raise HTTPException(429, "Execution slots busy")
    try:
        bid = create_batch()
        submit(execute_batch, bid)
    except Exception:
        slots.release()
        raise
    return {"id": bid}


@app.get("/api/evaluations")
def batches():
    with Session() as s:
        return [
            row_dict(b)
            for b in s.scalars(select(EvalBatch).order_by(EvalBatch.created_at.desc()).limit(10))
        ]


@app.get("/api/evaluations/{bid}")
def batch(bid: str):
    with Session() as s:
        b = s.get(EvalBatch, bid)
        if not b:
            raise HTTPException(404, "Evaluation not found")
        return row_dict(b)

# Trained ML artifact is loaded server-side; outcomes never enter inference inputs.

@app.get('/ml/evaluation')
def ml_evaluation():
    return json.loads((Path(__file__).resolve().parents[2] / 'ml/artifacts/evaluation.json').read_text())

@app.post('/ml/predict', dependencies=[Depends(demo_write)])
def ml_predict(features: ComplaintFeatures):
    return predict_response_delay(features.model_dump())

from app.escalation import EscalationFeatures, score_escalation
@app.post('/ml/escalation/predict', dependencies=[Depends(demo_write)])
def escalation_predict(features: EscalationFeatures):
    return score_escalation(features.model_dump())
@app.get('/ml/escalation/evaluation')
def escalation_evaluation():
    return json.loads((Path(__file__).resolve().parents[2] / 'ml/escalation/evaluation.json').read_text())
