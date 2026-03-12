from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CouponPayment
from app.schemas import CouponPaymentCreate, CouponPaymentOut

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("", response_model=List[CouponPaymentOut])
def list_coupons(
    ticker: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(CouponPayment)
    if ticker:
        q = q.filter(CouponPayment.ticker == ticker)
    if from_date:
        q = q.filter(CouponPayment.payment_date >= from_date)
    if to_date:
        q = q.filter(CouponPayment.payment_date <= to_date)
    return q.order_by(CouponPayment.payment_date).all()


@router.post("", response_model=CouponPaymentOut, status_code=201)
def add_coupon(payload: CouponPaymentCreate, db: Session = Depends(get_db)):
    obj = CouponPayment(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
