from __future__ import annotations

from datetime import date

import pytest

from app.models import Account, Asset, AssetValuation, BondInfo, Quote, Transaction
from app.services.portfolio import (
    get_asset_allocation,
    get_bond_ladder,
    get_coupon_schedule,
    get_holdings,
    get_portfolio_return,
    get_portfolio_value,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _setup_base(db):
    acc = Account(id="ACC1", name="Test", type="broker", broker_or_bank="Broker")
    db.add(acc)
    db.add(Asset(ticker="SBER", name="Sberbank", asset_class="stock_ru", currency="RUB"))
    db.add(Asset(ticker="LKOH", name="Lukoil", asset_class="stock_ru", currency="RUB"))
    db.add(Asset(ticker="OFZ", name="OFZ26238", asset_class="bond_gov", currency="RUB"))
    db.commit()


def _add_tx(db, ticker, tx_type, qty, price, amount=None, total_amount=None,
             nkd=None, commission=None, acc="ACC1", d=date(2024, 1, 1)):
    db.add(Transaction(
        date=d,
        account_id=acc,
        ticker=ticker,
        tx_type=tx_type,
        quantity=qty,
        price=price,
        amount=amount,
        nkd=nkd,
        commission=commission,
        total_amount=total_amount,
        currency="RUB",
    ))
    db.commit()


# ─── Holdings tests ───────────────────────────────────────────────────────────

def test_buy_creates_holding(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 260.0, commission=5.0)
    h = get_holdings(db)
    assert "SBER" in h
    assert h["SBER"]["quantity"] == 100.0


def test_buy_avg_cost(db):
    _setup_base(db)
    # First buy: 100 shares @ 260, commission 5 → cost = 26005
    _add_tx(db, "SBER", "buy", 100, 260.0, commission=5.0, d=date(2024, 1, 1))
    # Second buy: 50 shares @ 300, commission 3 → cost = 15003
    _add_tx(db, "SBER", "buy", 50, 300.0, commission=3.0, d=date(2024, 2, 1))
    h = get_holdings(db)
    assert h["SBER"]["quantity"] == 150.0
    expected_cost = (100 * 260 + 5) + (50 * 300 + 3)
    assert abs(h["SBER"]["total_cost"] - expected_cost) < 0.01


def test_sell_reduces_quantity(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 260.0, d=date(2024, 1, 1))
    _add_tx(db, "SBER", "sell", 40, 300.0, d=date(2024, 3, 1))
    h = get_holdings(db)
    assert h["SBER"]["quantity"] == 60.0


def test_sell_all_removes_holding(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 260.0, d=date(2024, 1, 1))
    _add_tx(db, "SBER", "sell", 100, 300.0, d=date(2024, 3, 1))
    h = get_holdings(db)
    assert "SBER" not in h


def test_initial_balance(db):
    _setup_base(db)
    _add_tx(db, "SBER", "initial_balance", 200, 250.0, total_amount=50000.0)
    h = get_holdings(db)
    assert h["SBER"]["quantity"] == 200.0
    assert h["SBER"]["total_cost"] == 50000.0


def test_maturity_reduces_quantity(db):
    _setup_base(db)
    _add_tx(db, "OFZ", "buy", 10, 950.0, d=date(2024, 1, 1))
    _add_tx(db, "OFZ", "maturity", 10, 1000.0, d=date(2024, 12, 1))
    h = get_holdings(db)
    assert "OFZ" not in h


def test_as_of_date_filter(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 260.0, d=date(2024, 1, 1))
    _add_tx(db, "SBER", "buy", 50, 280.0, d=date(2024, 6, 1))
    h = get_holdings(db, as_of_date=date(2024, 3, 1))
    assert h["SBER"]["quantity"] == 100.0


# ─── Portfolio value tests ────────────────────────────────────────────────────

def test_portfolio_value_with_quote(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 260.0)
    db.add(Quote(ticker="SBER", date=date(2024, 6, 1), close_price=310.0, currency="RUB"))
    db.commit()
    h = get_holdings(db)
    pv = get_portfolio_value(db, h)
    assert abs(pv["SBER"]["market_value"] - 31000.0) < 0.01


def test_portfolio_value_fallback_valuation(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 260.0)
    # AssetValuation.value is the TOTAL portfolio value (not per-unit)
    db.add(AssetValuation(date=date(2024, 6, 1), ticker="SBER", value=32000.0, currency="RUB"))
    db.commit()
    h = get_holdings(db)
    pv = get_portfolio_value(db, h)
    # No quote → fallback to valuation. market_value = val.value = 32000.0 (total, not qty * val.value)
    assert abs(pv["SBER"]["market_value"] - 32000.0) < 0.01


def test_unrealized_pnl(db):
    _setup_base(db)
    # Buy 100 @ 260 commission 0 → cost = 26000
    _add_tx(db, "SBER", "buy", 100, 260.0)
    db.add(Quote(ticker="SBER", date=date(2024, 6, 1), close_price=310.0))
    db.commit()
    h = get_holdings(db)
    pv = get_portfolio_value(db, h)
    # market_value = 31000, cost = 26000, pnl = 5000
    assert abs(pv["SBER"]["unrealized_pnl"] - 5000.0) < 0.01


# ─── Allocation tests ─────────────────────────────────────────────────────────

def test_asset_allocation(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 100.0)
    _add_tx(db, "LKOH", "buy", 10, 700.0)
    db.add(Quote(ticker="SBER", date=date(2024, 6, 1), close_price=100.0))
    db.add(Quote(ticker="LKOH", date=date(2024, 6, 1), close_price=700.0))
    db.commit()
    alloc = get_asset_allocation(db)
    assert "stock_ru" in alloc
    assert abs(alloc["stock_ru"]["pct"] - 100.0) < 0.01


# ─── Bond ladder tests ────────────────────────────────────────────────────────

def test_bond_ladder(db):
    _setup_base(db)
    _add_tx(db, "OFZ", "buy", 10, 950.0)
    db.add(BondInfo(
        ticker="OFZ",
        face_value=1000.0,
        maturity_date=date(2041, 5, 15),
        coupon_frequency_year=2,
        coupon_frequency_day=182,
    ))
    db.commit()
    ladder = get_bond_ladder(db)
    assert len(ladder) > 0
    assert ladder[0]["ticker"] == "OFZ"
    assert ladder[0]["amount"] == 10 * 1000.0


# ─── Coupon schedule tests ────────────────────────────────────────────────────

def test_coupon_schedule_projects_payments(db):
    _setup_base(db)
    _add_tx(db, "OFZ", "buy", 5, 950.0)
    db.add(BondInfo(
        ticker="OFZ",
        face_value=1000.0,
        coupon_sum=35.0,
        coupon_currency="RUB",
        coupon_frequency_year=2,
        coupon_frequency_day=182,
        first_coupon_date=date(2024, 1, 15),
        maturity_date=date(2041, 5, 15),
    ))
    db.commit()
    schedule = get_coupon_schedule(db, months_ahead=12)
    assert isinstance(schedule, list)
    # Each projected payment should be 35 * 5 = 175
    for entry in schedule:
        assert abs(entry["amount"] - 175.0) < 0.01


# ─── Portfolio return tests ───────────────────────────────────────────────────

def test_portfolio_return(db):
    _setup_base(db)
    _add_tx(db, "SBER", "buy", 100, 260.0)
    db.add(Quote(ticker="SBER", date=date(2024, 6, 1), close_price=310.0))
    db.commit()
    ret = get_portfolio_return(db)
    assert ret["total_invested"] == 26000.0
    assert abs(ret["current_value"] - 31000.0) < 0.01
    assert abs(ret["total_return"] - 5000.0) < 0.01
    assert abs(ret["total_return_pct"] - (5000 / 26000 * 100)) < 0.01
