# Архитектура MyInvest

## Обзор

MyInvest — локальное веб-приложение на Python для учёта инвестиционного портфеля. Архитектура построена по принципу **трёхслойного разделения**: HTTP-слой (роутеры) → бизнес-логика (сервисы) → данные (модели).

```
┌─────────────────────────────────────────────────────┐
│                    Браузер                           │
│         HTML + Bootstrap 5 + Chart.js + JS          │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (localhost:8000)
┌──────────────────────┴──────────────────────────────┐
│                  FastAPI + Uvicorn                   │
├─────────────────────────────────────────────────────┤
│  Роутеры (app/routers/)                             │
│    pages.py         — HTML-страницы (Jinja2)        │
│    accounts.py      — CRUD счетов                   │
│    assets.py        — CRUD активов                  │
│    transactions.py  — CRUD транзакций               │
│    analytics.py     — аналитика портфеля            │
│    import_export.py — импорт Excel / экспорт        │
├─────────────────────────────────────────────────────┤
│  Сервисы (app/services/)                            │
│    import_service.py  — парсинг Excel → ORM         │
│    export_service.py  — генерация Excel-отчётов     │
│    portfolio.py       — расчёт позиций и баланса    │
├─────────────────────────────────────────────────────┤
│  Модели (app/models.py) — SQLAlchemy ORM            │
│    Account │ Asset │ BondInfo │ Transaction │ Valuation │
├─────────────────────────────────────────────────────┤
│  SQLite (myinvest.db) — файловая БД, Alembic        │
└─────────────────────────────────────────────────────┘
```

## Стек технологий

| Слой              | Технология        | Назначение                                              |
| ----------------- | ----------------- | ------------------------------------------------------- |
| Язык              | Python 3.12+      | Основной язык                                           |
| Пакетный менеджер | uv                | Быстрая установка зависимостей                          |
| Web-фреймворк     | FastAPI           | Асинхронный, автодокументация (Swagger)                 |
| ASGI-сервер       | Uvicorn           | Лёгкий, один процесс (~30-50 МБ RAM)                    |
| Шаблоны           | Jinja2            | Серверный рендеринг HTML                                |
| ORM               | SQLAlchemy 2.0    | Декларативные модели, Mapped-синтаксис                  |
| Миграции          | Alembic           | Версионирование схемы, `render_as_batch` для SQLite     |
| БД                | SQLite            | Файловая, ноль настройки, достаточно для 1 пользователя |
| Excel             | openpyxl          | Чтение/запись `.xlsx`                                   |
| Расчёты           | pandas            | Агрегации (в будущих фазах)                             |
| CSS               | Bootstrap 5 (CDN) | Адаптивный UI без сборки                                |
| Графики           | Chart.js 4 (CDN)  | Donut, bar, line charts                                 |
| JavaScript        | Vanilla JS        | Fetch API, DOM, без фреймворков                         |

## Модель данных

### ER-диаграмма

```
Account 1──────────* Transaction *──────────1 Asset
                                                │
                                            1   │   1
                                           ┌────┴────┐
                                      BondInfo   AssetValuation
```

### Таблицы

**accounts** — брокерские и банковские счета.

- PK: `id` (строка, например `"S043V77"`)
- Тип: `broker`, `iis`, `deposit`, `savings`
- Группировка по `broker_or_bank`

**assets** — справочник активов (акции, облигации, ETF, фонды).

- PK: `ticker` (строка, например `"SBER"`)
- Класс: `stock_ru`, `stock_foreign`, `bond_gov`, `bond_corp`, `bond_muni`, `etf`, `deposit`, `cash`, `gold`, `other`

**bond_info** — расширенные параметры облигаций.

- PK/FK: `ticker → assets.ticker`
- Номинал, купон, дата погашения, оферта, периодичность выплат

**transactions** — все операции.

- PK: `id` (autoincrement)
- FK: `account_id → accounts.id`, `ticker → assets.ticker` (nullable)
- Типы: `buy`, `sell`, `dividend`, `coupon`, `amortization`, `maturity`, `commission`, `tax`, `deposit_in`, `deposit_out`, `interest`, `initial_balance`, `other`
- `ticker` может быть NULL (для `deposit_in`, `deposit_out`)

**asset_valuations** — стоимость актива на дату (из данных брокера).

- PK: `id` (autoincrement)
- FK: `ticker → assets.ticker`
- Уникальный составной ключ: `(date, ticker)`

### Правила расчёта (из EXCEL_FORMAT.md)

- `amount`: если заполнен — используется напрямую; если пуст — `quantity × price`
- `total_amount`: если заполнен — используется; если пуст — `amount + commission + nkd` (покупка) или `amount − commission` (продажа)

## Архитектурные решения

### 1. Серверный рендеринг + JSON API

Приложение использует гибридный подход:

- **HTML-страницы** рендерятся на сервере через Jinja2 (роутер `pages.py`)
- **Данные для дашборда** загружаются через JSON API (`/api/analytics/summary`) и рендерятся JavaScript'ом на клиенте
- Это позволяет использовать Chart.js для интерактивных графиков, сохраняя простоту серверных шаблонов

### 2. Jinja2 templates — общий объект

Объект `templates` создаётся в `app/main.py` и импортируется в роутеры. Там же регистрируются фильтры (`money`, `pct`, `fdate`) и глобальные функции (`profit_class`).

### 3. Импорт: полная замена

При импорте Excel все таблицы очищаются и данные вставляются заново (стратегия «replace»). Это проще и надёжнее для однопользовательского приложения. Upsert-логика запланирована в Фазе 6.

Порядок очистки (из-за FK): `AssetValuation → Transaction → BondInfo → Asset → Account`.
Порядок вставки: обратный.

### 4. Расчёт позиций (holdings)

Позиции рассчитываются динамически из транзакций (не хранятся в БД):

1. Выбираются все транзакции типа `buy`, `sell`, `initial_balance`
2. Агрегируются по ключу `(account_id, ticker)`
3. Текущая стоимость берётся из последней записи `AssetValuation` по тикеру
4. Если у тикера есть записи в нескольких счетах — стоимость распределяется пропорционально количеству

### 5. SQLite + Alembic с batch mode

SQLite не поддерживает `ALTER TABLE ... DROP COLUMN` и некоторые другие DDL-операции. Поэтому в `alembic/env.py` включён `render_as_batch=True`, который оборачивает миграции в пересоздание таблицы.

## Слои приложения

### Роутеры (`app/routers/`)

Тонкий HTTP-слой. Обязанности:

- Принять HTTP-запрос, извлечь параметры
- Вызвать сервис или выполнить простой запрос к БД
- Вернуть HTML (через `templates.TemplateResponse`) или JSON

Роутеры **не содержат** бизнес-логику расчётов.

### Сервисы (`app/services/`)

Бизнес-логика, независимая от HTTP:

- `import_service.py` — парсинг Excel, создание ORM-объектов, транзакция БД
- `export_service.py` — формирование openpyxl Workbook → bytes
- `portfolio.py` — расчёт позиций, баланса, аллокации, прибыли

Сервисы получают `Session` как параметр — это облегчает тестирование.

### Модели (`app/models.py`)

SQLAlchemy 2.0 Mapped-синтаксис с type hints:

```python
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
```

### Схемы (`app/schemas.py`)

Pydantic-модели для:

- Сериализации ORM-объектов в JSON (`AccountRead`, `TransactionRead`, ...)
- Аналитических структур (`PortfolioSummary`, `HoldingInfo`, ...)
- Enum-справочников и человекочитаемых лейблов (`ASSET_CLASS_LABELS`, `TX_TYPE_LABELS`)

## Frontend

### Принципы

- **Без сборки** — Bootstrap и Chart.js загружаются с CDN
- **Минимум JS** — JavaScript используется только для:
  - Загрузки данных через `fetch()` на дашборде
  - Рендеринга Chart.js-графиков
  - Вспомогательных функций (`formatMoney`, `formatPct`, `escapeHtml`)
- **Серверный HTML** — таблицы счетов, активов, транзакций рендерятся Jinja2

### Базовый шаблон (`base.html`)

- Боковая навигация (sidebar) с иконками Bootstrap Icons
- Активный пункт меню подсвечивается через проверку `request.url.path`
- Область уведомлений `#alert-area` для flash-сообщений

## Конфигурация

Вся конфигурация в `app/config.py`:

- `BASE_DIR` — корень проекта
- `DB_URL` — путь к SQLite (`sqlite:///myinvest.db`)
- `DEFAULT_EXCEL_FILE` — путь к файлу данных по умолчанию
- `SHEET_NAMES` — маппинг логических имён на русские названия листов Excel

## Тестирование

- Фреймворк: pytest
- Фикстура `db_session` — in-memory SQLite, отдельная для каждого теста
- Фикстура `client` — TestClient с подменой зависимости `get_db`
- Фикстура `sample_data` — минимальный набор данных для unit-тестов

## Планируемые расширения

| Фаза | Описание                                 | Новые файлы                                        |
| ---- | ---------------------------------------- | -------------------------------------------------- |
| 3    | Котировки MOEX ISS + Yahoo Finance       | `services/moex_api.py`, `services/yahoo_api.py`    |
| 4    | Доходность, графики стоимости во времени | расширение `portfolio.py`, новые Chart.js графики  |
| 5    | Лестница облигаций, купонный календарь   | `services/bond_service.py`, `templates/bonds.html` |
| 6    | CRUD через UI, импорт с дедупликацией    | формы в шаблонах, upsert в `import_service.py`     |
