"""GET /customers, GET /customers/{id}/calls — reads only, no pipeline work here."""
from fastapi import APIRouter, HTTPException

from app.schemas.call import Customer, CallSummary

router = APIRouter()


@router.get("", response_model=list[Customer])
def list_customers():
    raise HTTPException(status_code=501, detail="not implemented")


@router.get("/{customer_id}/calls", response_model=list[CallSummary])
def customer_calls(customer_id: str):
    raise HTTPException(status_code=501, detail="not implemented")
