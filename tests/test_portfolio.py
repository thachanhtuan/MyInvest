from __future__ import annotations

from app.config import DEFAULT_EXCEL_FILE
from app.services.import_service import import_excel
from app.services.portfolio import get_portfolio_summary


def test_portfolio_summary_with_data(db_session):
    """Test portfolio summary after importing real data."""
    if not DEFAULT_EXCEL_FILE.exists():
        import pytest
        pytest.skip("data.xlsx not found")

    import_excel(db_session, DEFAULT_EXCEL_FILE)
    summary = get_portfolio_summary(db_session)

    assert summary.total_invested > 0
    assert summary.current_value > 0
    assert len(summary.holdings) > 0
    assert len(summary.by_account) > 0
    assert len(summary.by_asset_class) > 0
    assert len(summary.by_broker) > 0

    # Verify shares sum to ~100%
    total_share = sum(a.share_pct for a in summary.by_account)
    assert 99.0 <= total_share <= 101.0


def test_portfolio_summary_empty_db(db_session):
    """Test portfolio summary with empty database."""
    summary = get_portfolio_summary(db_session)

    assert summary.total_invested == 0
    assert summary.current_value == 0
    assert summary.holdings == []
    assert summary.by_account == []


def test_portfolio_with_sample_data(sample_data):
    """Test portfolio with minimal sample data."""
    summary = get_portfolio_summary(sample_data)

    assert summary.total_invested == 2658.99
    assert summary.current_value == 2800.0
    assert summary.profit_loss > 0
    assert len(summary.holdings) == 1

    h = summary.holdings[0]
    assert h.ticker == "SBER"
    assert h.quantity == 10
    assert h.current_value == 2800.0
