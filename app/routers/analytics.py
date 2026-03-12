from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.portfolio import (
    get_asset_allocation,
    get_bond_ladder,
    get_coupon_schedule,
    get_holdings,
    get_portfolio_return,
    get_portfolio_value,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/holdings")
def holdings(
    account_id: Optional[str] = None,
    broker: Optional[str] = None,
    as_of_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    return get_holdings(db, account_id=account_id, broker=broker, as_of_date=as_of_date)


@router.get("/portfolio-value")
def portfolio_value(
    account_id: Optional[str] = None,
    as_of_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    holdings = get_holdings(db, account_id=account_id, as_of_date=as_of_date)
    return get_portfolio_value(db, holdings, as_of_date=as_of_date)


@router.get("/allocation")
def allocation(
    account_id: Optional[str] = None,
    as_of_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    return get_asset_allocation(db, account_id=account_id, as_of_date=as_of_date)


@router.get("/returns")
def returns(
    account_id: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    return get_portfolio_return(db, account_id=account_id, from_date=from_date, to_date=to_date)


@router.get("/bond-ladder")
def bond_ladder(
    account_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return get_bond_ladder(db, account_id=account_id)


@router.get("/coupon-schedule")
def coupon_schedule(
    account_id: Optional[str] = None,
    months_ahead: int = 12,
    db: Session = Depends(get_db),
):
    return get_coupon_schedule(db, account_id=account_id, months_ahead=months_ahead)
