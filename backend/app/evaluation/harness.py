import json
import logging
from app.config import DATA
from app.schemas import RunRequest
from app.agent.runner import create_run, execute_run
from app.db.models import EvalBatch
from app.db.repository import Session, get_run, new_id
from app.evaluation.metrics import score_case, aggregate

GOLDEN = json.loads((DATA / "golden.json").read_text())


def create_batch():
    bid = new_id()
    with Session.begin() as s:
        s.add(EvalBatch(id=bid, status="queued"))
    return bid


def execute_batch(bid):
    results = []
    try:
        with Session.begin() as s:
            s.get(EvalBatch, bid).status = "running"
        for case in GOLDEN:
            rid = create_run(RunRequest(task=case["task"], top_k=8), purpose="evaluation")
            execute_run(rid)
            results.append(score_case(case, get_run(rid)))
            with Session.begin() as s:
                batch = s.get(EvalBatch, bid)
                batch.results = list(results)
                batch.metrics = aggregate(results)
        with Session.begin() as s:
            s.get(EvalBatch, bid).status = "completed"
    except Exception:
        logging.getLogger("opspilot").exception("evaluation_batch_failed id=%s", bid)
        with Session.begin() as s:
            s.get(EvalBatch, bid).status = "failed"
