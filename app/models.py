from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # broker|iis|deposit|savings
    broker_or_bank: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="account")


class Asset(Base):
    __tablename__ = "assets"

    ticker: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_class: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    isin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    bond_info: Mapped[Optional[BondInfo]] = relationship("BondInfo", back_populates="asset", uselist=False)
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="asset")
    quotes: Mapped[list[Quote]] = relationship("Quote", back_populates="asset")
    coupon_payments: Mapped[list[CouponPayment]] = relationship("CouponPayment", back_populates="asset")
    valuations: Mapped[list[AssetValuation]] = relationship("AssetValuation", back_populates="asset")


class BondInfo(Base):
    __tablename__ = "bond_info"

    ticker: Mapped[str] = mapped_column(String, ForeignKey("assets.ticker"), primary_key=True)
    face_value: Mapped[float] = mapped_column(Float, default=1000.0)
    base_currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    coupon_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coupon_sum: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coupon_currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    coupon_frequency_year: Mapped[int] = mapped_column(Integer, default=2)
    coupon_frequency_day: Mapped[int] = mapped_column(Integer, default=180)
    maturity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    offer_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    first_coupon_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_amortizing: Mapped[bool] = mapped_column(Boolean, default=False)

    asset: Mapped[Asset] = relationship("Asset", back_populates="bond_info")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    account_id: Mapped[str] = mapped_column(String, ForeignKey("accounts.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, ForeignKey("assets.ticker"), nullable=False)
    tx_type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nominal_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nominal_currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nkd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    commission: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    broker: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    account: Mapped[Account] = relationship("Account", back_populates="transactions")
    asset: Mapped[Asset] = relationship("Asset", back_populates="transactions")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, ForeignKey("assets.ticker"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    close_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    asset: Mapped[Asset] = relationship("Asset", back_populates="quotes")


class CouponPayment(Base):
    __tablename__ = "coupon_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, ForeignKey("assets.ticker"), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    coupon_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    asset: Mapped[Asset] = relationship("Asset", back_populates="coupon_payments")


class AssetValuation(Base):
    __tablename__ = "asset_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str] = mapped_column(String, ForeignKey("assets.ticker"), nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nominal_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nominal_currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    value_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    asset: Mapped[Asset] = relationship("Asset", back_populates="valuations")


class TargetAllocation(Base):
    __tablename__ = "target_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_class: Mapped[str] = mapped_column(String, nullable=False)
    target_pct: Mapped[float] = mapped_column(Float, nullable=False)
