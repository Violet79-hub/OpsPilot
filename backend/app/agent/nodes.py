import json
from time import perf_counter
from app.schemas import Plan, AgentAnswer, Citation
from app.agent.planning import demo_plan, validate_plan, QUERIES
from app.services.llm import OpenAIProvider, PROMPTS
from app.tools.registry import invoke
from app.db.repository import add_event
from app.evaluation.evaluator import evaluate_answer


def usage_add(a, b):
    if not b:
        return a
    if a.get("source") == "unavailable" or b.get("source") == "unavailable":
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "source": "unavailable",
        }
    return {
        k: (a.get(k, 0) or 0) + (b.get(k, 0) or 0)
        for k in ["prompt_tokens", "completion_tokens", "total_tokens"]
    } | {"source": b["source"]}


def planner(state):
    start = perf_counter()
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "source": "no_llm"}
    if state["mode"] == "live":
        plan, usage = OpenAIProvider().structured_generate(
            (PROMPTS / "planner.txt").read_text(), state["task"], Plan
        )
        validate_plan(plan, state["task"])
    else:
        plan = demo_plan(state["task"])
    add_event(
        state["run_id"],
        "planner",
        {"task": state["task"]},
        {"plan": plan.model_dump(), "mode": state["mode"]},
        (perf_counter() - start) * 1000,
    )
    return {"plan": plan.model_dump(), "token_usage": usage, "attempts": 0}


def retrieval(state):
    start = perf_counter()
    plan = Plan.model_validate(state["plan"])
    queries = QUERIES[plan.task_type] or [plan.query]
    # Multi-query retrieval uses real vector scores; no source IDs are injected.
    found = {}
    primary = []
    for query in queries:
        results = invoke("search_knowledge", {"query": query, "top_k": 2})
        if results:
            primary.append(results[0])
        for r in results:
            if r["chunk_id"] not in found or found[r["chunk_id"]]["score"] < r["score"]:
                found[r["chunk_id"]] = r
    unique = {}
    for r in primary + sorted(found.values(), key=lambda r: r["score"], reverse=True):
        unique.setdefault(r["chunk_id"], r)
    limit = min(12, state["top_k"] + (4 if state.get("attempts", 0) else 0))
    results = list(unique.values())[:limit]
    add_event(
        state["run_id"],
        "retrieval",
        {"queries": queries, "top_k": limit},
        {"chunks": results},
        (perf_counter() - start) * 1000,
        tool="search_knowledge",
    )
    return {"retrieved_documents": results}


def tool_node(state):
    plan = Plan.model_validate(state["plan"])
    calls = []
    data = {"order_data": None, "customer_data": None, "ticket_data": None}
    oid, cid = plan.order_id, plan.customer_id
    selected = {s.action for s in plan.steps}

    def call(name, args):
        start = perf_counter()
        result = invoke(name, args)
        calls.append({"name": name, "arguments": args, "result": result})
        add_event(
            state["run_id"],
            "tools",
            args,
            {"result": result},
            (perf_counter() - start) * 1000,
            tool=name,
        )
        return result

    if "get_support_ticket" in selected and plan.ticket_id:
        ticket = call("get_support_ticket", {"ticket_id": plan.ticket_id})
        data["ticket_data"] = ticket
        if ticket:
            if (oid and oid != ticket["order_id"]) or (cid and cid != ticket["customer_id"]):
                data["policy_result"] = missing("IDENTIFIER_MISMATCH")
                return data | {"tool_calls": calls}
            oid, cid = ticket["order_id"], ticket["customer_id"]
    if "get_order" in selected and oid:
        data["order_data"] = call("get_order", {"order_id": oid})
        if data["order_data"]:
            linked = data["order_data"]["customer_id"]
            if cid and cid != linked:
                data["policy_result"] = missing("CUSTOMER_ORDER_MISMATCH")
                return data | {"tool_calls": calls}
            cid = linked
    if "get_customer" in selected and cid:
        data["customer_data"] = call("get_customer", {"customer_id": cid})
    if "calculate_refund" in selected and oid and data["order_data"] and data["customer_data"]:
        data["policy_result"] = call("calculate_refund", {"order_id": oid})
    elif plan.task_type == "privacy":
        data["policy_result"] = {
            "decision": "escalate",
            "amount": 0,
            "required_sources": ["privacy"],
            "reason_codes": ["PRIVACY_REVIEW"],
        }
    elif plan.task_type == "policy" or (
        plan.task_type in {"shipping", "refund", "warranty", "cancellation"}
        and not any([oid, cid, plan.ticket_id])
    ):
        # Requests about a named customer without an identifier cannot become an actionable decision.
        generic = "policy" in state["task"].lower() and not any(
            x in state["task"].lower() for x in ["customer", "order", "requests"]
        )
        data["policy_result"] = (
            {
                "decision": "inform",
                "amount": 0,
                "required_sources": [],
                "reason_codes": ["POLICY_INFORMATION"],
            }
            if generic
            else missing("EXPLICIT_ORDER_REQUIRED")
        )
    elif plan.task_type == "shipping" and data["order_data"] and data["customer_data"]:
        data["policy_result"] = {
            "decision": "inform",
            "amount": 0,
            "required_sources": ["shipping"],
            "reason_codes": ["DELIVERY_STATUS"],
        }
    else:
        data["policy_result"] = missing("MISSING_RECORD")
    return data | {"tool_calls": calls}


def missing(code):
    return {
        "decision": "insufficient_evidence",
        "amount": 0,
        "required_sources": [],
        "reason_codes": [code],
    }


def answer_node(state):
    start = perf_counter()
    result = dict(state["policy_result"])
    docs = state["retrieved_documents"]
    trusted = [
        r
        for r in docs
        if r["trusted"] and r["section"] != "Scope and recordkeeping" and r["section"] != "Overview"
    ]
    present = {r["document_id"] for r in trusted}
    required = set(result["required_sources"])
    insufficient = not required.issubset(present) or not trusted
    if insufficient:
        result = missing("MISSING_POLICY_EVIDENCE")
    sources = [r for r in trusted if r["document_id"] in required] if required else trusted[:2]
    citations = [
        Citation(chunk_id=r["chunk_id"], document_name=r["document_name"], section=r["section"])
        for r in sources
    ]
    decision, amount = result["decision"], result["amount"]
    message = {
        "approve": f"Recommend a USD {amount:,.2f} refund. Verified order facts satisfy the applicable return rules. Human approval is required before creating an internal support action.",
        "deny": "Do not approve a refund. The recorded order falls outside the applicable eligibility conditions.",
        "warranty": "Recommend warranty replacement rather than a cash refund. The recorded defect is covered by the warranty window.",
        "escalate": "Refer this request to a specialist. A risk, value, shipping or privacy condition requires manual review.",
        "insufficient_evidence": "Insufficient evidence. No business action can be approved until the missing records or policy evidence are resolved.",
        "inform": "Relevant policy evidence is shown below. No business operation has been requested or executed.",
    }[decision]
    if result["reason_codes"] == ["DELIVERY_STATUS"]:
        message = f"Order {state['order_data']['id']} is {state['order_data']['status']}. Shipping policy evidence is attached. No business action has been executed."
    answer = AgentAnswer(
        decision=decision,
        recommendation=message,
        amount=amount,
        citations=citations,
        evidence_status="insufficient"
        if decision == "insufficient_evidence"
        else "restricted"
        if result["reason_codes"] == ["PRIVACY_REVIEW"]
        else "sufficient",
        confidence=0
        if decision == "insufficient_evidence"
        else round(len(required & present) / max(1, len(required)), 2),
        reason_codes=result["reason_codes"],
    )
    usage = state["token_usage"]
    if state["mode"] == "live":
        answer, used = OpenAIProvider().structured_generate(
            (PROMPTS / "answer.txt").read_text(),
            json.dumps(
                {
                    "task": state["task"],
                    "policy_result": result,
                    "order": state.get("order_data"),
                    "customer": state.get("customer_data"),
                    "allowed_citations": [c.model_dump() for c in citations],
                    "evidence": trusted,
                    "draft": answer.model_dump(),
                }
            ),
            AgentAnswer,
        )
        usage = usage_add(usage, used)
    add_event(
        state["run_id"],
        "answer",
        {"source_count": len(citations)},
        {"answer": answer.model_dump()},
        (perf_counter() - start) * 1000,
    )
    return {"draft_answer": answer.model_dump(), "token_usage": usage}


def evaluator_node(state):
    start = perf_counter()
    result = evaluate_answer(state)
    add_event(
        state["run_id"],
        "evaluator",
        {"threshold": state["threshold"]},
        result.model_dump(),
        (perf_counter() - start) * 1000,
    )
    return {"evaluation": result.model_dump(), "attempts": state.get("attempts", 0) + 1}


def approval_node(state):
    status = "pending" if state["evaluation"]["passed"] else "blocked"
    add_event(
        state["run_id"],
        "human_review",
        {"decision": state["draft_answer"]["decision"]},
        {"approval_status": status, "action_executed": False},
    )
    return {"approval_status": status}
