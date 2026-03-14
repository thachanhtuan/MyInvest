from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Account, Asset, BondInfo, Transaction, AssetValuation


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with overridden DB dependency."""
    from httpx import ASGITransport, AsyncClient
    from fastapi.testclient import TestClient

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db_session: Session):
    """Insert minimal sample data."""
    acc = Account(id="test1", name="Test Account", type="broker",
                  broker_or_bank="TestBroker", currency="RUB")
    asset = Asset(ticker="SBER", name="Сбербанк", asset_class="stock_ru", currency="RUB")
    db_session.add_all([acc, asset])
    db_session.flush()

    tx = Transaction(
        date=datetime.date(2025, 1, 15), account_id="test1", ticker="SBER",
        tx_type="buy", quantity=10, price=265.5,
        amount=2655.0, total_amount=2658.99, currency="RUB",
    )
    val = AssetValuation(
        date=datetime.date(2025, 2, 15), ticker="SBER", value=2800.0, currency="RUB",
    )
    db_session.add_all([tx, val])
    db_session.commit()
    return db_session
