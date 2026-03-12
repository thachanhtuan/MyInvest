from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Asset, AssetValuation, BondInfo, Quote, Transaction


def _effective_cost(tx: Transaction) -> float:
    """Return the cash outflow (cost) for a buy transaction."""
    if tx.total_amount is not None:
        return abs(tx.total_amount)
    qty = tx.quantity or 0.0
    price = tx.price or 0.0
    amount = tx.amount if tx.amount is not None else qty * price
    nkd = tx.nkd or 0.0
    commission = tx.commission or 0.0
    return abs(amount) + nkd + commission


def get_holdings(
    db: Session,
    account_id: Optional[str] = None,
    broker: Optional[str] = None,
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Process transactions chronologically and compute holdings.
    Returns: {ticker: {quantity, avg_cost, total_cost, account_id, currency}}
    """
    q = db.query(Transaction).order_by(Transaction.date, Transaction.id)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if broker:
        q = q.filter(Transaction.broker == broker)
    if as_of_date:
        q = q.filter(Transaction.date <= as_of_date)

    holdings: Dict[str, Dict[str, Any]] = {}

    for tx in q.all():
        ticker = tx.ticker
        if ticker not in holdings:
            holdings[ticker] = {
                "quantity": 0.0,
                "avg_cost": 0.0,
                "total_cost": 0.0,
                "account_id": tx.account_id,
                "currency": tx.currency,
                "ticker": ticker,
            }

        h = holdings[ticker]

        if tx.tx_type == "initial_balance":
            qty = tx.quantity or 0.0
            cost = _effective_cost(tx) if qty > 0 else 0.0
            h["quantity"] = qty
            h["total_cost"] = cost
            h["avg_cost"] = cost / qty if qty else 0.0

        elif tx.tx_type == "buy":
            qty = tx.quantity or 0.0
            cost = _effective_cost(tx)
            new_qty = h["quantity"] + qty
            new_cost = h["total_cost"] + cost
            h["quantity"] = new_qty
            h["total_cost"] = new_cost
            h["avg_cost"] = new_cost / new_qty if new_qty else 0.0

        elif tx.tx_type == "sell":
            qty = abs(tx.quantity or 0.0)
            if h["quantity"] > 0 and qty > 0:
                sell_ratio = min(qty / h["quantity"], 1.0)
                h["total_cost"] -= h["total_cost"] * sell_ratio
            h["quantity"] = max(h["quantity"] - qty, 0.0)
            h["avg_cost"] = h["total_cost"] / h["quantity"] if h["quantity"] else 0.0

        elif tx.tx_type in ("maturity", "amortization"):
            qty = abs(tx.quantity or 0.0)
            if h["quantity"] > 0 and qty > 0:
                sell_ratio = min(qty / h["quantity"], 1.0)
                h["total_cost"] -= h["total_cost"] * sell_ratio
            h["quantity"] = max(h["quantity"] - qty, 0.0)
            h["avg_cost"] = h["total_cost"] / h["quantity"] if h["quantity"] else 0.0

    # Remove zero-quantity positions
    return {t: v for t, v in holdings.items() if v["quantity"] > 1e-9}


def _latest_quote_price(db: Session, ticker: str, as_of_date: Optional[date] = None) -> Optional[float]:
    """Return the most recent per-unit close price from quotes."""
    q = db.query(Quote).filter(Quote.ticker == ticker)
    if as_of_date:
        q = q.filter(Quote.date <= as_of_date)
    quote = q.order_by(Quote.date.desc()).first()
    return quote.close_price if quote else None


def _latest_valuation(
    db: Session, ticker: str, as_of_date: Optional[date] = None
) -> Optional[AssetValuation]:
    """Return the most recent AssetValuation record (total portfolio value, not per-unit)."""
    v = db.query(AssetValuation).filter(AssetValuation.ticker == ticker)
    if as_of_date:
        v = v.filter(AssetValuation.date <= as_of_date)
    return v.order_by(AssetValuation.date.desc()).first()


def get_portfolio_value(
    db: Session,
    holdings: Dict[str, Any],
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for ticker, h in holdings.items():
        qty = h["quantity"]
        avg_cost = h["avg_cost"]
        total_cost = h["total_cost"]

        # Try per-unit quote price first
        price = _latest_quote_price(db, ticker, as_of_date)
        if price is not None:
            market_value = qty * price
        else:
            # Fallback: AssetValuation.value is the TOTAL value reported by the broker
            val = _latest_valuation(db, ticker, as_of_date)
            if val is not None and val.value is not None:
                market_value = val.value
                price = val.value / qty if qty else None
            elif val is not None and val.value_pct is not None:
                # Bond-style: value_pct is % of face value
                bond = db.query(BondInfo).filter(BondInfo.ticker == ticker).first()
                face = bond.face_value if bond else 1000.0
                price = face * val.value_pct / 100
                market_value = qty * price
            else:
                market_value = None

        unrealized_pnl = (market_value - total_cost) if market_value is not None else None
        unrealized_pnl_pct = (
            unrealized_pnl / total_cost * 100 if (unrealized_pnl is not None and total_cost) else None
        )
        result[ticker] = {
            "ticker": ticker,
            "quantity": qty,
            "avg_cost": avg_cost,
            "total_cost": total_cost,
            "price": price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "account_id": h.get("account_id"),
            "currency": h.get("currency"),
        }
    return result


def get_portfolio_return(
    db: Session,
    account_id: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Any]:
    holdings = get_holdings(db, account_id=account_id, as_of_date=to_date)
    pv = get_portfolio_value(db, holdings, as_of_date=to_date)

    total_invested = sum(v["total_cost"] for v in pv.values())
    current_value = sum(v["market_value"] for v in pv.values() if v["market_value"] is not None)

    # Also add value for positions without market price
    for v in pv.values():
        if v["market_value"] is None:
            current_value += v["total_cost"]

    total_return = current_value - total_invested
    total_return_pct = (total_return / total_invested * 100) if total_invested else 0.0

    return {
        "total_invested": total_invested,
        "current_value": current_value,
        "total_return": total_return,
        "total_return_pct": total_return_pct,
    }


def get_asset_allocation(
    db: Session,
    account_id: Optional[str] = None,
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    holdings = get_holdings(db, account_id=account_id, as_of_date=as_of_date)
    pv = get_portfolio_value(db, holdings, as_of_date=as_of_date)

    class_values: Dict[str, float] = defaultdict(float)
    for ticker, v in pv.items():
        asset = db.query(Asset).filter(Asset.ticker == ticker).first()
        asset_class = asset.asset_class if asset else "other"
        value = v["market_value"] if v["market_value"] is not None else v["total_cost"]
        class_values[asset_class] += value

    total = sum(class_values.values())
    result: Dict[str, Any] = {}
    for ac, val in class_values.items():
        result[ac] = {
            "value": val,
            "pct": (val / total * 100) if total else 0.0,
        }
    return result


def get_bond_ladder(
    db: Session,
    account_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    holdings = get_holdings(db, account_id=account_id)
    rows: List[Dict[str, Any]] = []
    grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

    for ticker, h in holdings.items():
        bond = db.query(BondInfo).filter(BondInfo.ticker == ticker).first()
        if not bond:
            continue
        qty = h["quantity"]

        if bond.maturity_date:
            year = bond.maturity_date.year
            amount = bond.face_value * qty
            grouped[year].append(
                {
                    "date": bond.maturity_date.isoformat(),
                    "ticker": ticker,
                    "type": "maturity",
                    "amount": amount,
                    "year": year,
                }
            )

        if bond.offer_date:
            year = bond.offer_date.year
            amount = bond.face_value * qty
            grouped[year].append(
                {
                    "date": bond.offer_date.isoformat(),
                    "ticker": ticker,
                    "type": "offer",
                    "amount": amount,
                    "year": year,
                }
            )

    for year in sorted(grouped.keys()):
        rows.extend(sorted(grouped[year], key=lambda x: x["date"]))

    return rows


def get_coupon_schedule(
    db: Session,
    account_id: Optional[str] = None,
    months_ahead: int = 12,
) -> List[Dict[str, Any]]:
    holdings = get_holdings(db, account_id=account_id)
    today = date.today()
    month = today.month + months_ahead
    year = today.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    schedule: List[Dict[str, Any]] = []

    for ticker, h in holdings.items():
        bond = db.query(BondInfo).filter(BondInfo.ticker == ticker).first()
        if not bond:
            continue
        if not bond.first_coupon_date:
            continue

        qty = h["quantity"]
        coupon_amount_per_bond = bond.coupon_sum or 0.0
        if not coupon_amount_per_bond and bond.coupon_rate and bond.face_value:
            coupon_amount_per_bond = bond.face_value * bond.coupon_rate / 100 / bond.coupon_frequency_year

        period_days = bond.coupon_frequency_day or int(365 / max(bond.coupon_frequency_year, 1))
        payment_date = bond.first_coupon_date

        # Walk forward to the first future payment
        cutoff = bond.maturity_date or end_date
        while payment_date <= today:
            payment_date = payment_date + timedelta(days=period_days)

        while payment_date <= end_date and payment_date <= cutoff:
            schedule.append(
                {
                    "date": payment_date.isoformat(),
                    "ticker": ticker,
                    "amount": coupon_amount_per_bond * qty,
                    "currency": bond.coupon_currency or "RUB",
                }
            )
            payment_date = payment_date + timedelta(days=period_days)

    schedule.sort(key=lambda x: x["date"])
    return schedule
