"""GET /attention?date= — the ranked "needs a manager's attention today" view."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.api.reviews import REVIEWED_CALL_IDS
from app.db.session import DbConn
from app.schemas.call import CallSummary

router = APIRouter()


class AttentionDay(BaseModel):
    date: str
    call_count: int


class AttentionResponse(BaseModel):
    #: The day being shown. See `latest_call_date` for why this isn't "today".
    date: str | None
    #: Every day the corpus actually covers, so the UI can offer them.
    available_dates: list[AttentionDay]
    calls: list[CallSummary]
    #: How many of this day's calls a human has already triaged. Shown even
    #: when they are hidden, so the queue emptying reads as work done rather
    #: than as data going missing.
    reviewed_count: int = 0


def latest_call_date(conn) -> str | None:
    """What "today" means for this dataset.

    The corpus spans four days in 2020 (2020-03-15, 05-30, 06-01, 06-02), so a
    literal `DATE('now')` returns an empty list forever — the flagship view
    would be blank on stage. "Today" is therefore the most recent day that
    actually has calls, and the caller can override it with ?date=.
    """
    row = conn.execute("SELECT MAX(DATE(started_at)) AS d FROM calls").fetchone()
    return row["d"] if row and row["d"] else None


@router.get("", response_model=AttentionResponse)
def needs_attention(
    conn: DbConn,
    date: str | None = None,
    limit: int = 100,
    include_reviewed: bool = False,
):
    """Ranked calls for one day.

    Reviewed calls drop out by default. A queue whose job is "what still needs
    a manager" has to shrink as it is worked, or nobody can tell what is left;
    `include_reviewed=true` brings them back for anyone auditing what was done.
    """
    days = [
        AttentionDay(date=r["day"], call_count=r["n"])
        for r in conn.execute(
            """
            SELECT DATE(started_at) AS day, COUNT(*) AS n
            FROM calls GROUP BY day ORDER BY day DESC
            """
        )
    ]

    day = date or latest_call_date(conn)
    if day is None:
        return AttentionResponse(date=None, available_dates=days, calls=[])

    reviewed_count = conn.execute(
        f"""
        SELECT COUNT(*) FROM calls
        WHERE DATE(started_at) = ? AND id IN ({REVIEWED_CALL_IDS})
        """,
        (day,),
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        SELECT c.id, c.started_at, c.duration_seconds, c.intent_label,
               c.resolution_status, c.summary, c.attention_score,
               CASE WHEN c.id IN ({REVIEWED_CALL_IDS}) THEN 1 ELSE 0 END AS is_reviewed
        FROM calls c
        WHERE DATE(c.started_at) = ?
          AND ({int(include_reviewed)} = 1 OR c.id NOT IN ({REVIEWED_CALL_IDS}))
        -- SQLite sorts NULL below any value, so DESC puts unscored calls last:
        -- analysed calls rank above ones that haven't been.
        ORDER BY c.attention_score DESC, c.started_at DESC
        LIMIT ?
        """,
        (day, limit),
    ).fetchall()

    return AttentionResponse(
        date=day,
        available_dates=days,
        reviewed_count=reviewed_count,
        calls=[
            CallSummary(**{k: r[k] for k in r.keys() if k != "is_reviewed"},
                        is_reviewed=bool(r["is_reviewed"]))
            for r in rows
        ],
    )
