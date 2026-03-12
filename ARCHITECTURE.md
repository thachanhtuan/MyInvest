# Архитектура MyInvest

## Обзор

MyInvest — локальное веб-приложение для учёта личных инвестиций на российском рынке.  
Серверный рендеринг (SSR) на базе FastAPI + Jinja2, данные хранятся в SQLite.

```
┌──────────────────────────────────────────────────────┐
│                    Браузер                            │
│   Bootstrap 5 · Chart.js · vanilla JS (static/)      │
└────────────────────────┬─────────────────────────────┘
                         │  HTTP
┌────────────────────────▼─────────────────────────────┐
│                  FastAPI (uvicorn)                    │
│                                                      │
│  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  Страницы    │  │  REST API (/api/...)          │  │
│  │  (Jinja2 SSR)│  │  routers/                     │  │
│  └──────┬───────┘  └──────────────┬───────────────┘  │
│         │                         │                   │
│         └──────────┬──────────────┘                   │
│                    │                                  │
│         ┌──────────▼──────────┐                       │
│         │     Сервисы         │                       │
│         │  services/          │                       │
│         └──────────┬──────────┘                       │
│                    │                                  │
│         ┌──────────▼──────────┐   ┌───────────────┐  │
│         │  SQLAlchemy ORM     │   │  MOEX ISS API │  │
│         │  models.py          │   │  (httpx)      │  │
│         └──────────┬──────────┘   └───────────────┘  │
│                    │                                  │
└────────────────────┼──────────────────────────────────┘
                     │
              ┌──────▼──────┐
              │  SQLite     │
              │ myinvest.db │
              └─────────────┘
```

---

## Технологический стек

| Уровень        | Технология                          |
| -------------- | ----------------------------------- |
| Язык           | Python 3.12                         |
| Web-фреймворк  | FastAPI ≥ 0.110                     |
| ASGI-сервер    | uvicorn ≥ 0.29                      |
| ORM            | SQLAlchemy ≥ 2.0                    |
| Валидация      | Pydantic ≥ 2.6                      |
| Шаблоны        | Jinja2 ≥ 3.1                        |
| Frontend       | Bootstrap 5 + Chart.js + vanilla JS |
| Excel I/O      | openpyxl ≥ 3.1                      |
| HTTP-клиент    | httpx ≥ 0.27                        |
| База данных    | SQLite 3                            |
| Тестирование   | pytest ≥ 8.0 + pytest-asyncio       |

---

## Структура каталогов

```
MyInvest/
├── run.py                   # Точка входа: uvicorn на порту 8000
├── requirements.txt         # Зависимости Python
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI-приложение, lifespan, страницы (Jinja2)
│   ├── database.py          # Подключение к SQLite, SessionLocal, create_tables()
│   ├── models.py            # ORM-модели (8 таблиц)
│   ├── schemas.py           # Pydantic-схемы (request / response)
│   ├── routers/             # API-обработчики
│   │   ├── accounts.py      # /api/accounts
│   │   ├── assets.py        # /api/assets, /api/bond-info
│   │   ├── transactions.py  # /api/transactions
│   │   ├── quotes.py        # /api/quotes, /api/quotes/fetch/{ticker}
│   │   ├── coupons.py       # /api/coupons
│   │   ├── valuations.py    # /api/valuations
│   │   ├── analytics.py     # /api/analytics
│   │   └── import_export.py # /api/import, /api/export
│   └── services/
│       ├── portfolio.py     # Расчёт позиций, P&L, аллокации, лестницы облигаций
│       ├── market_data.py   # Загрузка котировок с MOEX ISS
│       └── excel_service.py # Импорт/экспорт Excel
├── templates/               # Jinja2-шаблоны
│   ├── base.html            # Базовый layout (навигация, Bootstrap)
│   ├── index.html           # Дашборд
│   ├── accounts.html        # Счета
│   ├── assets.html          # Активы
│   ├── transactions.html    # Транзакции
│   ├── analytics.html       # Аналитика портфеля
│   ├── bonds.html           # Облигации (лестница, купоны)
│   └── import_export.html   # Импорт / Экспорт Excel
├── static/
│   ├── css/style.css        # Пользовательские стили
│   └── js/app.js            # Frontend-логика (fetch-запросы, Chart.js)
├── tests/
│   ├── conftest.py          # Фикстуры pytest (in-memory SQLite)
│   ├── test_models.py       # Тесты ORM-моделей
│   └── test_analytics.py    # Тесты сервиса portfolio
├── docs/
│   ├── EXCEL_FORMAT.md      # Спецификация формата Excel
│   └── DATA_STRUCTURES.md   # Перечисления (Enum)
└── data-xlsx/               # Примеры Excel-файлов
```

---

## Слои приложения

### 1. Точка входа (`run.py`)

Запускает uvicorn на `127.0.0.1:8000` с автоперезагрузкой:

```python
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
```

### 2. FastAPI-приложение (`app/main.py`)

- **Lifespan**: при старте вызывает `create_tables()` — автоматическое создание таблиц.
- **Статика**: каталог `static/` монтируется на `/static`.
- **Шаблоны**: каталог `templates/`, рендеринг через `Jinja2Templates`.
- **Страницы**: GET-маршруты (`/`, `/accounts`, `/assets`, …) возвращают HTML.
- **API**: подключены роутеры из `app/routers/` с префиксом `/api/...`.

### 3. API-роутеры (`app/routers/`)

Каждый файл — отдельный `APIRouter` с CRUD-операциями:

| Роутер             | Префикс           | Основные операции              |
| ------------------ | ------------------ | ------------------------------ |
| `accounts.py`      | `/api/accounts`    | GET, POST, PUT, DELETE         |
| `assets.py`        | `/api/assets`      | GET, POST, PUT, DELETE + bond  |
| `transactions.py`  | `/api/transactions`| GET, POST, PUT, DELETE         |
| `quotes.py`        | `/api/quotes`      | GET, POST, DELETE, fetch MOEX  |
| `coupons.py`       | `/api/coupons`     | GET, POST, DELETE              |
| `valuations.py`    | `/api/valuations`  | GET, POST, DELETE              |
| `analytics.py`     | `/api/analytics`   | Портфель, P&L, аллокация      |
| `import_export.py` | `/api/import|export`| POST (загрузка), GET (выгрузка)|

Зависимость `get_db()` из `database.py` инжектируется через `Depends`.

### 4. Сервисы (`app/services/`)

Бизнес-логика, отделённая от HTTP-слоя:

- **`portfolio.py`** — расчёт текущих позиций (holdings), себестоимости, средней цены, нереализованной прибыли/убытка, аллокации по классам активов, лестницы облигаций, расписания купонов.
- **`market_data.py`** — асинхронные запросы к [MOEX ISS API](https://iss.moex.com) через `httpx`; парсинг ответов для акций и облигаций.
- **`excel_service.py`** — импорт из `.xlsx` (8 типов листов с русскими заголовками); экспорт всей базы в `.xlsx`.

### 5. ORM-модели (`app/models.py`)

8 таблиц, все наследуют `Base` (SQLAlchemy `DeclarativeBase`):

| Модель             | PK          | Назначение                                    |
| ------------------ | ----------- | --------------------------------------------- |
| `Account`          | `id` (str)  | Брокерские/банковские счета                   |
| `Asset`            | `ticker`    | Справочник активов                            |
| `BondInfo`         | `ticker` FK | Параметры облигаций (1:1 с Asset)             |
| `Transaction`      | `id` (int)  | Все операции (покупки, продажи, дивиденды…)   |
| `Quote`            | `id` (int)  | Исторические цены закрытия                    |
| `CouponPayment`    | `id` (int)  | Расписание купонных выплат                    |
| `AssetValuation`   | `id` (int)  | Стоимость позиций по данным брокера           |
| `TargetAllocation` | `id` (int)  | Целевая аллокация по классам активов          |

### 6. Pydantic-схемы (`app/schemas.py`)

`*Create` — входные данные для POST, `*Update` — для PUT, `*Out` — ответ API.  
Все схемы используют `model_config = ConfigDict(from_attributes=True)`.

### 7. База данных (`app/database.py`)

- **URL**: `sqlite:///./myinvest.db` (файл в корне проекта).
- **Миграции**: отсутствуют — таблицы создаются через `Base.metadata.create_all()`.
- **Сессия**: `SessionLocal` (autocommit=False, autoflush=False).
- **Зависимость**: `get_db()` — генератор, автоматически закрывает сессию.

### 8. Frontend

- **Шаблоны**: Jinja2 SSR — HTML формируется на сервере.
- **CSS**: Bootstrap 5 (CDN) + `static/css/style.css`.
- **JS**: `static/js/app.js` — fetch-запросы к REST API, обновление DOM, графики Chart.js.
- **Графики**: Chart.js (CDN) — аллокация (pie), динамика стоимости (line).

---

## Потоки данных

### Просмотр страницы

```
Браузер → GET /analytics → main.py → templates/analytics.html → HTML
Браузер → GET /api/analytics/... → routers/analytics.py → services/portfolio.py → SQLAlchemy → SQLite → JSON
```

### Загрузка котировки с MOEX

```
Браузер → GET /api/quotes/fetch/{ticker}
       → routers/quotes.py
       → services/market_data.py → httpx → MOEX ISS API
       → сохранение в таблицу Quote
       → JSON-ответ
```

### Импорт Excel

```
Браузер → POST /api/import (multipart/form-data, .xlsx)
       → routers/import_export.py
       → services/excel_service.py → openpyxl → парсинг листов
       → upsert в таблицы Account, Asset, BondInfo, Transaction, ...
       → JSON-ответ (статистика импорта)
```

---

## Конфигурация

Конфигурация задана константами в коде (без `.env` и переменных окружения):

| Параметр   | Значение                  | Где задан       |
| ---------- | ------------------------- | --------------- |
| Хост       | `127.0.0.1`              | `run.py`        |
| Порт       | `8000`                   | `run.py`        |
| БД         | `sqlite:///./myinvest.db`| `database.py`   |
| Reload     | `True`                   | `run.py`        |

---

## Тестирование

```bash
python -m pytest tests/ -v
```

- **conftest.py** — фикстура `db`: in-memory SQLite сессия для каждого теста.
- **test_models.py** — создание моделей, проверка связей.
- **test_analytics.py** — расчёты портфеля (holdings, P&L, аллокация).

---

## Внешние зависимости

- **MOEX ISS API** (`https://iss.moex.com`) — единственный внешний сервис; бесплатный, без API-ключей. Используется только для загрузки котировок. Приложение полностью работоспособно без интернета.

---

## Ключевые решения

| Решение                                   | Причина                                                    |
| ----------------------------------------- | ---------------------------------------------------------- |
| SQLite вместо PostgreSQL                   | Локальное приложение, один пользователь, zero-config       |
| Jinja2 SSR вместо SPA                     | Простота, нет необходимости в отдельном фронтенд-сборщике |
| Нет конвертации валют                      | Российский рынок, активы в RUB                            |
| `AssetValuation.value` — общая стоимость  | Значение от брокера, а не цена за единицу                 |
| Нет миграций (Alembic)                    | Приложение для личного пользования, схема стабильна       |
