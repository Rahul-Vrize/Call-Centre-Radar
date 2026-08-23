"""GET /calls/{id} — the full grounded detail: transcript, intent, mood timeline,
resolution, summary, needs-attention score, all with evidence."""
from fastapi import APIRouter, HTTPException

from app.schemas.call import CallDetail

router = APIRouter()


@router.get("/{call_id}", response_model=CallDetail)
def get_call(call_id: str):
    raise HTTPException(status_code=501, detail="not implemented")
