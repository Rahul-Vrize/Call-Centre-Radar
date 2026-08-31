"""POST /calls/{id}/review — manager triage, recorded as an append-only log.

The whole system refuses to let the model assert anything without a citation.
This applies the same rule to the people using it: closing a call is not a flag
being flipped, it is an event with an author, a time and a reason, and it stays
in the record even after it is undone.

That is why there is no UPDATE and no DELETE in this module. "Undo" appends a
`reopened` row; current state is simply the newest row. A call closed, reopened
and closed again reads back as exactly that, which is the point — a triage
history that can be quietly rewritten is not evidence of anything.

What this does NOT touch is `calls.resolution_status`. That column is the
model's judgment about whether the call solved the customer's problem, and it
is the input to every resolution rate, agent coaching gap and failing-issue
number on the dashboard. If a manager's click wrote to it, then the moment
anyone triaged a few calls, "Gas bill payments resolve at 69%" would stop being
a fact about the call centre and start being a fact about who clicked what.
The two live apart so that both stay true.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db.session import DbConn
from app.schemas.call import ReviewEvent, ReviewRequest, ReviewState

router = APIRouter()

#: Longest note we will store. Long enough for a real handover sentence, short
#: enough that the column never becomes a dumping ground.
MAX_NOTE_CHARS = 500
MAX_REVIEWER_CHARS = 80

#: Calls whose most recent review event closed them. Written once here and
#: imported by the ranked views, so "what counts as reviewed" has exactly one
#: definition — a queue that disagreed with the detail page about whether a
#: call was done would be worse than having no queue filter at all.
REVIEWED_CALL_IDS = """
    SELECT r.call_id FROM call_reviews r
    WHERE r.id = (SELECT MAX(r2.id) FROM call_reviews r2 WHERE r2.call_id = r.call_id)
      AND r.action = 'reviewed'
"""


def review_state(conn, call_id: str) -> ReviewState:
    """Fold the log down to the current state, newest event first."""
    rows = conn.execute(
        """
        SELECT action, reviewer, note, created_at
        FROM call_reviews WHERE call_id = ? ORDER BY id DESC
        """,
        (call_id,),
    ).fetchall()
    if not rows:
        return ReviewState()

    history = [
        ReviewEvent(
            action=r["action"], reviewer=r["reviewer"],
            note=r["note"] or "", created_at=r["created_at"],
        )
        for r in rows
    ]
    latest = history[0]
    closed = latest.action == "reviewed"
    return ReviewState(
        is_reviewed=closed,
        reviewed_by=latest.reviewer if closed else None,
        reviewed_at=latest.created_at if closed else None,
        note=latest.note if closed else "",
        history=history,
    )


@router.post(
    "/{call_id}/review",
    response_model=ReviewState,
    responses={
        404: {"description": "No such call"},
        409: {"description": "The call is already in that state"},
        422: {"description": "Missing reviewer, or note too long"},
    },
)
def add_review(call_id: str, body: ReviewRequest, conn: DbConn):
    """Append one triage event and return the resulting state."""
    exists = conn.execute("SELECT 1 FROM calls WHERE id = ?", (call_id,)).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail=f"no such call: {call_id}")

    reviewer = body.reviewer.strip()
    if not reviewer:
        raise HTTPException(
            status_code=422,
            detail="reviewer is required — an unattributed review is not a record",
        )
    if len(reviewer) > MAX_REVIEWER_CHARS:
        raise HTTPException(
            status_code=422, detail=f"reviewer exceeds {MAX_REVIEWER_CHARS} characters"
        )

    note = body.note.strip()
    if len(note) > MAX_NOTE_CHARS:
        raise HTTPException(
            status_code=422, detail=f"note exceeds {MAX_NOTE_CHARS} characters"
        )

    # Reject a no-op rather than writing a second identical row. The log should
    # record decisions, not double-clicks.
    current = review_state(conn, call_id)
    already = "reviewed" if current.is_reviewed else "reopened"
    if body.action == already:
        raise HTTPException(
            status_code=409,
            detail=f"call {call_id} is already marked {body.action}",
        )

    with conn:
        conn.execute(
            """
            INSERT INTO call_reviews (call_id, action, reviewer, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                call_id,
                body.action,
                reviewer,
                note,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
    return review_state(conn, call_id)


@router.get("/{call_id}/review", response_model=ReviewState)
def get_review(call_id: str, conn: DbConn):
    """Current state plus the full history. Safe on a call with no events."""
    if not conn.execute("SELECT 1 FROM calls WHERE id = ?", (call_id,)).fetchone():
        raise HTTPException(status_code=404, detail=f"no such call: {call_id}")
    return review_state(conn, call_id)
