from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import create_tables
from app.routers import (
    accounts,
    analytics,
    assets,
    coupons,
    import_export,
    quotes,
    transactions,
    valuations,
)

BASE_DIR = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="MyInvest", version="1.0.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ─── API routers ──────────────────────────────────────────────────────────────

app.include_router(accounts.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(quotes.router, prefix="/api")
app.include_router(coupons.router, prefix="/api")
app.include_router(valuations.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(import_export.router, prefix="/api")


# ─── Page routes ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/accounts", response_class=HTMLResponse)
async def page_accounts(request: Request):
    return templates.TemplateResponse("accounts.html", {"request": request})


@app.get("/assets", response_class=HTMLResponse)
async def page_assets(request: Request):
    return templates.TemplateResponse("assets.html", {"request": request})


@app.get("/transactions", response_class=HTMLResponse)
async def page_transactions(request: Request):
    return templates.TemplateResponse("transactions.html", {"request": request})


@app.get("/analytics", response_class=HTMLResponse)
async def page_analytics(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})


@app.get("/bonds", response_class=HTMLResponse)
async def page_bonds(request: Request):
    return templates.TemplateResponse("bonds.html", {"request": request})


@app.get("/import-export", response_class=HTMLResponse)
async def page_import_export(request: Request):
    return templates.TemplateResponse("import_export.html", {"request": request})


# ─── Startup ──────────────────────────────────────────────────────────────────
