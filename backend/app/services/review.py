from sqlalchemy import select, update
from fastapi import HTTPException
from app.db.models import AgentRun, HumanReview, SupportAction, AgentEvent
from app.db.repository import Session, new_id


def review_run(rid, review):
    with Session.begin() as s:
        run = s.scalar(select(AgentRun).where(AgentRun.id == rid).with_for_update())
        if not run:
            raise HTTPException(404, "Run not found")
        if (
            run.status not in {"pending_review", "blocked"}
            or run.revision != review.expected_revision
        ):
            raise HTTPException(
                409, "Run changed or was already reviewed; refresh before submitting"
            )
        if review.decision in {"approve", "edit"} and not run.state.get("evaluation", {}).get(
            "passed"
        ):
            raise HTTPException(
                409, "Evaluation failed; this recommendation cannot be approved or edited"
            )
        if review.decision == "edit" and not (review.edited_answer or "").strip():
            raise HTTPException(422, "A non-empty edited recommendation is required")
        status = {"approve": "approved", "reject": "rejected", "edit": "pending_review"}[
            review.decision
        ]
        changed = s.execute(
            update(AgentRun)
            .where(AgentRun.id == rid, AgentRun.revision == review.expected_revision)
            .values(status=status, revision=AgentRun.revision + 1)
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Concurrent review conflict")
        s.add(
            HumanReview(
                id=new_id(),
                run_id=rid,
                decision=review.decision,
                edited_answer=review.edited_answer,
            )
        )
        state = dict(run.state)
        if review.decision == "edit":
            # Human wording is retained separately and never changes computed amounts or citations.
            state["human_edited_answer"] = review.edited_answer.strip()
        state["approval_status"] = status
        run.state = state
        if review.decision == "approve":
            s.add(
                SupportAction(
                    id=new_id(),
                    run_id=rid,
                    action={
                        "type": "internal_support_recommendation",
                        "answer": state["draft_answer"],
                        "human_note": state.get("human_edited_answer"),
                        "payment_executed": False,
                    },
                )
            )
        s.add(
            AgentEvent(
                run_id=rid,
                node="human_review",
                event_type=review.decision,
                input_summary={"revision": review.expected_revision},
                output_summary={"status": status, "payment_executed": False},
                duration=0,
            )
        )
    return {"status": status, "revision": review.expected_revision + 1}
