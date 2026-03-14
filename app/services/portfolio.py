from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Account, Asset, AssetValuation, Transaction
from app.schemas import (
    ASSET_CLASS_LABELS,
    AccountSummary,
    AssetClassSummary,
    BrokerSummary,
    CurrencySummary,
    HoldingInfo,
    PortfolioSummary,
)


def _get_holdings(db: Session) -> list[HoldingInfo]:
    """Calculate holdings per (account_id, ticker) from transactions."""
    # Fetch all buy/sell/initial_balance transactions with tickers
    txs = (
        db.query(Transaction)
        .filter(
            Transaction.ticker.isnot(None),
            Transaction.tx_type.in_(["buy", "sell", "initial_balance"]),
        )
        .order_by(Transaction.date)
        .all()
    )

    # Build account and asset lookup
    accounts_map: dict[str, Account] = {
        a.id: a for a in db.query(Account).all()
    }
    assets_map: dict[str, Asset] = {
        a.ticker: a for a in db.query(Asset).all()
    }

    # Latest valuations per ticker (most recent date)
    latest_vals: dict[str, AssetValuation] = {}
    subq = (
        db.query(
            AssetValuation.ticker,
            func.max(AssetValuation.date).label("max_date"),
        )
        .group_by(AssetValuation.ticker)
        .subquery()
    )
    vals = (
        db.query(AssetValuation)
        .join(
            subq,
            (AssetValuation.ticker == subq.c.ticker)
            & (AssetValuation.date == subq.c.max_date),
        )
        .all()
    )
    for v in vals:
        latest_vals[v.ticker] = v

    # Aggregate per (account_id, ticker)
    key_quantity: dict[tuple[str, str], float] = defaultdict(float)
    key_invested: dict[tuple[str, str], float] = defaultdict(float)
    key_buy_qty: dict[tuple[str, str], float] = defaultdict(float)
    key_buy_cost: dict[tuple[str, str], float] = defaultdict(float)

    for tx in txs:
        key = (tx.account_id, tx.ticker)
        qty = tx.quantity or 0.0
        total = tx.total_amount or 0.0

        if tx.tx_type in ("buy", "initial_balance"):
            key_quantity[key] += qty
            key_invested[key] += total
            key_buy_qty[key] += qty
            key_buy_cost[key] += total
        elif tx.tx_type == "sell":
            key_quantity[key] -= qty
            key_invested[key] -= total

    holdings: list[HoldingInfo] = []
    for (account_id, ticker), quantity in key_quantity.items():
        if quantity <= 0:
            continue

        account = accounts_map.get(account_id)
        asset = assets_map.get(ticker)
        if not account or not asset:
            continue

        total_invested = key_invested[(account_id, ticker)]
        buy_qty = key_buy_qty[(account_id, ticker)]
        avg_price = key_buy_cost[(account_id, ticker)] / buy_qty if buy_qty else 0.0

        # Current value from latest valuation
        val = latest_vals.get(ticker)
        if val and val.value and val.value > 0:
            # Proportional: if valuation is for total position,
            # we need to figure out what share this account holds
            # For simplicity, use total valuation split by account share
            total_qty_for_ticker = sum(
                q for (a, t), q in key_quantity.items() if t == ticker and q > 0
            )
            if total_qty_for_ticker > 0:
                current_value = val.value * (quantity / total_qty_for_ticker)
            else:
                current_value = total_invested
        else:
            current_value = total_invested

        profit_loss = current_value - total_invested
        profit_loss_pct = (profit_loss / total_invested * 100) if total_invested else 0.0

        holdings.append(
            HoldingInfo(
                account_id=account_id,
                account_name=account.name,
                broker=account.broker_or_bank,
                ticker=ticker,
                asset_name=asset.name,
                asset_class=asset.asset_class,
                currency=asset.currency,
                quantity=quantity,
                avg_price=round(avg_price, 2),
                total_invested=round(total_invested, 2),
                current_value=round(current_value, 2),
                profit_loss=round(profit_loss, 2),
                profit_loss_pct=round(profit_loss_pct, 2),
            )
        )

    return holdings


def get_portfolio_summary(db: Session) -> PortfolioSummary:
    holdings = _get_holdings(db)

    # All accounts lookup (needed for both holdings-based and cash-only accounts)
    all_accounts: dict[str, Account] = {a.id: a for a in db.query(Account).all()}

    # Deposited per account: sum total_amount for initial_balance + deposit_in
    deposit_txs = (
        db.query(Transaction)
        .filter(Transaction.tx_type.in_(["initial_balance", "deposit_in"]))
        .all()
    )
    deposited_map: dict[str, float] = defaultdict(float)
    for tx in deposit_txs:
        deposited_map[tx.account_id] += tx.total_amount or 0.0

    # Cash balance per account: deposit_in + initial_balance + interest − deposit_out
    cash_flow_txs = (
        db.query(Transaction)
        .filter(Transaction.tx_type.in_(["deposit_in", "deposit_out", "interest", "initial_balance"]))
        .all()
    )
    cash_balance_map: dict[str, float] = defaultdict(float)
    for tx in cash_flow_txs:
        if tx.tx_type == "deposit_out":
            cash_balance_map[tx.account_id] -= tx.total_amount or 0.0
        else:
            cash_balance_map[tx.account_id] += tx.total_amount or 0.0

    # By account: start from holdings
    acc_map: dict[str, dict] = {}
    for h in holdings:
        if h.account_id not in acc_map:
            acc = all_accounts.get(h.account_id)
            acc_map[h.account_id] = {
                "account_id": h.account_id,
                "account_name": h.account_name,
                "broker": h.broker,
                "account_type": acc.type if acc else "broker",
                "total_invested": 0.0,
                "current_value": 0.0,
            }
        acc_map[h.account_id]["total_invested"] += h.total_invested
        acc_map[h.account_id]["current_value"] += h.current_value

    # Add cash-only accounts (savings, deposits) that have no securities holdings
    for account_id, acc in all_accounts.items():
        if account_id in acc_map:
            continue
        cash_val = cash_balance_map[account_id]
        if cash_val == 0:
            continue
        acc_map[account_id] = {
            "account_id": account_id,
            "account_name": acc.name,
            "broker": acc.broker_or_bank,
            "account_type": acc.type,
            "total_invested": deposited_map[account_id],
            "current_value": cash_val,
        }

    # Portfolio totals include all accounts (securities + cash)
    total_invested = sum(d["total_invested"] for d in acc_map.values())
    current_value = sum(d["current_value"] for d in acc_map.values())
    profit_loss = current_value - total_invested
    profit_loss_pct = (profit_loss / total_invested * 100) if total_invested else 0.0

    by_account = []
    for data in acc_map.values():
        inv = data["total_invested"]
        val = data["current_value"]
        pl = val - inv
        by_account.append(
            AccountSummary(
                account_id=data["account_id"],
                account_name=data["account_name"],
                account_type=data["account_type"],
                broker=data["broker"],
                total_deposited=round(deposited_map[data["account_id"]], 2),
                total_invested=round(inv, 2),
                current_value=round(val, 2),
                profit_loss=round(pl, 2),
                profit_loss_pct=round(pl / inv * 100 if inv else 0, 2),
                share_pct=round(val / current_value * 100 if current_value else 0, 2),
            )
        )
    by_account.sort(key=lambda x: x.current_value, reverse=True)

    # By broker
    broker_map: dict[str, dict] = {}
    for a in by_account:
        if a.broker not in broker_map:
            broker_map[a.broker] = {"total_invested": 0.0, "current_value": 0.0}
        broker_map[a.broker]["total_invested"] += a.total_invested
        broker_map[a.broker]["current_value"] += a.current_value

    by_broker = []
    for broker, data in broker_map.items():
        inv = data["total_invested"]
        val = data["current_value"]
        pl = val - inv
        by_broker.append(
            BrokerSummary(
                broker=broker,
                total_invested=round(inv, 2),
                current_value=round(val, 2),
                profit_loss=round(pl, 2),
                profit_loss_pct=round(pl / inv * 100 if inv else 0, 2),
                share_pct=round(val / current_value * 100 if current_value else 0, 2),
            )
        )
    by_broker.sort(key=lambda x: x.current_value, reverse=True)

    # By asset class
    class_map: dict[str, float] = defaultdict(float)
    for h in holdings:
        class_map[h.asset_class] += h.current_value

    by_asset_class = []
    for ac, val in class_map.items():
        by_asset_class.append(
            AssetClassSummary(
                asset_class=ac,
                label=ASSET_CLASS_LABELS.get(ac, ac),
                current_value=round(val, 2),
                share_pct=round(val / current_value * 100 if current_value else 0, 2),
            )
        )
    by_asset_class.sort(key=lambda x: x.current_value, reverse=True)

    # By currency
    curr_map: dict[str, float] = defaultdict(float)
    for h in holdings:
        curr_map[h.currency] += h.current_value

    by_currency = []
    for curr, val in curr_map.items():
        by_currency.append(
            CurrencySummary(
                currency=curr,
                current_value=round(val, 2),
                share_pct=round(val / current_value * 100 if current_value else 0, 2),
            )
        )
    by_currency.sort(key=lambda x: x.current_value, reverse=True)

    return PortfolioSummary(
        total_invested=round(total_invested, 2),
        current_value=round(current_value, 2),
        profit_loss=round(profit_loss, 2),
        profit_loss_pct=round(profit_loss_pct, 2),
        by_account=by_account,
        by_broker=by_broker,
        by_asset_class=by_asset_class,
        by_currency=by_currency,
        holdings=sorted(holdings, key=lambda h: h.current_value, reverse=True),
    )
