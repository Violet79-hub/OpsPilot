"""Metrics compare independently authored fixtures with actual recorded outputs."""

from statistics import mean


def score_case(case, run):
    state = run.get("state", {})
    answer = state.get("draft_answer", {})
    expected_sources = set(case["expected_sources"])
    retrieved = {
        r["document_id"]
        for r in state.get("retrieved_documents", [])
        if r["section"] not in {"Overview", "Scope and recordkeeping"}
    }
    retrieved_chunks = {r["chunk_id"]: r for r in state.get("retrieved_documents", [])}
    tools = {c["name"] for c in state.get("tool_calls", [])}
    if state.get("retrieved_documents"):
        tools.add("search_knowledge")
    citations = answer.get("citations", [])
    valid = sum(
        1
        for c in citations
        if c["chunk_id"] in retrieved_chunks
        and c["document_name"] == retrieved_chunks[c["chunk_id"]]["document_name"]
        and c["section"] == retrieved_chunks[c["chunk_id"]]["section"]
    )
    amount = answer.get("amount", -1)
    decision = answer.get("decision") == case["expected_decision"]
    amount_ok = case["expected_refund_range"][0] <= amount <= case["expected_refund_range"][1]
    tool_accuracy = tools == set(case["expected_tools"])
    recall = len(expected_sources & retrieved) / len(expected_sources) if expected_sources else None
    citation_accuracy = (
        valid / len(citations)
        if citations
        else (None if case["expected_decision"] == "insufficient_evidence" else 0)
    )
    passed = (
        decision
        and amount_ok
        and tool_accuracy
        and (recall is None or recall == 1)
        and (citation_accuracy is None or citation_accuracy == 1)
    )
    return {
        "id": case["id"],
        "task": case["task"],
        "run_id": run["id"],
        "expected_decision": case["expected_decision"],
        "actual_decision": answer.get("decision", "error"),
        "amount": amount,
        "retrieval_hit": bool(expected_sources & retrieved) if expected_sources else None,
        "retrieval_recall": recall,
        "tool_accuracy": int(tool_accuracy),
        "decision_accuracy": int(decision),
        "citation_accuracy": citation_accuracy,
        "amount_correct": amount_ok,
        "passed": passed,
        "latency_ms": run["latency"],
        "tokens": run.get("token_usage", {}).get("total_tokens"),
        "cost": run.get("estimated_cost"),
    }


def aggregate(results):
    def avg(key):
        values = [float(r[key]) for r in results if r.get(key) is not None]
        return mean(values) if values else None

    return {
        "cases": len(results),
        "passed": sum(r["passed"] for r in results),
        "retrieval_hit_rate": avg("retrieval_hit"),
        "retrieval_recall": avg("retrieval_recall"),
        "tool_accuracy": avg("tool_accuracy"),
        "decision_accuracy": avg("decision_accuracy"),
        "citation_accuracy": avg("citation_accuracy"),
        "answer_pass_rate": avg("passed"),
        "avg_latency_ms": avg("latency_ms"),
        "avg_tokens": avg("tokens"),
        "avg_cost": avg("cost"),
    }
