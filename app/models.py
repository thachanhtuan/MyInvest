from __future__ import annotations

import datetime

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    broker_or_bank: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="RUB")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")


class Asset(Base):
    __tablename__ = "assets"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_class: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="RUB")
    isin: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    target_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)

    bond_info: Mapped[BondInfo | None] = relationship(back_populates="asset", uselist=False)
    transactions: Mapped[list[Transaction]] = relationship(back_populates="asset")
    valuations: Mapped[list[AssetValuation]] = relationship(back_populates="asset")


class BondInfo(Base):
    __tablename__ = "bond_info"

    ticker: Mapped[str] = mapped_column(
        String, ForeignKey("assets.ticker"), primary_key=True
    )
    face_value: Mapped[float] = mapped_column(Float, default=1000)
    base_currency: Mapped[str | None] = mapped_column(String, nullable=True)
    coupon_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    coupon_sum: Mapped[float | None] = mapped_column(Float, nullable=True)
    coupon_currency: Mapped[str | None] = mapped_column(String, nullable=True)
    coupon_frequency_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coupon_frequency_day: Mapped[int | None] = mapped_column(Integer, default=30)
    maturity_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    offer_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    first_coupon_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    is_amortizing: Mapped[bool] = mapped_column(Boolean, default=False)

    asset: Mapped[Asset] = relationship(back_populates="bond_info")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    account_id: Mapped[str] = mapped_column(
        String, ForeignKey("accounts.id"), nullable=False
    )
    ticker: Mapped[str | None] = mapped_column(
        String, ForeignKey("assets.ticker"), nullable=True
    )
    tx_type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    nominal_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    nominal_currency: Mapped[str | None] = mapped_column(String, nullable=True)
    nkd: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="RUB")
    broker: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    account: Mapped[Account] = relationship(back_populates="transactions")
    asset: Mapped[Asset | None] = relationship(back_populates="transactions")


class AssetValuation(Base):
    __tablename__ = "asset_valuations"
    __table_args__ = (
        UniqueConstraint("date", "ticker", name="uq_valuation_date_ticker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(
        String, ForeignKey("assets.ticker"), nullable=False
    )
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)
    nominal_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    nominal_currency: Mapped[str | None] = mapped_column(String, nullable=True)
    value_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    asset: Mapped[Asset] = relationship(back_populates="valuations")


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(4), nullable=True)


class CurrencyRate(Base):
    __tablename__ = "currency_rates"
    __table_args__ = (
        UniqueConstraint("date", "currency", name="uq_currency_rate_date_currency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
