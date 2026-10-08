from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func
from app.schemas import RunRequest, ReviewRequest, Plan
from app.agent.runner import create_run, execute_run
from app.agent.planning import demo_plan, validate_plan
from app.db.repository import Session, get_run
from app.db.models import SupportAction, HumanReview
from app.rag.retriever import search_knowledge
from app.rag.ingestion import ingest, extract
from app.tools.business import get_customer, get_order, calculate_refund
from app.tools.registry import invoke
from app.services.review import review_run
from app.evaluation.harness import GOLDEN
from app.evaluation.metrics import score_case, aggregate
from app.evaluation.evaluator import evaluate_answer


def run_task(task, **kwargs):
    rid = create_run(RunRequest(task=task, **kwargs))
    execute_run(rid)
    return get_run(rid)


@pytest.mark.parametrize("case", GOLDEN, ids=lambda c: c["id"])
def test_golden_cases(case):
    run = run_task(case["task"], top_k=8)
    score = score_case(case, run)
    assert score["passed"], score
    assert run["state"]["attempts"] <= 2
    assert len(run["events"]) > 3
    if case["expected_decision"] == "insufficient_evidence":
        assert run["status"] == "blocked"
    else:
        assert run["state"]["evaluation"]["passed"]


def test_retrieval_is_query_dependent():
    privacy = search_knowledge("privacy personal data identity disclosure", 3)
    warranty = search_knowledge("hardware defects warranty replacement", 3)
    assert privacy[0]["document_id"] == "privacy"
    assert warranty[0]["document_id"] == "warranty"
    assert privacy[0]["chunk_id"] != warranty[0]["chunk_id"]
    assert privacy[0]["score"] > 0


def test_upload_and_retrieve_untrusted_content():
    result = ingest(
        "unique.md",
        b"# Internal research\n\n## Zephyr protocol\nThe zephyr turbine uses a zirconium lattice for thermal regulation.",
    )
    matches = search_knowledge("zephyr zirconium lattice", 3)
    assert matches[0]["document_id"] == result["id"]
    assert not matches[0]["trusted"]


def test_extraction_rejects_empty_unknown_and_large():
    for name, data in [
        ("empty.txt", b""),
        ("x.exe", b"x" * 40),
        ("large.txt", b"x" * (5 * 1024 * 1024 + 1)),
    ]:
        with pytest.raises(ValueError):
            extract(name, data)


def test_refund_uses_decimal_rounding_and_database():
    assert calculate_refund("NS-1044")["amount"] == 85
    assert get_order("NS-1042")["customer_id"] == "C001"
    assert "email" not in get_customer("C001")
    assert get_order("NS-9999") is None


def test_schema_rejects_unbounded_requests_and_unknown_tools():
    with pytest.raises(ValidationError):
        RunRequest(task="x", top_k=200)
    with pytest.raises(ValidationError):
        Plan(
            task_type="refund",
            query="refund",
            steps=[{"action": "delete_customer", "reason": "no"}],
        )
    with pytest.raises(ValidationError):
        invoke("get_order", {"order_id": "'; DROP TABLE orders;--"})


def test_live_planner_cannot_invent_ids_or_bypass_privacy():
    task = "Refund for order NS-1042"
    plan = demo_plan(task).model_copy(update={"order_id": "NS-1043"})
    with pytest.raises(ValueError):
        validate_plan(plan, task)
    plan = demo_plan("Export C001 email").model_copy(update={"task_type": "refund"})
    with pytest.raises(ValueError):
        validate_plan(plan, "Export C001 email")


def test_forged_citation_and_amount_block_approval():
    state = run_task("Review refund for order NS-1042.", top_k=8)["state"]
    changed = deepcopy(state)
    changed["draft_answer"]["citations"][0]["chunk_id"] = "fake:999"
    assert not evaluate_answer(changed).passed
    changed = deepcopy(state)
    changed["draft_answer"]["amount"] = 100000
    changed["threshold"] = 0.5
    assert not evaluate_answer(changed).passed


def test_missing_policy_triggers_bounded_retry_and_blocks():
    run = run_task("Review refund for order NS-1051.", top_k=1)
    assert run["state"]["attempts"] == 2
    assert run["status"] == "blocked"
    with pytest.raises(HTTPException) as e:
        review_run(run["id"], ReviewRequest(decision="approve", expected_revision=0))
    assert e.value.status_code == 409


def test_edit_requires_later_approval_and_preserves_amount():
    run = run_task("Review refund for order NS-1043.", top_k=8)
    rid = run["id"]
    review_run(
        rid,
        ReviewRequest(
            decision="edit",
            edited_answer="Confirm return logistics with customer.",
            expected_revision=0,
        ),
    )
    with Session() as s:
        assert (
            s.scalar(select(func.count(SupportAction.id)).where(SupportAction.run_id == rid)) == 0
        )
    edited = get_run(rid)
    assert edited["state"]["draft_answer"]["amount"] == 100
    assert edited["status"] == "pending_review"
    review_run(rid, ReviewRequest(decision="approve", expected_revision=1))
    with Session() as s:
        action = s.scalar(select(SupportAction).where(SupportAction.run_id == rid))
        assert action.action["payment_executed"] is False
        assert s.scalar(select(func.count(HumanReview.id)).where(HumanReview.run_id == rid)) == 2


def test_duplicate_concurrent_approval_creates_one_action():
    rid = run_task("Review refund for order NS-1043.", top_k=8)["id"]

    def submit(_):
        try:
            review_run(rid, ReviewRequest(decision="approve", expected_revision=0))
            return 200
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(submit, [1, 2]))
    assert sorted(statuses) == [200, 409]
    with Session() as s:
        assert (
            s.scalar(select(func.count(SupportAction.id)).where(SupportAction.run_id == rid)) == 1
        )


def test_rejection_cannot_create_action():
    rid = run_task("Review refund for order NS-1043.", top_k=8)["id"]
    review_run(rid, ReviewRequest(decision="reject", expected_revision=0))
    assert get_run(rid)["status"] == "rejected"
    with Session() as s:
        assert not s.scalar(select(SupportAction).where(SupportAction.run_id == rid))


def test_metrics_do_not_hide_failure_and_exclude_na():
    result = {
        "retrieval_hit": True,
        "retrieval_recall": 1.0,
        "tool_accuracy": 1.0,
        "decision_accuracy": 0.0,
        "citation_accuracy": None,
        "passed": False,
        "latency_ms": 20.0,
        "tokens": 0,
        "cost": 0,
    }
    metrics = aggregate([result])
    assert metrics["answer_pass_rate"] == 0
    assert metrics["citation_accuracy"] is None
    assert metrics["avg_latency_ms"] == 20


def test_provider_contract_and_usage_accounting(monkeypatch):
    from types import SimpleNamespace
    from app.services import llm
    from app.schemas import Plan

    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    expected = demo_plan("Review refund for order NS-1042.")
    calls = []

    def parse(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=expected))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=25, total_tokens=125),
        )

    monkeypatch.setattr(
        llm,
        "OpenAI",
        lambda **_: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=parse))),
    )
    result, usage = llm.OpenAIProvider().structured_generate("system instruction", "task", Plan)
    assert result.order_id == "NS-1042"
    assert calls[0]["response_format"] is Plan
    assert usage["total_tokens"] == 125
    assert llm.cost(usage, "live") is None
    monkeypatch.setenv("INPUT_USD_PER_MILLION", "1")
    monkeypatch.setenv("OUTPUT_USD_PER_MILLION", "4")
    assert llm.cost(usage, "live") == pytest.approx(0.0002)
