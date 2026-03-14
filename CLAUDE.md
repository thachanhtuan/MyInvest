# MyInvest — Claude Code Instructions

## Project

Local personal investment tracking web app. Russian UI. SQLite database.

## Run

```bash
uv sync                                        # install deps
uv run alembic upgrade head                    # apply migrations
uv run uvicorn app.main:app --reload           # start server at :8000
uv run pytest tests/ -v                        # run tests
```

## Architecture

Three-layer: `app/routers/` (HTTP) → `app/services/` (logic) → `app/models.py` (ORM).
Services take `db: Session` as parameter — no HTTP dependency.
Jinja2 templates in `templates/`, shared `templates` object in `app/main.py`.

## Key Conventions

- `from __future__ import annotations` at top of every Python file
- SQLAlchemy 2.0 `Mapped` syntax, `db.get(Model, pk)` instead of `Query.get()`
- Dates are `datetime.date` objects, never strings
- `str | None` syntax, not `Optional[str]`
- Vanilla JS only — no React/Vue. CDN Bootstrap 5 + Chart.js
- All user-facing text in Russian. Code/comments/commits in English
- Excel sheet names: "Счета", "Активы", "Облигации", "Транзакции", "Стоимость активов"
- Import strategy: clear all + re-insert (full replace)
- Jinja2 filters: `{{ val|money }}`, `{{ val|pct }}`, `{{ val|fdate }}`
- Alembic with `render_as_batch=True` for SQLite compatibility

## Models (app/models.py)

- `Account` — PK: `id` (string), type: broker/iis/deposit/savings
- `Asset` — PK: `ticker` (string), asset_class: stock_ru/bond_gov/bond_corp/etf/...
- `BondInfo` — PK/FK: `ticker → Asset`, face_value, coupon, maturity
- `Transaction` — FK: account_id, ticker (nullable for deposit_in/out)
- `AssetValuation` — unique on (date, ticker), value from broker

## Testing

- pytest with in-memory SQLite (`tests/conftest.py`)
- Test dates must be `datetime.date(...)` objects
- Fixtures: `db_session`, `client`, `sample_data`

## Documentation

- `docs/ARCHITECTURE.md` — full architecture description
- `docs/CODE_STANDARDS.md` — code conventions and rules
- `docs/EXCEL_FORMAT.md` — Excel file format spec
- `docs/DATA_STRUCTURES.md` — enum reference (AccountType, AssetClass, TransactionType)
