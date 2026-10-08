from app.schemas import EvaluationResult, AgentAnswer


def evaluate_answer(state):
    answer = AgentAnswer.model_validate(state["draft_answer"])
    retrieved = {r["chunk_id"]: r for r in state["retrieved_documents"]}
    cited = [retrieved.get(c.chunk_id) for c in answer.citations]
    valid_citations = bool(cited) and all(
        r and r["trusted"] and c.document_name == r["document_name"] and c.section == r["section"]
        for c, r in zip(answer.citations, cited)
    )
    present = {
        r["document_id"]
        for r in cited
        if r and r["trusted"] and r["section"] not in {"Overview", "Scope and recordkeeping"}
    }
    expected = state["policy_result"]
    called = {c["name"] for c in state["tool_calls"]} | {"search_knowledge"}
    selected = {s["action"] for s in state["plan"]["steps"]}
    requires_order = answer.decision in {"approve", "deny", "warranty"}
    mandatory = {"get_order", "get_customer", "calculate_refund"} if requires_order else set()
    checks = {
        "citation_membership": bool(valid_citations),
        "policy_coverage": set(expected["required_sources"]).issubset(present),
        "tool_coverage": (selected | mandatory).issubset(called),
        "decision_consistency": answer.decision == expected["decision"],
        "amount_consistency": abs(answer.amount - expected["amount"]) < 0.005,
        "record_integrity": not requires_order
        or bool(state.get("order_data") and state.get("customer_data")),
        "evidence_sufficient": answer.decision != "insufficient_evidence"
        and answer.evidence_status != "insufficient",
    }
    score = sum(checks.values()) / len(checks)
    # Safety-critical failures are never overridden by a lower threshold.
    passed = all(checks.values()) and score >= state["threshold"]
    return EvaluationResult(
        passed=passed, score=score, issues=[k for k, v in checks.items() if not v], checks=checks
    )
