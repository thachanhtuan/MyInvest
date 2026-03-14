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
│    quotes.py        — обновление котировок          │
│    currencies.py    — курсы валют (ЦБР)             │
├─────────────────────────────────────────────────────┤
│  Сервисы (app/services/)                            │
│    import_service.py    — парсинг Excel → ORM       │
│    export_service.py    — генерация Excel-отчётов   │
│    portfolio.py         — расчёт позиций и баланса  │
│    quotes_service.py    — котировки MOEX ISS+Yahoo  │
│    currency_service.py  — курсы валют из ЦБР API    │
├─────────────────────────────────────────────────────┤
│  Модели (app/models.py) — SQLAlchemy ORM            │
│    Account │ Asset │ BondInfo │ Transaction          │
│    AssetValuation │ Currency │ CurrencyRate          │
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

Currency  (справочник: code PK, name, symbol)
    │
    └── CurrencyRate  (курсы к рублю: date, currency → Currency.code, rate, source)
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

**currency_rates** — курсы валют к рублю.

- PK: `id` (autoincrement)
- `currency`: код валюты (3 символа: `"USD"`, `"EUR"`, `"CNY"`)
- `rate`: сколько рублей за 1 единицу валюты
- `source`: источник (`"cbr"`, `"manual"` и т.д.), nullable
- Уникальный составной ключ: `(date, currency)`

**currencies** — справочник поддерживаемых валют.

- PK: `code` (строка 3 символа, например `"USD"`)
- `name`: полное название на русском (`"Доллар США"`)
- `symbol`: символ валюты (`"$"`, `"€"`, `"¥"`), nullable
- Заполняется один раз при создании БД (через миграцию), не меняется при импорте
- Используется как список валют для автоматического запроса курсов у ЦБР

### Правила расчёта (из EXCEL_FORMAT.md)

- `amount`: если заполнен — используется напрямую; если пуст — `quantity × price`
- `total_amount`: если заполнен — используется; если пуст — `amount + commission + nkd` (покупка) или `amount − commission` (продажа)
- **Конвертация валют:** котировки хранятся в `asset_valuations` в валюте актива (USD, EUR, CNY, RUB). При расчёте портфеля стоимость умножается на курс из `currency_rates`, итоговый баланс всегда в рублях.

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
- `quotes_service.py` — получение рыночных котировок (MOEX ISS + Yahoo Finance)
- `currency_service.py` — запрос курсов валют из API Центробанка России

Сервисы получают `Session` как параметр — это облегчает тестирование.

#### Сервис котировок (`quotes_service.py`)

**Точка входа:** `fetch_all_quotes(db) → QuoteResult`

**Шаг 1. Выбор открытых позиций** (`_get_open_positions`)

Из транзакций типа `buy`, `sell`, `initial_balance` суммируется количество по каждому тикеру.
Тикеры с нулевым или отрицательным остатком исключаются.
Для каждой открытой позиции собирается словарь:

```
ticker → {asset_class, exchange, face_value, total_qty, currency, isin}
```

Поле `isin` обязательно — если оно пустое, позиция переходит в ошибки (`"ISIN не заполнен"`).

**Шаг 2. Определение источника котировок** (`_pick_source`)

```
exchange задан?  →  использовать exchange как источник ("yahoo", "moex", ...)
asset_class == stock_foreign?  →  "yahoo"
deposit / cash?  →  None (котировки не нужны, SKIP)
всё остальное  →  "moex"
```

**Шаг 3. Запрос цены по ISIN**

Запрос идёт по `asset.isin` (биржевой ISIN-код), а не по `asset.ticker` (который может быть читаемым названием, например `"ОФЗ 26238"`).

- **MOEX ISS:** `_fetch_moex_price(isin, asset_class, face_value)`
- **Yahoo Finance:** `_fetch_yahoo_price(isin)`

**Шаг 4. Алгоритм выбора цены из MOEX ISS** (`_fetch_moex_price`)

За один HTTP-запрос запрашиваются **две секции**: `marketdata` (реальное время) и `securities` (справочные данные), включая поле `BOARDID` (режим торгов).

**Фильтрация по режиму торгов:** MOEX возвращает несколько строк для одного тикера (разные режимы). Используется приоритет:
- **Акции:** `TQBR` (основной режим Т+)
- **Облигации:** `TQCB` (корпоративные), `TQOB` (ОФЗ), `TQIR` (еврооблигации)
- Fallback: любой режим с ненулевой ценой

Берётся первое ненулевое значение по приоритету полей:

| Приоритет | Секция | Поле | Когда заполнено |
|---|---|---|---|
| 1 | `marketdata` | `LAST` | Последняя сделка — только во время торговой сессии |
| 2 | `marketdata` | `WAPRICE` | Средневзвешенная цена сессии (VWAP) |
| 3 | `securities` | `PREVPRICE` | Цена закрытия **предыдущей** сессии — заполнена всегда |

> `PREVPRICE` находится в секции `securities`, а не в `marketdata`. Запрос `PREVADMITTEDQUOTE` и `CLOSE` из `marketdata` MOEX ISS тихо игнорирует для облигаций — эти поля там не существуют.

`PREVPRICE` — надёжный fallback: это цена закрытия предыдущей торговой сессии, доступная в любое время суток.

Для облигаций MOEX возвращает цену **в процентах от номинала** (например, `96.5`).
Пересчёт в рубли: `price = (raw_price / 100) × face_value`.

В лог записывается исходное поле: `MOEX bond RU000A10B008: PREVADMITTEDQUOTE=96.5%, face=1000.0, price=965.0`.

**Шаг 5. Сохранение** (`_upsert_valuation`)

Рассчитанная стоимость `price × qty` сохраняется в `asset_valuations` с ключом `(date, ticker)`.
Если запись на текущую дату уже есть — обновляется. Сохранение идёт по `ticker` (PK таблицы), а не по ISIN.

#### Сервис курсов валют (`currency_service.py`)

**Точка входа:** `fetch_currency_rates(db, date=None) → CurrencyRateResult`

Параметр `date` — дата, на которую запрашиваются курсы. По умолчанию — `datetime.date.today()`.

**Шаг 1. Список валют из справочника**

Загружаются все записи таблицы `currencies`. Если таблица пуста — возвращается пустой результат без HTTP-запроса.

**Шаг 2. Запрос к API ЦБР** (`_fetch_cbr_xml`)

```
GET https://www.cbr.ru/scripts/XML_daily.asp?date_req=DD/MM/YYYY
```

ЦБР возвращает XML в кодировке **windows-1251** (кодировка объявлена в заголовке `<?xml ...?>`). Для корректного парсинга используется `ET.fromstring(resp.content)` — ElementTree читает кодировку из заголовка XML автоматически.

Структура ответа:

```xml
<ValCurs Date="14.03.2026">
    <Valute>
        <CharCode>USD</CharCode>
        <Nominal>1</Nominal>
        <Name>Доллар США</Name>
        <Value>85,3220</Value>
        <VunitRate>85,3220</VunitRate>
    </Valute>
    ...
</ValCurs>
```

Используется поле **`VunitRate`** — курс уже нормализован к 1 единице валюты (в отличие от `Value`, которое зависит от `Nominal`). Десятичный разделитель — запятая, заменяется на точку перед `float()`.

**Шаг 3. Сохранение** (`_upsert_rate`)

Для каждой валюты из справочника ищется совпадение по `CharCode` в ответе ЦБР.

- Найдена → upsert в `currency_rates` с ключом `(date, currency)`: если запись на эту дату уже есть — `rate` и `source` обновляются; иначе вставляется новая.
- Не найдена → ошибка в `result.errors`.

`source` всегда `"cbr"`. Коммит делается один раз после обработки всех валют.

**API:**

```
POST /api/currencies/rates/refresh?date=YYYY-MM-DD   — запрос курсов (date опционален)
GET  /api/currencies/rates/log                        — просмотр лога
```

**Лог:** `logs/currency_rates.log`

#### Сервис портфеля (`portfolio.py`)

**Точка входа:** `get_portfolio_summary(db) → PortfolioSummary`

Рассчитывает текущее состояние портфеля: позиции по активам, прибыль/убыток, аллокацию по счетам, брокерам, классам активов и валютам.

**Шаг 1. Расчёт позиций** (`_get_holdings`)

Из транзакций типа `buy`, `sell`, `initial_balance` агрегируется количество по каждому тикеру в разрезе счетов. Позиции с нулевым или отрицательным остатком исключаются.

**Шаг 2. Загрузка котировок и курсов валют**

Запрашиваются две справочные таблицы:

1. **Последние котировки** — из `asset_valuations` выбирается последняя запись по каждому тикеру (max date). Котировка хранится **в валюте актива** (например, облигация с номиналом USD хранит стоимость в USD).

2. **Последние курсы валют** — из `currency_rates` выбирается последний курс по каждой валюте (max date). Курсы хранят "сколько рублей за 1 единицу валюты".

```python
latest_rates: dict[str, float] = {"RUB": 1.0}  # RUB всегда = 1
# Загружаем USD, EUR, CNY, ...
```

**Шаг 3. Расчёт стоимости в рублях с конвертацией валюты**

Для каждой позиции:

1. Берётся `value` из `asset_valuations` (стоимость позиции в валюте актива)
2. Если позиция на нескольких счетах — стоимость пропорционально распределяется по количеству
3. **Конвертация в рубли:**
   ```python
   val_currency = val.currency or asset.currency or "RUB"
   rate = latest_rates.get(val_currency, 1.0)
   current_value = value_in_asset_currency * rate
   ```
4. Если курс валюты не найден (не загружен из ЦБР) — rate = 1.0 (без конвертации)

**Пример:**
- Облигация с номиналом 100 USD
- MOEX отдал цену 92% → `value = 92.0` USD (сохранено в `asset_valuations.value`)
- Курс USD: `rate = 85.5` RUB (из `currency_rates`)
- Стоимость в рублях: `92.0 × 85.5 = 7866 RUB`

**Шаг 4. Агрегация по измерениям**

Из массива позиций строятся сводки:
- **По счетам** (`AccountSummary`) — с учётом типа счёта (broker/iis/deposit/savings)
- **По брокерам** (`BrokerSummary`)
- **По классам активов** (`AssetClassSummary`)
- **По валютам** (`CurrencySummary`) — использует `asset.currency`, а не `current_value` (итоговая стоимость уже в RUB)

Депозиты и сберегательные счета без активов включаются в итоги по балансу наличности (`deposit_in`, `deposit_out`, `interest`).

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
- `MOEX_ISS_BASE_URL` — базовый URL MOEX ISS API
- `CBR_API_URL` — URL ЦБР для XML-выгрузки курсов валют
- `QUOTES_LOG_FILE`, `IMPORT_LOG_FILE`, `EXPORT_LOG_FILE`, `APP_LOG_FILE`, `CURRENCY_RATES_LOG_FILE` — пути к лог-файлам

## Тестирование

- Фреймворк: pytest
- Фикстура `db_session` — in-memory SQLite, отдельная для каждого теста
- Фикстура `client` — TestClient с подменой зависимости `get_db`
- Фикстура `sample_data` — минимальный набор данных для unit-тестов

## Планируемые расширения

| Фаза | Описание                                 | Новые файлы                                        |
| ---- | ---------------------------------------- | -------------------------------------------------- |
| 4    | Доходность, графики стоимости во времени | расширение `portfolio.py`, новые Chart.js графики  |
| 5    | Лестница облигаций, купонный календарь   | `services/bond_service.py`, `templates/bonds.html` |
| 6    | CRUD через UI, импорт с дедупликацией    | формы в шаблонах, upsert в `import_service.py`     |
