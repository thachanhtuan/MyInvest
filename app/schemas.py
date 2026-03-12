from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ─── Account ──────────────────────────────────────────────────────────────────

class AccountBase(BaseModel):
    id: str
    name: str
    type: str
    broker_or_bank: str
    currency: Optional[str] = None
    notes: Optional[str] = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    broker_or_bank: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None


class AccountOut(AccountBase):
    model_config = ConfigDict(from_attributes=True)


# ─── Asset ────────────────────────────────────────────────────────────────────

class AssetBase(BaseModel):
    ticker: str
    name: str
    asset_class: str
    currency: Optional[str] = None
    isin: Optional[str] = None
    notes: Optional[str] = None
    target_min: Optional[float] = None
    target_max: Optional[float] = None
    target_pct: Optional[float] = None
    target_date: Optional[date] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_class: Optional[str] = None
    currency: Optional[str] = None
    isin: Optional[str] = None
    notes: Optional[str] = None
    target_min: Optional[float] = None
    target_max: Optional[float] = None
    target_pct: Optional[float] = None
    target_date: Optional[date] = None


class AssetOut(AssetBase):
    model_config = ConfigDict(from_attributes=True)


# ─── BondInfo ─────────────────────────────────────────────────────────────────

class BondInfoBase(BaseModel):
    ticker: str
    face_value: float = 1000.0
    base_currency: Optional[str] = None
    coupon_rate: Optional[float] = None
    coupon_sum: Optional[float] = None
    coupon_currency: Optional[str] = None
    coupon_frequency_year: int = 2
    coupon_frequency_day: int = 180
    maturity_date: Optional[date] = None
    offer_date: Optional[date] = None
    first_coupon_date: Optional[date] = None
    is_amortizing: bool = False


class BondInfoCreate(BondInfoBase):
    pass


class BondInfoOut(BondInfoBase):
    model_config = ConfigDict(from_attributes=True)


# ─── Transaction ──────────────────────────────────────────────────────────────

class TransactionBase(BaseModel):
    date: date
    account_id: str
    ticker: str
    tx_type: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    nominal_amount: Optional[float] = None
    nominal_currency: Optional[str] = None
    nkd: Optional[float] = None
    commission: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    broker: Optional[str] = None
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    account_id: Optional[str] = None
    ticker: Optional[str] = None
    tx_type: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    nominal_amount: Optional[float] = None
    nominal_currency: Optional[str] = None
    nkd: Optional[float] = None
    commission: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    broker: Optional[str] = None
    notes: Optional[str] = None


class TransactionOut(TransactionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ─── Quote ────────────────────────────────────────────────────────────────────

class QuoteBase(BaseModel):
    ticker: str
    date: date
    close_price: float
    currency: Optional[str] = None
    source: Optional[str] = None


class QuoteCreate(QuoteBase):
    pass


class QuoteOut(QuoteBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ─── CouponPayment ────────────────────────────────────────────────────────────

class CouponPaymentBase(BaseModel):
    ticker: str
    payment_date: date
    coupon_amount: float
    currency: Optional[str] = None


class CouponPaymentCreate(CouponPaymentBase):
    pass


class CouponPaymentOut(CouponPaymentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ─── AssetValuation ───────────────────────────────────────────────────────────

class AssetValuationBase(BaseModel):
    date: date
    ticker: str
    value: Optional[float] = None
    currency: Optional[str] = None
    nominal_value: Optional[float] = None
    nominal_currency: Optional[str] = None
    value_pct: Optional[float] = None


class AssetValuationCreate(AssetValuationBase):
    pass


class AssetValuationOut(AssetValuationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ─── TargetAllocation ─────────────────────────────────────────────────────────

class TargetAllocationBase(BaseModel):
    asset_class: str
    target_pct: float


class TargetAllocationCreate(TargetAllocationBase):
    pass


class TargetAllocationOut(TargetAllocationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
