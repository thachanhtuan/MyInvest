# Copilot Instructions — MyInvest

## О проекте

MyInvest — локальное веб-приложение для учёта личных инвестиций на российском рынке.  
Python 3.12, FastAPI, SQLAlchemy 2.0, Jinja2 SSR, SQLite, Bootstrap 5.

---

## Архитектура и слои

- **`app/main.py`** — FastAPI-приложение, lifespan, маршруты страниц (Jinja2 SSR).
- **`app/routers/`** — REST API (`/api/...`), по одному файлу на сущность.
- **`app/services/`** — бизнес-логика (расчёты портфеля, загрузка котировок, Excel).
- **`app/models.py`** — ORM-модели SQLAlchemy (8 таблиц).
- **`app/schemas.py`** — Pydantic-схемы (`*Create`, `*Update`, `*Out`).
- **`app/database.py`** — подключение к SQLite, `get_db()`.
- **`templates/`** — Jinja2-шаблоны, `base.html` — базовый layout.
- **`static/`** — CSS и JS (Bootstrap 5, Chart.js, vanilla JS).
- **`tests/`** — pytest, in-memory SQLite.

---

## Соглашения по коду

### Python

- Версия Python: **3.12**.
- Типизация: использовать аннотации типов для аргументов функций и возвращаемых значений.
- ORM: **SQLAlchemy 2.0** (Mapped[], mapped_column()), декларативная база.
- Валидация: **Pydantic v2** (ConfigDict(from_attributes=True)).
- Асинхронность: роутеры и сервисы используют `async def` по необходимости; `httpx.AsyncClient` для внешних запросов.
- Зависимости: `Depends(get_db)` для получения сессии БД в роутерах.

### Именование

- Файлы роутеров — множественное число: `accounts.py`, `assets.py`, `transactions.py`.
- Pydantic-схемы: `{Entity}Create`, `{Entity}Update`, `{Entity}Out`.
- ORM-модели: единственное число с CamelCase: `Account`, `Asset`, `Transaction`.
- Таблицы: генерируются SQLAlchemy автоматически из имени класса.

### Структура API

- Префикс: `/api/{ресурс}` (например, `/api/accounts`).
- CRUD: GET (список), POST (создание), PUT (обновление), DELETE (удаление).
- Возвращаемые данные: Pydantic `*Out`-схемы.
- Ошибки: `HTTPException` с кодами 404, 400 и т.д.

### Frontend

- Шаблоны: Jinja2, наследование от `base.html` через `{% extends "base.html" %}`.
- CSS-фреймворк: Bootstrap 5 (CDN, не устанавливается локально).
- Графики: Chart.js (CDN).
- JavaScript: vanilla JS, fetch-запросы к REST API для CRUD-операций.
- Стили: минимальные кастомные стили в `static/css/style.css`.

---

## База данных

- **SQLite** — файл `myinvest.db` в корне проекта.
- Таблицы создаются автоматически через `Base.metadata.create_all()`.
- Миграции (Alembic) **не используются**.
- `AssetValuation.value` — это **общая стоимость** позиции от брокера, а не цена за единицу. Использовать напрямую как `market_value`, не умножать на количество.

---

## Внешние API

- **MOEX ISS API** (`https://iss.moex.com`) — единственный внешний сервис.
- Бесплатный, без регистрации и API-ключей.
- Клиент: `httpx.AsyncClient` в `app/services/market_data.py`.
- Конвертация валют **не выполняется** — все расчёты в валюте актива.

---

## Тестирование

```bash
python -m pytest tests/ -v
```

- Фреймворк: **pytest** + **pytest-asyncio**.
- Фикстура `db` (conftest.py): создаёт in-memory SQLite сессию для каждого теста.
- Тесты моделей: `tests/test_models.py`.
- Тесты аналитики: `tests/test_analytics.py`.

---

## Запуск

```bash
pip install -r requirements.txt
python run.py
```

Приложение доступно на `http://127.0.0.1:8000`.  
API-документация: `/docs` (Swagger) и `/redoc` (ReDoc).

---

## Что учитывать при генерации кода

1. **Язык документации и комментариев** — русский (по контексту; код на английском).
2. **Новые модели** — добавлять в `app/models.py`, схемы — в `app/schemas.py`.
3. **Новые эндпоинты** — создавать роутер в `app/routers/`, подключать в `app/main.py`.
4. **Бизнес-логика** — выносить в `app/services/`, не помещать в роутеры.
5. **Новые страницы** — шаблон в `templates/`, наследование от `base.html`, маршрут в `main.py`.
6. **Зависимости** — добавлять в `requirements.txt`.
7. **Тесты** — добавлять в `tests/`, использовать фикстуру `db`.
8. **Excel** — при добавлении новых сущностей обновлять `excel_service.py` и `docs/EXCEL_FORMAT.md`.
