from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.billing_store import (
    get_records,
    find_by_invoice,
    create_record,
)


router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


class BillingRecordCreate(BaseModel):
    company: str
    invoice_id: str
    amount: str
    due_date: str


@router.get("/records")
def list_billing_records():
    return {
        "records": get_records()
    }


@router.get("/records/{invoice_id}")
def get_billing_record(invoice_id: str):

    record = find_by_invoice(invoice_id)

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Billing record not found"
        )

    return record


@router.post("/records")
def create_billing_record(payload: BillingRecordCreate):

    record = create_record(
        company=payload.company,
        invoice_id=payload.invoice_id,
        amount=payload.amount,
        due_date=payload.due_date
    )

    return record