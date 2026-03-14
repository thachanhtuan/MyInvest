# MyInvest — Copilot Instructions

## Project Overview

MyInvest is a local-only personal investment tracking web app. It imports data from Excel, stores it in SQLite, and displays analytics (portfolio balance, asset allocation, profit/loss) in the browser. The UI is entirely in Russian.

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, openpyxl, pandas
- **Frontend**: Jinja2 server-side templates, Bootstrap 5 (CDN), Chart.js (CDN), Vanilla JS
- **Database**: SQLite (`myinvest.db`)
- **Package manager**: uv

## Architecture — Three-Layer Separation

```
Routers (app/routers/) → Services (app/services/) → Models (app/models.py)
```

- **Routers** are thin HTTP handlers: parse request → call service → return response
- **Services** contain business logic, receive `db: Session` as parameter, no HTTP dependency
- **Models** are SQLAlchemy 2.0 ORM classes using `Mapped` type syntax
- **Schemas** (`app/schemas.py`) are Pydantic models for validation and serialization

### Key Files

| File                             | Purpose                                                                        |
| -------------------------------- | ------------------------------------------------------------------------------ |
| `app/main.py`                    | FastAPI app, lifespan, router registration, Jinja2 setup                       |
| `app/config.py`                  | Paths, DB URL, Excel sheet name mapping                                        |
| `app/database.py`                | Engine, SessionLocal, Base, `get_db()`                                         |
| `app/models.py`                  | 5 ORM models: Account, Asset, BondInfo, Transaction, AssetValuation            |
| `app/schemas.py`                 | Pydantic models + enum labels (`ASSET_CLASS_LABELS`, `TX_TYPE_LABELS`)         |
| `app/routers/pages.py`           | HTML page routes (GET `/`, `/accounts`, `/assets`, `/transactions`, `/import`) |
| `app/routers/analytics.py`       | `GET /api/analytics/summary` — full portfolio JSON                             |
| `app/routers/import_export.py`   | Import Excel + export balance Excel                                            |
| `app/services/import_service.py` | Parse Excel → ORM objects, full-replace strategy                               |
| `app/services/portfolio.py`      | Calculate holdings, balance, allocation from transactions                      |
| `app/services/export_service.py` | Generate openpyxl workbook for balance export                                  |
| `app/utils/formatters.py`        | Jinja2 filters: `money`, `pct`, `fdate`, `profit_class`                        |

## Code Style Rules

### Python

- Every file starts with `from __future__ import annotations`
- Type hints are mandatory for function arguments and return values
- Use `str | None` (not `Optional[str]`)
- Import order: stdlib → third-party → project (`app.`)
- Use SQLAlchemy 2.0 `Mapped` syntax for models
- Use `db.get(Model, pk)` instead of deprecated `Query.get()`
- Dates must be `datetime.date` objects, never strings
- Services receive `Session` as parameter — never import `get_db` in services

### JavaScript

- Vanilla JS only — no frameworks (React, Vue, etc.)
- `const` by default, `let` when needed, never `var`
- `async/await` over `.then()` chains
- Always escape user strings via `escapeHtml()` before DOM insertion

### HTML / Jinja2

- All templates extend `base.html`
- Use filters: `{{ value|money }}`, `{{ value|pct }}`, `{{ value|fdate }}`
- Dashboard data loads via `fetchJSON('/api/analytics/summary')` in JS

### Naming

- Python files/functions: `snake_case`
- Classes: `PascalCase`
- Private functions: `_snake_case`
- DB tables: `snake_case`, plural (`asset_valuations`)
- API routes: `/api/{resource}/`
- HTML routes: `/{page}`
- JS functions: `camelCase`

## Data Model

- `Account.id` (string PK, e.g. `"S043V77"`)
- `Asset.ticker` (string PK, e.g. `"SBER"`)
- `Transaction.ticker` is nullable (`deposit_in`/`deposit_out` have no ticker)
- `AssetValuation` has unique constraint on `(date, ticker)`
- Holdings are calculated dynamically from transactions, not stored

## Excel Import

- Sheet names are in Russian, mapped in `app/config.py → SHEET_NAMES`:
  `"Счета"`, `"Активы"`, `"Облигации"`, `"Транзакции"`, `"Стоимость активов"`
- Import order (FK respect): Account → Asset → BondInfo → Transaction → AssetValuation
- Strategy: clear all tables → re-insert (full replace)
- `amount` rule: use value if present, else `quantity × price`
- `total_amount` rule: use value if present, else `amount + commission + nkd` (buy) or `amount − commission` (sell)

## Testing

- Framework: pytest with in-memory SQLite
- Fixtures: `db_session` (clean session), `client` (TestClient), `sample_data` (minimal dataset)
- Dates in test data must be `datetime.date(...)` objects, not strings
- Run: `uv run pytest tests/ -v`

## UI Language

- All user-visible text must be in **Russian**
- Code, comments, variable names, commits — in **English**
- Russian labels for enums: `ASSET_CLASS_LABELS`, `TX_TYPE_LABELS` in `app/schemas.py`

## Common Patterns

### Adding a new API endpoint

1. Create or edit a router file in `app/routers/`
2. If logic is non-trivial, add a function in `app/services/`
3. Add Pydantic schema in `app/schemas.py` if needed
4. Register the router in `app/main.py` if it's a new file

### Adding a new page

1. Add route in `app/routers/pages.py`
2. Create template in `templates/` extending `base.html`
3. Add nav link in `templates/base.html` sidebar

### Adding a new model field

1. Add field to ORM model in `app/models.py`
2. Add to Pydantic schema in `app/schemas.py`
3. Update import parser in `app/services/import_service.py`
4. Generate migration: `uv run alembic revision --autogenerate -m "description"`
5. Apply: `uv run alembic upgrade head`
