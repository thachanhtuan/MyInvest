# MyInvest

Personal investment tracking web application built with FastAPI, SQLAlchemy, and Bootstrap 5.

## Features

- **Accounts** – broker, IIS, deposit, and savings accounts
- **Assets** – stocks, bonds, ETFs, deposits, gold, cash, and more
- **Transactions** – buy, sell, dividends, coupons, amortization, deposits, and more
- **Quotes** – manual or automatic (MOEX ISS) price fetch
- **Bond analytics** – coupon schedule projection, bond ladder chart
- **Portfolio analytics** – holdings, market value, P&L, asset allocation
- **Excel import/export** – bulk data management

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3.12 + FastAPI + uvicorn     |
| Database    | SQLite via SQLAlchemy ORM           |
| Excel I/O   | openpyxl                            |
| HTTP client | httpx (MOEX API)                    |
| Templates   | Jinja2 (server-side rendering)      |
| Frontend    | Bootstrap 5 + Chart.js + vanilla JS |

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Excel Import Format

The Excel file should contain sheets named (in Russian):

| Sheet name         | Model             |
|--------------------|-------------------|
| Счета              | Account           |
| Активы             | Asset             |
| Облигации          | BondInfo          |
| Транзакции         | Transaction       |
| Котировки          | Quote             |
| Купоны             | CouponPayment     |
| Стоимость актива   | AssetValuation    |
| Целевая аллокация  | TargetAllocation  |

First row is headers (English or Russian column names are supported).

## Running Tests

```bash
python -m pytest tests/ -v
```

## API Documentation

FastAPI auto-generates interactive docs at:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc:       [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Project Structure

```
app/
├── main.py           – FastAPI app, routes
├── database.py       – SQLAlchemy engine & session
├── models.py         – ORM models
├── schemas.py        – Pydantic schemas
├── routers/          – API endpoint handlers
└── services/
    ├── portfolio.py  – Holdings, P&L, allocation, bond ladder
    ├── excel_service.py – Import/export
    └── market_data.py   – MOEX price fetching
templates/            – Jinja2 HTML templates
static/               – CSS & JS assets
tests/                – pytest test suite
```