from __future__ import annotations

import datetime
from enum import Enum

from pydantic import BaseModel


class AccountType(str, Enum):
    broker = "broker"
    iis = "iis"
    deposit = "deposit"
    savings = "savings"


class AssetClass(str, Enum):
    stock_ru = "stock_ru"
    stock_foreign = "stock_foreign"
    bond_gov = "bond_gov"
    bond_corp = "bond_corp"
    bond_muni = "bond_muni"
    etf = "etf"
    deposit = "deposit"
    cash = "cash"
    gold = "gold"
    other = "other"


ASSET_CLASS_LABELS: dict[str, str] = {
    "stock_ru": "Российские акции",
    "stock_foreign": "Иностранные акции",
    "bond_gov": "Гос. облигации",
    "bond_corp": "Корп. облигации",
    "bond_muni": "Муницип. облигации",
    "etf": "Фонды (ETF/БПИФ)",
    "deposit": "Депозиты",
    "cash": "Денежные средства",
    "gold": "Золото",
    "other": "Прочее",
}


class TransactionType(str, Enum):
    buy = "buy"
    sell = "sell"
    dividend = "dividend"
    coupon = "coupon"
    amortization = "amortization"
    maturity = "maturity"
    commission = "commission"
    tax = "tax"
    deposit_in = "deposit_in"
    deposit_out = "deposit_out"
    interest = "interest"
    initial_balance = "initial_balance"
    other = "other"


TX_TYPE_LABELS: dict[str, str] = {
    "buy": "Покупка",
    "sell": "Продажа",
    "dividend": "Дивиденд",
    "coupon": "Купон",
    "amortization": "Амортизация",
    "maturity": "Погашение",
    "commission": "Комиссия",
    "tax": "Налог",
    "deposit_in": "Пополнение",
    "deposit_out": "Вывод",
    "interest": "Проценты",
    "initial_balance": "Нач. баланс",
    "other": "Прочее",
}


class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    CNY = "CNY"


# --- Account schemas ---


class AccountRead(BaseModel):
    id: str
    name: str
    type: str
    broker_or_bank: str
    currency: str
    notes: str | None = None

    model_config = {"from_attributes": True}


# --- Asset schemas ---


class AssetRead(BaseModel):
    ticker: str
    name: str
    asset_class: str
    currency: str
    isin: str | None = None
    notes: str | None = None
    target_min: float | None = None
    target_max: float | None = None
    target_pct: float | None = None
    target_date: datetime.date | None = None
    exchange: str | None = None

    model_config = {"from_attributes": True}


# --- BondInfo schemas ---


class BondInfoRead(BaseModel):
    ticker: str
    face_value: float
    base_currency: str | None = None
    coupon_rate: float | None = None
    coupon_sum: float | None = None
    coupon_currency: str | None = None
    coupon_frequency_year: int | None = None
    coupon_frequency_day: int | None = None
    maturity_date: datetime.date | None = None
    offer_date: datetime.date | None = None
    first_coupon_date: datetime.date | None = None
    is_amortizing: bool = False

    model_config = {"from_attributes": True}


# --- Transaction schemas ---


class TransactionRead(BaseModel):
    id: int
    date: datetime.date
    account_id: str
    ticker: str | None = None
    tx_type: str
    quantity: float | None = None
    price: float | None = None
    amount: float | None = None
    nominal_amount: float | None = None
    nominal_currency: str | None = None
    nkd: float | None = None
    commission: float | None = None
    total_amount: float | None = None
    currency: str
    broker: str | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


# --- AssetValuation schemas ---


class AssetValuationRead(BaseModel):
    id: int
    date: datetime.date
    ticker: str
    value: float | None = None
    currency: str | None = None
    nominal_value: float | None = None
    nominal_currency: str | None = None
    value_pct: float | None = None

    model_config = {"from_attributes": True}


# --- Analytics schemas ---


class HoldingInfo(BaseModel):
    account_id: str
    account_name: str
    broker: str
    ticker: str
    asset_name: str
    asset_class: str
    currency: str
    quantity: float
    avg_price: float
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_pct: float


class AccountSummary(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    broker: str
    total_deposited: float
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_pct: float
    share_pct: float


class BrokerSummary(BaseModel):
    broker: str
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_pct: float
    share_pct: float


class AssetClassSummary(BaseModel):
    asset_class: str
    label: str
    current_value: float
    share_pct: float


class CurrencySummary(BaseModel):
    currency: str
    current_value: float
    share_pct: float


class PortfolioSummary(BaseModel):
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_pct: float
    by_account: list[AccountSummary]
    by_broker: list[BrokerSummary]
    by_asset_class: list[AssetClassSummary]
    by_currency: list[CurrencySummary]
    holdings: list[HoldingInfo]


class QuoteResult(BaseModel):
    updated: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = []
    log_file: str | None = None


class CurrencyRateResult(BaseModel):
    date: datetime.date | None = None
    updated: int = 0
    failed: int = 0
    errors: list[str] = []
    log_file: str | None = None


class ImportResult(BaseModel):
    accounts: int = 0
    assets: int = 0
    bonds: int = 0
    transactions: int = 0
    valuations: int = 0
    errors: list[str] = []
