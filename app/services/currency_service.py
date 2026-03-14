from __future__ import annotations

import datetime
import logging
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy.orm import Session

from app.config import CBR_API_URL, CURRENCY_RATES_LOG_FILE
from app.models import Currency, CurrencyRate
from app.schemas import CurrencyRateResult
from app.utils.logging_util import flush_all_handlers, setup_file_handler

logger = logging.getLogger(__name__)
setup_file_handler(logger, CURRENCY_RATES_LOG_FILE)  # Configure once at import time

_CBR_TIMEOUT = 15.0  # seconds
_SOURCE = "cbr"


def _fetch_cbr_xml(date: datetime.date) -> dict[str, float]:
    """Fetch currency rates from CBR API for the given date.

    Returns dict: currency_code -> rate (RUB per 1 unit of currency).
    Raises httpx.HTTPError or ValueError on failure.
    """
    date_str = date.strftime("%d/%m/%Y")
    url = f"{CBR_API_URL}?date_req={date_str}"
    logger.debug(f"CBR request: {url}")

    resp = httpx.get(url, timeout=_CBR_TIMEOUT)
    resp.raise_for_status()

    # CBR response declares windows-1251 in XML header — parse from bytes
    root = ET.fromstring(resp.content)

    rates: dict[str, float] = {}
    for valute in root.findall("Valute"):
        char_code_el = valute.find("CharCode")
        vunit_el = valute.find("VunitRate")
        if char_code_el is None or vunit_el is None:
            continue
        code = char_code_el.text or ""
        vunit_text = (vunit_el.text or "").replace(",", ".")
        try:
            rates[code] = float(vunit_text)
        except ValueError:
            logger.warning(f"CBR: cannot parse rate for {code!r}: {vunit_text!r}")

    return rates


def _upsert_rate(
    db: Session,
    date: datetime.date,
    currency: str,
    rate: float,
) -> None:
    existing = (
        db.query(CurrencyRate)
        .filter(CurrencyRate.date == date, CurrencyRate.currency == currency)
        .first()
    )
    if existing:
        existing.rate = rate
        existing.source = _SOURCE
    else:
        db.add(CurrencyRate(date=date, currency=currency, rate=rate, source=_SOURCE))


def fetch_currency_rates(
    db: Session,
    date: datetime.date | None = None,
) -> CurrencyRateResult:
    """Fetch CBR rates for all currencies in the reference table and upsert into currency_rates."""
    if date is None:
        date = datetime.date.today()

    result = CurrencyRateResult(date=date, log_file=str(CURRENCY_RATES_LOG_FILE))

    logger.info("=" * 80)
    logger.info(f"Starting CBR currency rates fetch for {date}")

    # Load reference currencies
    currencies = db.query(Currency).all()
    if not currencies:
        logger.warning("No currencies in reference table — nothing to fetch")
        logger.info("=" * 80)
        flush_all_handlers(logger)
        return result

    codes = [c.code for c in currencies]
    logger.info(f"Currencies to fetch: {', '.join(codes)}")

    # Fetch rates from CBR
    try:
        cbr_rates = _fetch_cbr_xml(date)
    except httpx.HTTPStatusError as exc:
        msg = f"CBR HTTP error: {exc.response.status_code}"
        logger.error(msg)
        result.failed = len(codes)
        result.errors.append(msg)
        flush_all_handlers(logger)
        return result
    except httpx.TimeoutException:
        msg = "CBR request timed out"
        logger.error(msg)
        result.failed = len(codes)
        result.errors.append(msg)
        flush_all_handlers(logger)
        return result
    except Exception as exc:
        msg = f"CBR request failed: {type(exc).__name__}: {exc}"
        logger.error(msg)
        result.failed = len(codes)
        result.errors.append(msg)
        flush_all_handlers(logger)
        return result

    logger.debug(f"CBR returned {len(cbr_rates)} currencies")

    # Upsert each reference currency
    for code in codes:
        rate = cbr_rates.get(code)
        if rate is None:
            msg = f"{code}: курс не найден в ответе ЦБР"
            logger.warning(f"FAIL {code}: not in CBR response")
            result.failed += 1
            result.errors.append(msg)
            continue

        _upsert_rate(db, date, code, rate)
        result.updated += 1
        logger.info(f"OK {code}: rate={rate:.4f} RUB")

    db.commit()

    logger.info(
        f"CBR rates fetch completed: updated={result.updated}, failed={result.failed}"
    )
    if result.errors:
        logger.warning("Errors:\n" + "\n".join(f"  - {e}" for e in result.errors))
    logger.info("=" * 80)

    flush_all_handlers(logger)
    return result
