from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import httpx


MOEX_STOCK_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}.json?iss.meta=off"
)
MOEX_BOND_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/bonds/securities/{ticker}.json?iss.meta=off"
)

BOND_ASSET_CLASSES = {"bond_gov", "bond_corp", "bond_muni"}


async def fetch_moex_price(
    ticker: str,
    asset_class: str,
) -> Optional[Tuple[float, date, str]]:
    """
    Fetch the latest price from MOEX ISS.
    Returns (price, date, currency) or None on failure.
    """
    if asset_class in BOND_ASSET_CLASSES:
        url = MOEX_BOND_URL.format(ticker=ticker)
        preferred_boards = {"TQOB", "TQCB", "TQOD", "TQIR"}
    else:
        url = MOEX_STOCK_URL.format(ticker=ticker)
        preferred_boards = {"TQBR", "TQDE", "TQTF"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except Exception:
        return None

    return _parse_moex_response(data, preferred_boards, asset_class)


def _parse_moex_response(
    data: dict,
    preferred_boards: set,
    asset_class: str,
) -> Optional[Tuple[float, date, str]]:
    try:
        marketdata = data.get("marketdata", {})
        md_columns = marketdata.get("columns", [])
        md_data = marketdata.get("data", [])

        securities = data.get("securities", {})
        sec_columns = securities.get("columns", [])
        sec_data = securities.get("data", [])

        if not md_columns or not md_data:
            return None

        board_col = md_columns.index("BOARDID") if "BOARDID" in md_columns else None
        price_col = None
        for price_field in ("LAST", "PREVPRICE", "MARKETPRICE"):
            if price_field in md_columns:
                price_col = md_columns.index(price_field)
                break

        date_col = None
        for date_field in ("SYSTIME", "UPDATETIME", "TRADEDATE"):
            if date_field in md_columns:
                date_col = md_columns.index(date_field)
                break

        # Try to get currency from securities block
        currency = "RUB"
        if sec_columns and sec_data:
            curr_col = None
            for curr_field in ("CURRENCYID", "FACEUNIT"):
                if curr_field in sec_columns:
                    curr_col = sec_columns.index(curr_field)
                    break
            if curr_col is not None and sec_data:
                currency = sec_data[0][curr_col] or "RUB"

        # Find best row
        best_row = None
        for row in md_data:
            if board_col is not None and row[board_col] not in preferred_boards:
                continue
            if price_col is not None and row[price_col] is not None:
                best_row = row
                break

        if best_row is None:
            # Fallback: take first row with a price
            for row in md_data:
                if price_col is not None and row[price_col] is not None:
                    best_row = row
                    break

        if best_row is None:
            return None

        price = float(best_row[price_col])
        trade_date = date.today()
        if date_col is not None and best_row[date_col]:
            raw = str(best_row[date_col])[:10]
            try:
                from datetime import datetime
                trade_date = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                pass

        return price, trade_date, currency
    except Exception:
        return None
