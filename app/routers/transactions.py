from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction
from app.schemas import TransactionRead

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    account_id: str | None = Query(None),
    ticker: str | None = Query(None),
    tx_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction).order_by(Transaction.date.desc())
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if ticker:
        query = query.filter(Transaction.ticker == ticker)
    if tx_type:
        query = query.filter(Transaction.tx_type == tx_type)
    return query.all()
