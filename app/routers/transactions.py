from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction
from app.schemas import TransactionCreate, TransactionOut, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=List[TransactionOut])
def list_transactions(
    account_id: Optional[str] = None,
    ticker: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    tx_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if ticker:
        q = q.filter(Transaction.ticker == ticker)
    if from_date:
        q = q.filter(Transaction.date >= from_date)
    if to_date:
        q = q.filter(Transaction.date <= to_date)
    if tx_type:
        q = q.filter(Transaction.tx_type == tx_type)
    return q.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    obj = Transaction(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    obj = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    obj = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(obj)
    db.commit()
