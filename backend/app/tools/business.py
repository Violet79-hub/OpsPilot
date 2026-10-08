from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from app.config import AS_OF, DATA
from app.db.models import Customer, Order, SupportTicket
from app.db.repository import Session, row_dict

POLICIES = json.loads((DATA / "policy_rules.json").read_text())


def get_order(order_id: str):
    with Session() as s:
        return row_dict(s.get(Order, order_id))


def get_customer(customer_id: str):
    with Session() as s:
        row = row_dict(s.get(Customer, customer_id))
        if row:
            row.pop("email", None)
        return row


def get_support_ticket(ticket_id: str):
    with Session() as s:
        return row_dict(s.get(SupportTicket, ticket_id))


def calculate_refund(order_id: str):
    order = get_order(order_id)
    if not order:
        return {
            "decision": "insufficient_evidence",
            "amount": 0,
            "required_sources": ["support"],
            "reason_codes": ["ORDER_NOT_FOUND"],
        }
    customer = get_customer(order["customer_id"])
    return decide(order, customer)


def decide(order, customer):
    def result(decision, amount, sources, code):
        return {
            "decision": decision,
            "amount": float(amount),
            "required_sources": sources,
            "reason_codes": [code],
            "as_of": AS_OF,
        }

    if not order or not customer:
        return result("insufficient_evidence", 0, ["support"], "MISSING_RECORD")
    if customer["risk_level"] == "high":
        return result("escalate", 0, ["fraud", "escalation"], "FRAUD_HOLD")
    amount = Decimal(str(order["amount"]))
    if amount > POLICIES["escalation"]["rules"]["max_refund_usd"]:
        return result("escalate", 0, ["escalation"], "VALUE_REQUIRES_REVIEW")
    if order["category"] == "digital":
        return result("deny", 0, ["refund"], "DIGITAL_EXCLUDED")
    if order["category"] == "subscription":
        days = (date.fromisoformat(AS_OF) - date.fromisoformat(order["purchase_date"])).days
        eligible = (
            0 <= days <= POLICIES["cancellation"]["rules"]["subscription_days"]
            and order["condition"] == "unused"
        )
        return result(
            "approve" if eligible else "deny",
            amount if eligible else 0,
            ["cancellation"],
            "UNUSED_WITHIN_WINDOW" if eligible else "SUBSCRIPTION_EXCLUDED",
        )
    if order["status"] != "delivered" or not order["delivery_date"]:
        return result("escalate", 0, ["shipping"], "DELIVERY_INVESTIGATION")
    days = (date.fromisoformat(AS_OF) - date.fromisoformat(order["delivery_date"])).days
    if days < 0:
        return result("insufficient_evidence", 0, ["support"], "INVALID_DELIVERY_DATE")
    if order["condition"] == "misuse":
        return result("deny", 0, ["returns", "warranty"], "MISUSE_EXCLUDED")
    if order["condition"] not in {"unopened", "opened", "defective"}:
        return result("insufficient_evidence", 0, ["returns"], "UNKNOWN_CONDITION")
    gold = customer["tier"] == "Gold"
    window = (
        POLICIES["vip"]["rules"]["gold_window_days"]
        if gold
        else POLICIES["refund"]["rules"]["window_days"]
    )
    sources = ["refund"] + (["vip"] if gold else [])
    if days <= window:
        factor = (
            Decimal("1") - Decimal(str(POLICIES["refund"]["rules"]["restocking_rate"]))
            if order["condition"] == "opened"
            else Decimal("1")
        )
        value = (amount * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return result(
            "approve", value, sources, "RESTOCKING_FEE" if factor < 1 else "WITHIN_RETURN_WINDOW"
        )
    if order["condition"] == "defective" and days <= POLICIES["warranty"]["rules"]["warranty_days"]:
        return result("warranty", 0, ["warranty"] + sources, "WARRANTY_REPLACEMENT")
    return result(
        "deny",
        0,
        sources + (["warranty"] if order["condition"] == "defective" else []),
        "WINDOW_EXPIRED",
    )
