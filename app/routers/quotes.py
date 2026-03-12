from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, Quote
from app.schemas import QuoteCreate, QuoteOut
from app.services.market_data import fetch_moex_price

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("", response_model=List[QuoteOut])
def list_quotes(
    ticker: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Quote)
    if ticker:
        q = q.filter(Quote.ticker == ticker)
    if from_date:
        q = q.filter(Quote.date >= from_date)
    if to_date:
        q = q.filter(Quote.date <= to_date)
    return q.order_by(Quote.date.desc()).limit(500).all()


@router.post("", response_model=QuoteOut, status_code=201)
def add_quote(payload: QuoteCreate, db: Session = Depends(get_db)):
    obj = Quote(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/fetch")
async def fetch_quotes(ticker: str, db: Session = Depends(get_db)):
    """Fetch latest price from MOEX and store it."""
    asset = db.query(Asset).filter(Asset.ticker == ticker).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    result = await fetch_moex_price(ticker, asset.asset_class)
    if not result:
        raise HTTPException(status_code=502, detail="Could not fetch price from MOEX")
    price, price_date, currency = result
    existing = (
        db.query(Quote)
        .filter(Quote.ticker == ticker, Quote.date == price_date)
        .first()
    )
    if existing:
        existing.close_price = price
        existing.currency = currency
        existing.source = "MOEX"
    else:
        obj = Quote(
            ticker=ticker,
            date=price_date,
            close_price=price,
            currency=currency,
            source="MOEX",
        )
        db.add(obj)
    db.commit()
    return {"ticker": ticker, "date": str(price_date), "close_price": price, "currency": currency}


@router.get("/fetch/{ticker}")
async def fetch_quote_get(ticker: str, db: Session = Depends(get_db)):
    """GET endpoint to fetch latest quote from MOEX."""
    asset = db.query(Asset).filter(Asset.ticker == ticker).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    result = await fetch_moex_price(ticker, asset.asset_class)
    if not result:
        raise HTTPException(status_code=502, detail="Could not fetch price from MOEX")
    price, price_date, currency = result
    existing = (
        db.query(Quote)
        .filter(Quote.ticker == ticker, Quote.date == price_date)
        .first()
    )
    if existing:
        existing.close_price = price
        existing.currency = currency
        existing.source = "MOEX"
    else:
        obj = Quote(
            ticker=ticker,
            date=price_date,
            close_price=price,
            currency=currency,
            source="MOEX",
        )
        db.add(obj)
    db.commit()
    return {"ticker": ticker, "date": str(price_date), "close_price": price, "currency": currency}
