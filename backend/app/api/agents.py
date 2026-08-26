"""GET /agents — per-agent call volume, handle time, and outcomes.

Volume and handle time come straight from metadata, so this view is meaningful
as soon as calls are ingested. Resolution rate and average attention depend on
the reasoning layer and read 0 until it has run.
"""
from fastapi import APIRouter

from app.db.session import DbConn
from app.schemas.call import AgentStats

router = APIRouter()


@router.get("", response_model=list[AgentStats])
def list_agents(conn: DbConn):
    rows = conn.execute(
        """
        SELECT a.id,
               a.name,
               COUNT(c.id) AS call_count,
               COALESCE(AVG(c.duration_seconds), 0) AS avg_handle_time_seconds,
               -- Rate over ANALYSED calls only; an unanalysed call is unknown,
               -- not unresolved, and averaging it in as 0 would defame the agent.
               COALESCE(
                   AVG(CASE WHEN c.resolution_status IS NULL THEN NULL
                            WHEN c.resolution_status = 'resolved' THEN 1.0
                            ELSE 0.0 END),
                   0
               ) AS resolution_rate,
               COALESCE(AVG(c.attention_score), 0) AS avg_attention_score
        FROM agents a
        LEFT JOIN calls c ON c.agent_id = a.id
        GROUP BY a.id, a.name
        ORDER BY call_count DESC, a.name
        """
    ).fetchall()
    return [AgentStats(**dict(r)) for r in rows]
