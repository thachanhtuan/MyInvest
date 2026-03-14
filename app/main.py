from __future__ import annotations

import contextlib
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_LOG_FILE, BASE_DIR
from app.utils.formatters import format_date, format_money, format_pct, profit_class
from app.utils.logging_util import setup_file_handler


# App-level logger
logger = logging.getLogger("app")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Start up: configure logging. Shutdown: flush logs."""
    # Configure app-level logging
    setup_file_handler(logger, APP_LOG_FILE)
    logger.info("=" * 80)
    logger.info("MyInvest application started")
    logger.info("=" * 80)

    yield

    # Shutdown: flush all handlers
    logger.info("=" * 80)
    logger.info("MyInvest application shutting down")
    logger.info("=" * 80)
    for handler in logger.handlers:
        handler.flush()


app = FastAPI(title="MyInvest", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.filters["money"] = format_money
templates.env.filters["pct"] = format_pct
templates.env.filters["fdate"] = format_date
templates.env.globals["profit_class"] = profit_class

# Import routers
from app.routers import pages, import_export, accounts, assets, transactions, analytics, quotes  # noqa: E402

app.include_router(pages.router)
app.include_router(import_export.router)
app.include_router(accounts.router)
app.include_router(assets.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(quotes.router)
