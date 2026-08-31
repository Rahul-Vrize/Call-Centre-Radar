"""GET /overview — everything a support manager needs on one screen.

Deliberately one endpoint, not six. The landing page should render in a single
round trip: the research on operational dashboards is consistent that
time-to-insight suffers when a control-room view has to assemble itself from
parallel requests that settle at different moments.

Scope is ALL DATES, unlike /attention which is scoped to a single day. The
question this page answers is "what is wrong across the whole corpus", and the
corpus spans four non-contiguous days — a per-day view here would hide two
thirds of it.

Everything returned is already computed and stored. This endpoint aggregates;
it never analyses.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.db.session import DbConn
from app.schemas.call import CallSummary, Evidence

router = APIRouter()

#: An issue resolving this far below the corpus baseline is flagged.
RESOLUTION_ALERT_GAP = 0.05

#: Minimum calls before an agent's per-issue rate is worth reporting.
MIN_CALLS_FOR_AGENT_ISSUE = 8

#: A customer contacting this many times about ONE issue is a pattern.
REPEAT_THRESHOLD = 3

_RESOLVED = (
    "AVG(CASE WHEN {t}.resolution_status IS NULL THEN NULL "
    "         WHEN {t}.resolution_status = 'resolved' THEN 1.0 ELSE 0.0 END)"
)


class Kpis(BaseModel):
    calls_analysed: int
    hours_of_audio: float
    days_covered: int
    citations_total: int
    citations_verified: int
    citation_rate: float
    unresolved: int
    needs_attention: int
    repeat_contact_issues: int


class FailingIssue(BaseModel):
    cluster_id: int
    label: str
    call_count: int
    resolution_rate: float
    gap: float               # vs corpus baseline, in points
    avg_attention: float


class AgentGap(BaseModel):
    agent_id: str
    agent_name: str
    overall_rate: float
    issue_label: str
    issue_rate: float
    gap: float               # vs the agent's OWN baseline
    call_count: int


class RepeatContact(BaseModel):
    customer_id: str
    customer_name: str
    cluster_id: int
    issue_label: str
    call_count: int
    unresolved_count: int


class IssueBar(BaseModel):
    cluster_id: int
    label: str
    call_count: int
    resolution_rate: float
    avg_attention: float
    below_baseline: bool


class DayVolume(BaseModel):
    date: str
    call_count: int
    unresolved: int
    avg_attention: float


class Overview(BaseModel):
    kpis: Kpis
    baseline_resolution: float
    attention_queue: list[CallSummary]
    failing_issues: list[FailingIssue]
    agent_gaps: list[AgentGap]
    repeat_contacts: list[RepeatContact]
    issues: list[IssueBar]
    days: list[DayVolume]


@router.get("", response_model=Overview)
def overview(conn: DbConn, queue_size: int = 8):
    base = conn.execute(
        f"""
        SELECT COUNT(*) AS n,
               COALESCE(SUM(c.duration_seconds) / 3600.0, 0) AS hours,
               COALESCE({_RESOLVED.format(t='c')}, 0) AS res
        FROM calls c WHERE c.analyzed_at IS NOT NULL
        """
    ).fetchone()
    baseline = base["res"]

    ev = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(verified), 0) AS v FROM evidence"
    ).fetchone()

    repeats_n = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT c.customer_id, cc.cluster_id
            FROM call_clusters cc JOIN calls c ON c.id = cc.call_id
            GROUP BY 1, 2 HAVING COUNT(*) >= ?
        )
        """,
        (REPEAT_THRESHOLD,),
    ).fetchone()[0]

    kpis = Kpis(
        calls_analysed=base["n"],
        hours_of_audio=round(base["hours"], 1),
        days_covered=conn.execute(
            "SELECT COUNT(DISTINCT DATE(started_at)) FROM calls"
        ).fetchone()[0],
        citations_total=ev["n"],
        citations_verified=ev["v"],
        citation_rate=(ev["v"] / ev["n"]) if ev["n"] else 0.0,
        unresolved=conn.execute(
            "SELECT COUNT(*) FROM calls WHERE resolution_status = 'unresolved'"
        ).fetchone()[0],
        needs_attention=conn.execute(
            "SELECT COUNT(*) FROM calls WHERE attention_score >= 30"
        ).fetchone()[0],
        repeat_contact_issues=repeats_n,
    )

    # --- the queue: worst calls anywhere in the corpus, not just one day ----
    #
    # Joined to the intent citation so the ranked list carries its own evidence.
    # A dashboard row that states an intent without showing the words behind it
    # is a claim the reader has to take on trust — which is the thing this
    # system exists not to ask for.
    queue = []
    for r in conn.execute(
        """
        SELECT c.id, c.started_at, c.duration_seconds, c.intent_label,
               c.resolution_status, c.summary, c.attention_score,
               e.turn_id, e.timestamp, e.quote, e.verified,
               e.match_score, e.support_score
        FROM calls c
        LEFT JOIN evidence e
               ON e.call_id = c.id AND e.claim_type = 'intent'
        WHERE c.analyzed_at IS NOT NULL
        ORDER BY c.attention_score DESC, c.started_at DESC LIMIT ?
        """,
        (queue_size,),
    ):
        queue.append(
            CallSummary(
                id=r["id"], started_at=r["started_at"],
                duration_seconds=r["duration_seconds"],
                intent_label=r["intent_label"],
                resolution_status=r["resolution_status"],
                summary=r["summary"], attention_score=r["attention_score"],
                intent_evidence=(
                    Evidence(
                        turn_id=r["turn_id"] or 0, timestamp=r["timestamp"],
                        quote=r["quote"], verified=bool(r["verified"]),
                        match_score=r["match_score"] or 0.0,
                        support_score=r["support_score"] or 0.0,
                    )
                    if r["quote"] else None
                ),
            )
        )

    # --- issues, with the failing ones separated out ------------------------
    issue_rows = conn.execute(
        f"""
        SELECT ic.id, ic.label, COUNT(*) AS n,
               COALESCE({_RESOLVED.format(t='c')}, 0) AS res,
               COALESCE(AVG(c.attention_score), 0) AS attn
        FROM issue_clusters ic
        JOIN call_clusters cc ON cc.cluster_id = ic.id
        JOIN calls c          ON c.id = cc.call_id
        GROUP BY ic.id, ic.label ORDER BY n DESC
        """
    ).fetchall()

    issues = [
        IssueBar(
            cluster_id=r["id"], label=r["label"], call_count=r["n"],
            resolution_rate=r["res"], avg_attention=r["attn"],
            below_baseline=(r["res"] - baseline) < -RESOLUTION_ALERT_GAP,
        )
        for r in issue_rows
    ]
    failing = sorted(
        (
            FailingIssue(
                cluster_id=i.cluster_id, label=i.label, call_count=i.call_count,
                resolution_rate=i.resolution_rate,
                gap=i.resolution_rate - baseline, avg_attention=i.avg_attention,
            )
            for i in issues if i.below_baseline
        ),
        key=lambda x: x.gap,
    )

    # --- agents underperforming their OWN baseline on one issue -------------
    agent_gaps: list[AgentGap] = []
    for a in conn.execute(
        f"""
        SELECT a.id, a.name, COALESCE({_RESOLVED.format(t='c')}, 0) AS rate
        FROM agents a JOIN calls c ON c.agent_id = a.id
        WHERE c.analyzed_at IS NOT NULL GROUP BY a.id, a.name
        """
    ):
        worst = conn.execute(
            f"""
            SELECT ic.label, COUNT(*) AS n, COALESCE({_RESOLVED.format(t='c')}, 0) AS res
            FROM calls c
            JOIN call_clusters cc ON cc.call_id = c.id
            JOIN issue_clusters ic ON ic.id = cc.cluster_id
            WHERE c.agent_id = ? AND c.analyzed_at IS NOT NULL
            GROUP BY ic.id HAVING n >= ? ORDER BY res LIMIT 1
            """,
            (a["id"], MIN_CALLS_FOR_AGENT_ISSUE),
        ).fetchone()
        if worst and (worst["res"] - a["rate"]) < -0.10:
            agent_gaps.append(
                AgentGap(
                    agent_id=a["id"], agent_name=a["name"], overall_rate=a["rate"],
                    issue_label=worst["label"], issue_rate=worst["res"],
                    gap=worst["res"] - a["rate"], call_count=worst["n"],
                )
            )
    agent_gaps.sort(key=lambda x: x.gap)

    # --- customers stuck on one issue ---------------------------------------
    repeats = [
        RepeatContact(
            customer_id=r["customer_id"], customer_name=r["name"],
            cluster_id=r["cluster_id"], issue_label=r["label"],
            call_count=r["n"], unresolved_count=r["unres"] or 0,
        )
        for r in conn.execute(
            """
            SELECT c.customer_id, cu.name, cc.cluster_id, ic.label,
                   COUNT(*) AS n,
                   SUM(CASE WHEN c.resolution_status='unresolved' THEN 1 ELSE 0 END) AS unres
            FROM call_clusters cc
            JOIN calls c           ON c.id = cc.call_id
            JOIN customers cu      ON cu.id = c.customer_id
            JOIN issue_clusters ic ON ic.id = cc.cluster_id
            GROUP BY c.customer_id, cc.cluster_id
            HAVING n >= ? ORDER BY n DESC, unres DESC LIMIT 5
            """,
            (REPEAT_THRESHOLD,),
        )
    ]

    days = [
        DayVolume(
            date=r["d"], call_count=r["n"], unresolved=r["unres"] or 0,
            avg_attention=r["attn"] or 0.0,
        )
        for r in conn.execute(
            """
            SELECT DATE(started_at) AS d, COUNT(*) AS n,
                   SUM(CASE WHEN resolution_status='unresolved' THEN 1 ELSE 0 END) AS unres,
                   AVG(attention_score) AS attn
            FROM calls GROUP BY d ORDER BY d
            """
        )
    ]

    return Overview(
        kpis=kpis, baseline_resolution=baseline, attention_queue=queue,
        failing_issues=failing, agent_gaps=agent_gaps[:4],
        repeat_contacts=repeats, issues=issues, days=days,
    )
