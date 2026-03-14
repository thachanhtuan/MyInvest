from __future__ import annotations

from pathlib import Path

from app.config import DEFAULT_EXCEL_FILE
from app.models import Account, Asset, BondInfo, Transaction, AssetValuation
from app.services.import_service import import_excel


def test_import_default_file(db_session):
    """Test importing the actual data.xlsx file."""
    if not DEFAULT_EXCEL_FILE.exists():
        import pytest
        pytest.skip("data.xlsx not found")

    result = import_excel(db_session, DEFAULT_EXCEL_FILE)

    assert result.accounts == 5
    assert result.assets == 25
    assert result.bonds == 9
    assert result.transactions == 83
    assert result.valuations == 55
    assert result.errors == []

    # Verify data in DB
    assert db_session.query(Account).count() == 5
    assert db_session.query(Asset).count() == 25
    assert db_session.query(BondInfo).count() == 9
    assert db_session.query(Transaction).count() == 83
    assert db_session.query(AssetValuation).count() == 55


def test_reimport_clears_data(db_session):
    """Test that re-importing clears old data."""
    if not DEFAULT_EXCEL_FILE.exists():
        import pytest
        pytest.skip("data.xlsx not found")

    import_excel(db_session, DEFAULT_EXCEL_FILE)
    import_excel(db_session, DEFAULT_EXCEL_FILE)

    assert db_session.query(Account).count() == 5
    assert db_session.query(Transaction).count() == 83


def test_import_nonexistent_file(db_session):
    result = import_excel(db_session, Path("/nonexistent/file.xlsx"))
    assert len(result.errors) > 0
    assert result.accounts == 0
