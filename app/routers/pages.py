from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import templates
from app.models import Account, Asset, Transaction
from app.schemas import TX_TYPE_LABELS

router = APIRouter()


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/accounts")
def accounts_page(request: Request, db: Session = Depends(get_db)):
    accounts = db.query(Account).order_by(Account.broker_or_bank, Account.name).all()
    return templates.TemplateResponse(
        "accounts.html", {"request": request, "accounts": accounts}
    )


@router.get("/assets")
def assets_page(request: Request, db: Session = Depends(get_db)):
    assets = db.query(Asset).order_by(Asset.asset_class, Asset.name).all()
    return templates.TemplateResponse(
        "assets.html", {"request": request, "assets": assets}
    )


@router.get("/transactions")
def transactions_page(
    request: Request,
    account_id: str | None = None,
    ticker: str | None = None,
    tx_type: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Transaction).order_by(Transaction.date.desc())
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if ticker:
        query = query.filter(Transaction.ticker == ticker)
    if tx_type:
        query = query.filter(Transaction.tx_type == tx_type)
    txs = query.all()

    accounts = db.query(Account).order_by(Account.name).all()
    tickers = db.query(Asset.ticker, Asset.name).order_by(Asset.name).all()

    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": txs,
            "accounts": accounts,
            "tickers": tickers,
            "tx_type_labels": TX_TYPE_LABELS,
            "filter_account": account_id or "",
            "filter_ticker": ticker or "",
            "filter_tx_type": tx_type or "",
        },
    )


@router.get("/import")
def import_page(request: Request):
    return templates.TemplateResponse("import.html", {"request": request})
