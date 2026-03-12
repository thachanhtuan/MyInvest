from __future__ import annotations

from datetime import date

import pytest

from app.models import (
    Account,
    Asset,
    AssetValuation,
    BondInfo,
    CouponPayment,
    Quote,
    TargetAllocation,
    Transaction,
)


def make_account(db, acc_id="ACC1"):
    acc = Account(id=acc_id, name="Test", type="broker", broker_or_bank="TestBroker")
    db.add(acc)
    db.commit()
    return acc


def make_asset(db, ticker="SBER", asset_class="stock_ru"):
    a = Asset(ticker=ticker, name="Sberbank", asset_class=asset_class)
    db.add(a)
    db.commit()
    return a


def test_create_account(db):
    acc = make_account(db)
    result = db.query(Account).filter_by(id="ACC1").first()
    assert result is not None
    assert result.name == "Test"
    assert result.type == "broker"


def test_create_asset(db):
    a = make_asset(db)
    result = db.query(Asset).filter_by(ticker="SBER").first()
    assert result is not None
    assert result.asset_class == "stock_ru"


def test_create_bond_info(db):
    make_asset(db, ticker="OFZ26238", asset_class="bond_gov")
    bi = BondInfo(
        ticker="OFZ26238",
        face_value=1000.0,
        coupon_rate=7.1,
        coupon_frequency_year=2,
        coupon_frequency_day=182,
        maturity_date=date(2041, 5, 15),
        first_coupon_date=date(2024, 11, 15),
    )
    db.add(bi)
    db.commit()
    result = db.query(BondInfo).filter_by(ticker="OFZ26238").first()
    assert result.coupon_rate == 7.1
    assert result.maturity_date == date(2041, 5, 15)


def test_create_transaction(db):
    make_account(db)
    make_asset(db)
    tx = Transaction(
        date=date(2024, 1, 10),
        account_id="ACC1",
        ticker="SBER",
        tx_type="buy",
        quantity=100,
        price=260.0,
        commission=5.0,
        currency="RUB",
    )
    db.add(tx)
    db.commit()
    result = db.query(Transaction).first()
    assert result is not None
    assert result.quantity == 100
    assert result.price == 260.0


def test_create_quote(db):
    make_asset(db)
    q = Quote(ticker="SBER", date=date(2024, 6, 1), close_price=310.5, currency="RUB", source="MOEX")
    db.add(q)
    db.commit()
    result = db.query(Quote).first()
    assert result.close_price == 310.5


def test_create_coupon_payment(db):
    make_asset(db, ticker="BOND1", asset_class="bond_corp")
    cp = CouponPayment(ticker="BOND1", payment_date=date(2024, 3, 1), coupon_amount=42.38, currency="RUB")
    db.add(cp)
    db.commit()
    result = db.query(CouponPayment).first()
    assert result.coupon_amount == 42.38


def test_create_asset_valuation(db):
    make_asset(db)
    av = AssetValuation(date=date(2024, 6, 1), ticker="SBER", value=31050.0, currency="RUB")
    db.add(av)
    db.commit()
    result = db.query(AssetValuation).first()
    assert result.value == 31050.0


def test_create_target_allocation(db):
    ta = TargetAllocation(asset_class="stock_ru", target_pct=40.0)
    db.add(ta)
    db.commit()
    result = db.query(TargetAllocation).first()
    assert result.target_pct == 40.0


def test_account_has_transactions_relationship(db):
    make_account(db)
    make_asset(db)
    for i in range(3):
        db.add(Transaction(
            date=date(2024, 1, i + 1),
            account_id="ACC1",
            ticker="SBER",
            tx_type="buy",
            quantity=10,
            price=270.0,
        ))
    db.commit()
    acc = db.query(Account).filter_by(id="ACC1").first()
    assert len(acc.transactions) == 3
