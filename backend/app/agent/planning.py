import re
from app.schemas import Plan, Step

QUERIES = {
    "refund": [
        "refund eligibility physical unopened opened defective restocking",
        "Gold customer return extension",
        "hardware defects warranty replacement",
        "manual review refunds above 1500",
        "fraud high risk holds",
        "returns misuse condition verification",
        "shipping in transit delivery investigation",
        "digital downloads refund",
    ],
    "warranty": [
        "hardware defects warranty replacement",
        "refund eligibility defective return window",
        "Gold customer return extension",
        "returns misuse condition verification",
        "fraud high risk holds",
        "manual review refunds above 1500",
    ],
    "cancellation": [
        "subscription cancellation refunds unused 7 days",
        "fraud high risk holds",
        "manual review refunds above 1500",
    ],
    "shipping": [
        "shipping in transit delivery investigation",
        "customer support evidence order customer",
    ],
    "privacy": ["privacy personal data identity disclosure"],
    "support": [
        "customer support ticket order customer evidence",
        "refund eligibility physical defective",
        "Gold customer return extension",
        "hardware warranty",
        "fraud high risk",
        "manual review refunds",
    ],
    "policy": [],
    "unknown": ["customer support evidence missing order customer"],
}


def demo_plan(task):
    lower = task.lower()
    order = re.search(r"(?:NS-|#)(\d{4})\b", task, re.I)
    customer = re.search(r"\bC\d{3}\b", task, re.I)
    ticket = re.search(r"\bT\d{3}\b", task, re.I)
    if any(
        x in lower
        for x in ["email", "personal data", "export customer", "privacy", "payment details"]
    ):
        kind = "privacy"
    elif any(x in lower for x in ["subscription", "cancel"]):
        kind = "cancellation"
    elif any(x in lower for x in ["refund", "return"]):
        kind = "refund"
    elif any(x in lower for x in ["warranty", "replacement", "defect"]):
        kind = "warranty"
    elif any(x in lower for x in ["shipping", "delivery", "tracking"]):
        kind = "shipping"
    elif ticket:
        kind = "support"
    elif "policy" in lower or "policies" in lower:
        kind = "policy"
    else:
        kind = "unknown"
    names = ["search_knowledge"]
    if kind != "privacy":
        if ticket:
            names += ["get_support_ticket"]
        if order or ticket:
            names += ["get_order", "get_customer"]
            if kind in {"refund", "warranty", "cancellation", "support"}:
                names += ["calculate_refund"]
        elif customer:
            names += ["get_customer"]
    return Plan(
        task_type=kind,
        order_id="NS-" + order[1] if order else None,
        customer_id=customer[0].upper() if customer else None,
        ticket_id=ticket[0].upper() if ticket else None,
        query=task[:2000],
        steps=[
            Step(
                action=n,
                reason={
                    "search_knowledge": "Find relevant policy evidence",
                    "get_support_ticket": "Resolve the requested support case",
                    "get_order": "Verify order facts",
                    "get_customer": "Check tier and risk status",
                    "calculate_refund": "Apply auditable business rules",
                }[n],
            )
            for n in names
        ],
    )


def validate_plan(plan, task):
    """Identifier guardrails apply equally to model-generated plans."""
    explicit = demo_plan(task)
    for key in ["order_id", "customer_id", "ticket_id"]:
        if getattr(plan, key) != getattr(explicit, key):
            raise ValueError("Planner identifiers do not match explicit task identifiers")
    if explicit.task_type == "privacy" and plan.task_type != "privacy":
        raise ValueError("Privacy requests must follow the restricted branch")
    if len({s.action for s in plan.steps}) != len(plan.steps):
        raise ValueError("Duplicate tools are not allowed")
    return plan
