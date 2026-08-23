"""GET /attention?date= — the ranked "needs a manager's attention today" view."""
from fastapi import APIRouter, HTTPException

from app.schemas.call import CallSummary

router = APIRouter()


@router.get("", response_model=list[CallSummary])
def needs_attention(date: str | None = None):
    raise HTTPException(status_code=501, detail="not implemented")
