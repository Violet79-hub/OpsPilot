import logging
from time import perf_counter
from app.db.models import AgentRun, Evaluation, now
from app.db.repository import Session, add_event, new_id
from app.agent.graph import graph
from app.services.llm import cost

logger = logging.getLogger("opspilot")


def create_run(request, purpose="interactive"):
    rid = new_id()
    with Session.begin() as s:
        s.add(
            AgentRun(
                id=rid,
                task=request.task,
                mode=request.mode,
                purpose=purpose,
                state={"top_k": request.top_k, "threshold": request.threshold},
            )
        )
    return rid


def execute_run(rid):
    start = perf_counter()
    with Session.begin() as s:
        run = s.get(AgentRun, rid)
        run.status = "running"
        state = {"run_id": rid, "task": run.task, "mode": run.mode, **run.state}
    try:
        result = graph.invoke(state, {"recursion_limit": 24})
        elapsed = (perf_counter() - start) * 1000
        with Session.begin() as s:
            run = s.get(AgentRun, rid)
            run.state = dict(result)
            run.status = "pending_review" if result["approval_status"] == "pending" else "blocked"
            run.latency = elapsed
            run.token_usage = result["token_usage"]
            run.estimated_cost = cost(run.token_usage, run.mode)
            run.completed_at = now()
            s.add(Evaluation(id=new_id(), run_id=rid, result=result["evaluation"]))
        logger.info(
            "run_completed id=%s status=%s latency_ms=%.3f", rid, result["approval_status"], elapsed
        )
    except Exception as exc:
        logger.exception("run_failed id=%s", rid)
        # Do not expose provider responses, credentials or exception payloads through the API.
        error = f"{type(exc).__name__}: execution failed; inspect server logs."
        add_event(rid, "error", {}, {"error": error}, event_type="failed")
        with Session.begin() as s:
            run = s.get(AgentRun, rid)
            run.status = "failed"
            run.state = {**state, "error": error}
            run.latency = (perf_counter() - start) * 1000
            run.completed_at = now()
