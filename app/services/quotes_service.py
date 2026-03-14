from __future__ import annotations

import datetime
import logging
from collections import defaultdict

import httpx
import yfinance as yf
from sqlalchemy.orm import Session

from app.config import MOEX_ISS_BASE_URL, QUOTES_LOG_FILE
from app.models import Asset, AssetValuation, BondInfo, Transaction
from app.schemas import QuoteResult
from app.utils.logging_util import flush_all_handlers, setup_file_handler

logger = logging.getLogger(__name__)
setup_file_handler(logger, QUOTES_LOG_FILE)  # Configure once at import time


_BOND_CLASSES = {"bond_gov", "bond_corp", "bond_muni"}
_NO_QUOTE_CLASSES = {"deposit", "cash"}
_YAHOO_DEFAULT_CLASSES = {"stock_foreign"}

_MOEX_TIMEOUT = 10.0  # seconds per request


def _pick_source(asset_class: str, exchange: str | None) -> str | None:
    """Determine quote source: 'moex', 'yahoo', or None (no quotes needed)."""
    if asset_class in _NO_QUOTE_CLASSES:
        return None
    if exchange:
        return exchange
    if asset_class in _YAHOO_DEFAULT_CLASSES:
        return "yahoo"
    return "moex"


def _get_open_positions(db: Session) -> dict[str, dict]:
    """Return open positions per ticker from transaction history.

    Result: ticker -> {asset_class, exchange, face_value, total_qty, currency}
    """
    txs = (
        db.query(Transaction)
        .filter(
            Transaction.ticker.isnot(None),
            Transaction.tx_type.in_(["buy", "sell", "initial_balance"]),
        )
        .all()
    )

    qty_map: dict[str, float] = defaultdict(float)
    for tx in txs:
        qty = tx.quantity or 0.0
        if tx.tx_type in ("buy", "initial_balance"):
            qty_map[tx.ticker] += qty
        elif tx.tx_type == "sell":
            qty_map[tx.ticker] -= qty

    assets: dict[str, Asset] = {a.ticker: a for a in db.query(Asset).all()}
    bond_infos: dict[str, BondInfo] = {b.ticker: b for b in db.query(BondInfo).all()}

    positions: dict[str, dict] = {}
    for ticker, qty in qty_map.items():
        if qty <= 0:
            continue
        asset = assets.get(ticker)
        if not asset:
            continue
        bond = bond_infos.get(ticker)
        positions[ticker] = {
            "asset_class": asset.asset_class,
            "exchange": asset.exchange,
            "face_value": bond.face_value if bond else 1.0,
            "total_qty": qty,
            "currency": asset.currency,
        }

    return positions


def _fetch_moex_price(ticker: str, asset_class: str, face_value: float) -> float | None:
    """Fetch price from MOEX ISS.

    Bonds: returns price per bond in RUB (converted from % of face value).
    Stocks/ETF: returns price per share in RUB.
    """
    market = "bonds" if asset_class in _BOND_CLASSES else "shares"
    url = (
        f"{MOEX_ISS_BASE_URL}/engines/stock/markets/{market}/securities/{ticker}.json"
        "?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST,CLOSE"
    )

    logger.debug(f"MOEX request: {url}")

    try:
        resp = httpx.get(url, timeout=_MOEX_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(f"MOEX HTTP error for {ticker}: {exc.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"MOEX timeout for {ticker}")
        return None
    except Exception as exc:
        logger.warning(f"MOEX request failed for {ticker}: {type(exc).__name__}: {exc}")
        return None

    try:
        md = data["marketdata"]
        columns = md["columns"]
        rows = md["data"]

        # Find available price columns
        last_idx = columns.index("LAST") if "LAST" in columns else None
        close_idx = columns.index("CLOSE") if "CLOSE" in columns else None

        if last_idx is None and close_idx is None:
            logger.warning(
                f"MOEX response for {ticker} has no LAST or CLOSE columns. "
                f"Available columns: {columns}"
            )
            return None

    except (KeyError, ValueError) as exc:
        logger.warning(f"Unexpected MOEX response structure for {ticker}: {exc}")
        logger.debug(f"MOEX response: {data}")
        return None

    raw_price: float | None = None
    for row in rows:
        if not row:
            continue
        # Try LAST first, then CLOSE
        if last_idx is not None:
            val = row[last_idx]
            if val is not None and float(val) > 0:
                raw_price = float(val)
                break
        if close_idx is not None:
            val = row[close_idx]
            if val is not None and float(val) > 0:
                raw_price = float(val)
                break

    if raw_price is None:
        logger.info(f"No price data from MOEX for {ticker} (market={market})")
        return None

    if asset_class in _BOND_CLASSES:
        # MOEX bond prices are in % of face value (e.g. 96.5 means 96.5% of face_value)
        price = (raw_price / 100.0) * face_value
        logger.debug(f"MOEX bond {ticker}: raw={raw_price}%, face={face_value}, price={price}")
        return price

    logger.debug(f"MOEX stock/etf {ticker}: price={raw_price}")
    return raw_price


def _fetch_yahoo_price(ticker: str) -> float | None:
    """Fetch current price from Yahoo Finance."""
    logger.debug(f"Yahoo request: {ticker}")
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.fast_info
        price = info.last_price
        if price is not None and float(price) > 0:
            logger.debug(f"Yahoo {ticker}: price={price}")
            return float(price)
        else:
            logger.info(f"Yahoo {ticker}: no valid price (got {price})")
            return None
    except Exception as exc:
        logger.warning(f"Yahoo Finance request failed for {ticker}: {type(exc).__name__}: {exc}")
        return None


def _upsert_valuation(
    db: Session,
    ticker: str,
    value: float,
    currency: str,
    today: datetime.date,
) -> None:
    existing = (
        db.query(AssetValuation)
        .filter(AssetValuation.date == today, AssetValuation.ticker == ticker)
        .first()
    )
    if existing:
        existing.value = value
        existing.currency = currency
    else:
        db.add(AssetValuation(date=today, ticker=ticker, value=value, currency=currency))


def fetch_all_quotes(db: Session) -> QuoteResult:
    """Fetch current market quotes for all open positions and upsert asset_valuations."""
    # DIAGNOSTIC: direct file write, bypasses logging — remove after debug
    import pathlib as _pl
    _dbg = _pl.Path("logs/DEBUG_was_here.txt")
    _dbg.parent.mkdir(exist_ok=True)
    _dbg.write_text(f"fetch_all_quotes called at {datetime.datetime.now()}\nfile={__file__}\n")

    today = datetime.date.today()
    positions = _get_open_positions(db)
    result = QuoteResult(log_file=str(QUOTES_LOG_FILE))

    logger.info("=" * 80)
    logger.info(f"Starting quotes refresh for {len(positions)} positions on {today}")
    logger.info("=" * 80)

    for ticker, pos in positions.items():
        source = _pick_source(pos["asset_class"], pos["exchange"])
        if source is None:
            result.skipped += 1
            logger.info(f"SKIP {ticker}: asset_class={pos['asset_class']} (no quotes needed)")
            continue

        logger.info(
            f"FETCH {ticker}: source={source}, asset_class={pos['asset_class']}, "
            f"qty={pos['total_qty']}, face_value={pos['face_value']}"
        )

        try:
            if source == "moex":
                price = _fetch_moex_price(ticker, pos["asset_class"], pos["face_value"])
            else:
                price = _fetch_yahoo_price(ticker)

            if price is None:
                result.failed += 1
                error_msg = f"{ticker}: цена не получена от {source} [DBG]"
                result.errors.append(error_msg)
                logger.warning(f"FAIL {ticker}: no price returned from {source}")
                continue

            total_value = price * pos["total_qty"]
            _upsert_valuation(db, ticker, round(total_value, 2), pos["currency"], today)
            result.updated += 1
            logger.info(
                f"OK {ticker}: price={price:.4f}, total={total_value:.2f} {pos['currency']}"
            )

        except Exception as exc:
            logger.exception(f"ERROR {ticker}: unexpected exception")
            result.failed += 1
            result.errors.append(f"{ticker}: {type(exc).__name__}: {exc}")

    db.commit()
    logger.info("=" * 80)
    logger.info(
        f"Quotes refresh completed: updated={result.updated}, "
        f"failed={result.failed}, skipped={result.skipped}"
    )
    if result.errors:
        logger.warning(f"Errors summary:\n" + "\n".join(f"  - {e}" for e in result.errors))
    logger.info("=" * 80)

    flush_all_handlers(logger)

    return result
