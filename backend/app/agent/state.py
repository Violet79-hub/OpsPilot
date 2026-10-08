from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    task: str
    mode: str
    top_k: int
    threshold: float
    plan: dict
    retrieved_documents: list
    tool_calls: list
    order_data: dict | None
    customer_data: dict | None
    ticket_data: dict | None
    policy_result: dict
    draft_answer: dict
    evaluation: dict
    token_usage: dict
    attempts: int
    approval_status: str
