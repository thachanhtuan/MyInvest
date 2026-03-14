from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import QUOTES_LOG_FILE
from app.database import get_db
from app.schemas import PortfolioSummary, QuoteResult
from app.services.portfolio import get_portfolio_summary
from app.services.quotes_service import fetch_all_quotes

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=PortfolioSummary)
def portfolio_summary(db: Session = Depends(get_db)):
    return get_portfolio_summary(db)


@router.post("/quotes-refresh", response_model=QuoteResult)
def refresh_quotes_temp(db: Session = Depends(get_db)) -> QuoteResult:
    """Temporary endpoint for quotes refresh - testing"""
    return fetch_all_quotes(db)


@router.get("/quotes-log", response_class=PlainTextResponse)
def get_quotes_log_temp():
    """Temporary endpoint to view quotes log"""
    if not QUOTES_LOG_FILE.exists():
        return f"Log file not found: {QUOTES_LOG_FILE}"
    try:
        with open(QUOTES_LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading log: {e}"

