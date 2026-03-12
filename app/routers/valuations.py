from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AssetValuation
from app.schemas import AssetValuationCreate, AssetValuationOut

router = APIRouter(prefix="/valuations", tags=["valuations"])


@router.get("", response_model=List[AssetValuationOut])
def list_valuations(
    ticker: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(AssetValuation)
    if ticker:
        q = q.filter(AssetValuation.ticker == ticker)
    if from_date:
        q = q.filter(AssetValuation.date >= from_date)
    if to_date:
        q = q.filter(AssetValuation.date <= to_date)
    return q.order_by(AssetValuation.date.desc()).all()


@router.post("", response_model=AssetValuationOut, status_code=201)
def add_valuation(payload: AssetValuationCreate, db: Session = Depends(get_db)):
    obj = AssetValuation(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
