"""GET /agents — per-agent call volume, handle time, and outcomes."""
from fastapi import APIRouter, HTTPException

from app.schemas.call import AgentStats

router = APIRouter()


@router.get("", response_model=list[AgentStats])
def list_agents():
    raise HTTPException(status_code=501, detail="not implemented")
