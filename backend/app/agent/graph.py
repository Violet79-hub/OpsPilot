from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.nodes import (
    planner,
    retrieval,
    tool_node,
    answer_node,
    evaluator_node,
    approval_node,
)

builder = StateGraph(AgentState)
for name, fn in [
    ("planner", planner),
    ("retrieval", retrieval),
    ("tools", tool_node),
    ("answer", answer_node),
    ("evaluator", evaluator_node),
    ("approval", approval_node),
]:
    builder.add_node(name, fn)
builder.add_edge(START, "planner")
builder.add_edge("planner", "retrieval")
builder.add_edge("retrieval", "tools")
builder.add_edge("tools", "answer")
builder.add_edge("answer", "evaluator")
builder.add_conditional_edges(
    "evaluator",
    lambda s: "retry" if not s["evaluation"]["passed"] and s["attempts"] < 2 else "finish",
    {"retry": "retrieval", "finish": "approval"},
)
builder.add_edge("approval", END)
graph = builder.compile()
# Durable human review is an application-level transaction after graph completion.
# We deliberately do not claim LangGraph checkpoint/interrupt persistence.
