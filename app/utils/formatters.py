from __future__ import annotations

import datetime
import locale


def format_money(value: float | None, currency: str = "RUB") -> str:
    if value is None:
        return "—"
    symbols = {"RUB": "\u20bd", "USD": "$", "EUR": "\u20ac", "CNY": "\u00a5"}
    symbol = symbols.get(currency, currency)
    formatted = f"{value:,.2f}".replace(",", "\u00a0")
    return f"{formatted} {symbol}"


def format_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}%"


def format_date(value: datetime.date | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def profit_class(value: float | None) -> str:
    if value is None or value == 0:
        return ""
    return "text-success" if value > 0 else "text-danger"
