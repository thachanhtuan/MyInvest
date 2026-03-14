# Требования к коду MyInvest

Правила и соглашения, которых следует придерживаться при разработке проекта.

## Язык и стиль

### Python

- **Версия**: 3.12+ (используем `from __future__ import annotations` в каждом файле)
- **Форматирование**: стандартный PEP 8, длина строки 100 символов
- **Импорты**: сначала stdlib, затем third-party, затем проект (`app.`); разделять пустой строкой
- **Type hints**: обязательны для аргументов функций и возвращаемых значений
- **Nullable-типы**: синтаксис `str | None`, не `Optional[str]`

```python
from __future__ import annotations

import datetime                          # stdlib
from pathlib import Path

from sqlalchemy.orm import Session       # third-party

from app.models import Account           # project
```

### SQL / ORM

- **SQLAlchemy 2.0 Mapped-синтаксис** для моделей:
  ```python
  class Account(Base):
      __tablename__ = "accounts"
      id: Mapped[str] = mapped_column(String, primary_key=True)
  ```
- **Не использовать** устаревший `Query.get()` — заменять на `db.get(Model, pk)`
- **Дата** в моделях: `datetime.date` (не строки). Преобразование из Excel — через `_cell_to_date()`

### JavaScript

- **Vanilla JS** — без фреймворков (React, Vue, Angular)
- `const` по умолчанию, `let` при необходимости, никогда `var`
- `async/await` вместо `.then()`-цепочек
- Все строки для вставки в DOM — через `escapeHtml()` (защита от XSS)

### HTML / Jinja2

- Все шаблоны наследуют `base.html` через `{% extends "base.html" %}`
- Блоки: `{% block title %}`, `{% block content %}`, `{% block scripts %}`
- Фильтры для вывода данных:
  - `{{ value|money }}` — форматирование денег с символом валюты
  - `{{ value|pct }}` — процент с `+`/`-`
  - `{{ value|fdate }}` — дата в формате `ДД.ММ.ГГГГ`

## Архитектурные правила

### Слои

| Слой    | Каталог          | Знает о                   | Не знает о              |
| ------- | ---------------- | ------------------------- | ----------------------- |
| Роутеры | `app/routers/`   | Сервисах, моделях, схемах | —                       |
| Сервисы | `app/services/`  | Моделях                   | HTTP, Request, Response |
| Модели  | `app/models.py`  | SQLAlchemy Base           | Сервисах, роутерах      |
| Схемы   | `app/schemas.py` | Pydantic                  | Моделях, сервисах       |

**Главное правило**: сервисы получают `Session` как параметр и не зависят от FastAPI. Это позволяет вызывать их из тестов без HTTP-контекста.

### Роутеры

- Тонкие: принять запрос → вызвать сервис или простой запрос → вернуть ответ
- HTML-страницы — в `pages.py`, API-эндпоинты — в остальных файлах
- Все API-маршруты начинаются с `/api/`
- HTML-маршруты не имеют префикса (`/`, `/accounts`, `/import`)

### Сервисы

- Бизнес-логика без привязки к HTTP
- Принимают `db: Session` первым аргументом
- Возвращают Pydantic-модели или примитивы, не ORM-объекты напрямую (в аналитике)
- Логируют ключевые операции через `logging.getLogger(__name__)`

### Модели

- Все наследуют `app.database.Base`
- Первичные ключи:
  - `Account.id` и `Asset.ticker` — строковые (бизнес-идентификаторы)
  - Остальные — `Integer` с `autoincrement`
- Связи (`relationship`) — двунаправленные с `back_populates`
- Enum-значения хранятся как `String` в БД (не Python Enum) — валидация в Pydantic

## Работа с данными

### Excel-импорт

- Имена листов — русские, определены в `app/config.py → SHEET_NAMES`
- Стратегия: полная очистка + повторная вставка (replace)
- Порядок вставки (из-за FK): `Account → Asset → BondInfo → Transaction → AssetValuation`
- Преобразование типов:
  - `datetime.datetime` → `datetime.date`
  - `"true"/"false"` → `bool`
  - Пустая ячейка → `None`
- Вычисляемые поля (`amount`, `total_amount`) — по правилам из `docs/EXCEL_FORMAT.md`

### Расчёт позиций

- Позиции не хранятся в БД — вычисляются динамически из транзакций
- Ключ позиции: `(account_id, ticker)`
- Текущая стоимость: из последней записи `AssetValuation` по тикеру
- Если `AssetValuation` нет — стоимость = вложения (без прибыли/убытка)

## Фронтенд

### CDN-зависимости (без локальных копий)

- Bootstrap 5.3.x — стили и компоненты
- Bootstrap Icons — иконки в навигации
- Chart.js 4.x — графики

### Структура страницы

- Sidebar (240px, тёмный фон) с навигацией
- Основная область (`flex-grow-1`, светлый фон `#f8f9fa`)
- `#alert-area` — контейнер для уведомлений

### Дашборд

- Данные загружаются асинхронно через `fetchJSON('/api/analytics/summary')`
- Три состояния: loading → empty (нет данных) → content
- Графики рендерятся функцией `renderPieChart()` из `app.js`

## Тестирование

### Структура

```
tests/
├── conftest.py           # Фикстуры: db_session, client, sample_data
├── test_import.py        # Тесты импорта Excel
└── test_portfolio.py     # Тесты расчёта портфеля
```

### Правила

- Каждый тест использует свою in-memory SQLite БД (фикстура `db_session`)
- Тесты не зависят друг от друга и не разделяют состояние
- Даты в тестовых данных — объекты `datetime.date(...)`, не строки
- При отсутствии `data.xlsx` — тесты с реальными данными пропускаются (`pytest.skip`)

### Фикстуры

| Фикстура      | Назначение                                                                    |
| ------------- | ----------------------------------------------------------------------------- |
| `db_session`  | Чистая in-memory SQLite сессия                                                |
| `client`      | `TestClient` с подменой `get_db`                                              |
| `sample_data` | Сессия с минимальным набором данных (1 счёт, 1 актив, 1 транзакция, 1 оценка) |

## Миграции

- `alembic/env.py` настроен на `render_as_batch=True` (необходимо для SQLite)
- Модели импортируются в `env.py` для поддержки автогенерации
- Новая миграция: `uv run alembic revision --autogenerate -m "описание"`
- Применение: `uv run alembic upgrade head`

## Безопасность

- XSS: все пользовательские строки в DOM — через `escapeHtml()`
- SQL Injection: используется ORM с параметризованными запросами, raw SQL запрещён
- Загрузка файлов: проверка расширения `.xlsx`, временный файл удаляется после обработки
- Приложение работает локально — аутентификация не требуется

## Именование

| Сущность          | Соглашение                        | Пример                  |
| ----------------- | --------------------------------- | ----------------------- |
| Python-файлы      | `snake_case`                      | `import_service.py`     |
| Классы            | `PascalCase`                      | `AssetValuation`        |
| Функции           | `snake_case`                      | `get_portfolio_summary` |
| Приватные функции | `_snake_case`                     | `_compute_amount`       |
| Таблицы БД        | `snake_case`, множественное число | `asset_valuations`      |
| API-маршруты      | `/api/{ресурс}/`                  | `/api/accounts/`        |
| HTML-маршруты     | `/{страница}`                     | `/transactions`         |
| Jinja2-шаблоны    | `snake_case.html`                 | `import.html`           |
| JS-функции        | `camelCase`                       | `formatMoney`           |
| CSS-классы        | Bootstrap 5 утилиты               | `text-success`, `mb-4`  |

## Язык интерфейса

- Весь UI на **русском языке** — заголовки, метки, подписи, уведомления
- Код, комментарии, имена переменных, git-сообщения — на **английском**
- Справочники с русскими лейблами: `ASSET_CLASS_LABELS`, `TX_TYPE_LABELS` в `schemas.py`
