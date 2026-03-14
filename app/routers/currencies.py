from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.config import CURRENCY_RATES_LOG_FILE
from app.database import get_db
from app.schemas import CurrencyRateResult
from app.services.currency_service import fetch_currency_rates
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/currencies", tags=["currencies"])


@router.post("/rates/refresh", response_model=CurrencyRateResult)
def refresh_currency_rates(
    date: datetime.date | None = Query(default=None, description="Дата курса (YYYY-MM-DD). По умолчанию — сегодня."),
    db: Session = Depends(get_db),
) -> CurrencyRateResult:
    """Fetch currency rates from CBR for the given date and save to currency_rates."""
    return fetch_currency_rates(db, date)


@router.get("/rates/log", response_class=PlainTextResponse)
def get_currency_rates_log() -> str:
    """Return the content of the currency rates log file."""
    if not CURRENCY_RATES_LOG_FILE.exists():
        return f"Log file not found: {CURRENCY_RATES_LOG_FILE}"
    try:
        with open(CURRENCY_RATES_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return content or f"Log file is empty: {CURRENCY_RATES_LOG_FILE}"
    except Exception as exc:
        return f"Error reading log file: {exc}"
