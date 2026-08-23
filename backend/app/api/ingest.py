"""POST /ingest — the live-demo path. Runs the full pipeline synchronously (or
via background task + polling) on a recording that was never in the precomputed
batch, proving this is a pipeline and not just a lookup table."""
from fastapi import APIRouter, HTTPException, UploadFile

router = APIRouter()


@router.post("")
async def ingest_call(audio: UploadFile, customer_name: str, agent_name: str):
    raise HTTPException(status_code=501, detail="not implemented")
