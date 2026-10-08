from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Step(StrictModel):
    action: Literal[
        "search_knowledge", "get_order", "get_customer", "get_support_ticket", "calculate_refund"
    ]
    reason: str


class Plan(StrictModel):
    task_type: Literal[
        "refund", "warranty", "shipping", "cancellation", "privacy", "support", "policy", "unknown"
    ]
    order_id: str | None = None
    customer_id: str | None = None
    ticket_id: str | None = None
    query: str = Field(min_length=1, max_length=2000)
    steps: list[Step] = Field(min_length=1, max_length=6)


class Citation(StrictModel):
    chunk_id: str
    document_name: str
    section: str


class AgentAnswer(StrictModel):
    decision: Literal["approve", "deny", "warranty", "escalate", "insufficient_evidence", "inform"]
    recommendation: str = Field(min_length=1)
    amount: float = Field(ge=0)
    currency: Literal["USD"] = "USD"
    citations: list[Citation]
    evidence_status: Literal["sufficient", "insufficient", "restricted"]
    confidence: float = Field(ge=0, le=1)
    reason_codes: list[str]


class EvaluationResult(StrictModel):
    passed: bool
    score: float = Field(ge=0, le=1)
    issues: list[str]
    needs_human_review: bool = True
    checks: dict[str, bool]


class RunRequest(StrictModel):
    task: str = Field(min_length=8, max_length=4000)
    mode: Literal["demo", "live"] = "demo"
    top_k: int = Field(default=6, ge=1, le=12)
    threshold: float = Field(default=0.8, ge=0.5, le=1)


class ReviewRequest(StrictModel):
    decision: Literal["approve", "reject", "edit"]
    edited_answer: str | None = Field(default=None, max_length=4000)
    expected_revision: int = Field(ge=0)
