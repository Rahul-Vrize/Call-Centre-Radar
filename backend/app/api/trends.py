"""GET /trends — recurring issue clusters and their frequency over time."""
from fastapi import APIRouter, HTTPException

from app.schemas.call import TrendingIssue

router = APIRouter()


@router.get("", response_model=list[TrendingIssue])
def trending_issues():
    raise HTTPException(status_code=501, detail="not implemented")
