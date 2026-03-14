from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session

from app.config import QUOTES_LOG_FILE
from app.database import get_db
from app.schemas import QuoteResult
from app.services.quotes_service import fetch_all_quotes

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.post("/refresh", response_model=QuoteResult)
def refresh_quotes(db: Session = Depends(get_db)) -> QuoteResult:
    """Fetch current market quotes for all open positions."""
    return fetch_all_quotes(db)


@router.get("/log", response_class=PlainTextResponse)
def get_quotes_log():
    """Return the content of the quotes log file."""
    if not QUOTES_LOG_FILE.exists():
        return f"Log file not found: {QUOTES_LOG_FILE}\nParent dir exists: {QUOTES_LOG_FILE.parent.exists()}"
    try:
        with open(QUOTES_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        if not content:
            return f"Log file is empty: {QUOTES_LOG_FILE}\nFile size: {QUOTES_LOG_FILE.stat().st_size}"
        return content
    except Exception as e:
        return f"Error reading log file: {e}"


@router.get("/debug")
def debug_logging():
    """Debug endpoint to check logging configuration."""
    from app.services.quotes_service import logger

    logger.info("TEST: Debug endpoint called")
    for handler in logger.handlers:
        handler.flush()

    return JSONResponse({
        "log_file": str(QUOTES_LOG_FILE),
        "log_file_exists": QUOTES_LOG_FILE.exists(),
        "parent_dir_exists": QUOTES_LOG_FILE.parent.exists(),
        "logger_name": logger.name,
        "logger_level": logging.getLevelName(logger.level),
        "handlers_count": len(logger.handlers),
        "handlers": [
            {
                "type": type(h).__name__,
                "level": logging.getLevelName(h.level),
            }
            for h in logger.handlers
        ],
    })

