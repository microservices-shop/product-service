# Product Service

Микросервис каталога товаров для интернет-магазина электроники. Отвечает за управление товарами, категориями, динамическими атрибутами и резервированием остатков.

## Технологический стек

| Технология | Версия | Назначение |
|---|---|---|
| Python | 3.12 | Язык разработки |
| FastAPI | 0.128.0 | Web-фреймворк |
| SQLAlchemy | 2.0.45 | ORM |
| PostgreSQL | 18 | База данных |
| Alembic | 1.18.0 | Миграции БД |
| asyncpg | 0.31.0 | Асинхронный драйвер PostgreSQL |
| Pydantic | 2.12.5 | Валидация данных |
| FastStream | ≥ 0.6.7 | Брокер сообщений (RabbitMQ) |
| httpx | 0.28.1 | HTTP-клиент для межсервисного взаимодействия |
| Loguru | 0.7.3 | Логирование |
| Uvicorn | 0.40.0 | ASGI-сервер |
| Ruff | 0.14.5 | Линтер и форматтер |
| pytest | — | Тестирование |

## Структура проекта

```
product-service/
├── src/
│   ├── main.py              # Точка входа, фабрика приложения
│   ├── config.py            # Конфигурация (pydantic-settings)
│   ├── exceptions.py        # Кастомные исключения
│   ├── logging.py           # Настройка логирования (Loguru)
│   ├── utils.py             # Утилиты
│   ├── api/
│   │   ├── auth.py          # Авторизация (X-User-Role)
│   │   ├── dependencies.py  # Dependency Injection (сервисы, сессии)
│   │   ├── v1/              # Публичный API v1
│   │   │   ├── router.py        # Агрегирующий роутер v1
│   │   │   ├── products.py      # Эндпоинты товаров
│   │   │   ├── categories.py    # Эндпоинты категорий
│   │   │   └── attributes.py    # Эндпоинты атрибутов
│   │   └── internal/        # Internal API (межсервисное взаимодействие)
│   │       ├── router.py        # Агрегирующий роутер internal
│   │       └── products.py      # Резервирование товаров
│   ├── db/
│   │   ├── database.py      # Async engine и session factory
│   │   ├── models.py        # SQLAlchemy-модели
│   │   └── enums.py         # Перечисления (ProductStatus, AttributeType)
│   ├── repositories/        # Слой доступа к данным (Repository pattern)
│   │   ├── products.py
│   │   ├── categories.py
│   │   ├── attributes.py
│   │   └── reservations.py
│   ├── services/            # Бизнес-логика (Service layer)
│   │   ├── products.py
│   │   ├── categories.py
│   │   ├── attributes.py
│   │   ├── reservations.py
│   │   └── cart_webhook.py
│   ├── schemas/             # Pydantic-схемы
│   │   ├── products.py
│   │   ├── categories.py
│   │   ├── attributes.py
│   │   ├── internal.py
│   │   └── common.py
│   ├── messaging/           # Интеграция с RabbitMQ (FastStream)
│   │   ├── broker.py        # Экземпляр RabbitBroker
│   │   ├── consumers.py     # Обработчики сообщений
│   │   └── schemas.py       # Схемы сообщений
│   └── integrations/        # Интеграции с внешними сервисами
├── alembic/                 # Миграции базы данных
│   ├── env.py
│   └── versions/            # Файлы миграций
├── tests/                   # Тесты
│   ├── unit/                # Юнит-тесты (моки БД)
│   └── integration/         # Интеграционные тесты (реальная БД)
├── Dockerfile
├── docker-compose.yml       # Production-конфигурация
├── docker-compose.dev.yml   # Dev-конфигурация (БД + мигратор + приложение)
├── docker-compose.test.yml  # Тестовая БД для интеграционных тестов
├── alembic.ini              # Конфигурация Alembic
├── requirements.txt
├── pyproject.toml           # Настройки Ruff и pytest
└── .pre-commit-config.yaml  # Pre-commit хуки (Ruff)
```

## Архитектура

Сервис построен на **трёхслойной архитектуре**:

```
API (роутеры) → Service (бизнес-логика) → Repository (доступ к данным)
```

- **API слой** — обработка HTTP-запросов, валидация входных данных, авторизация.
- **Service слой** — бизнес-логика, оркестрация операций, обработка ошибок.
- **Repository слой** — работа с БД через SQLAlchemy (async).

**Dependency Injection** реализован через FastAPI `Depends()` с типизированными аннотациями (`Annotated`).

## API

Сервис запускается на порту **8002**. Интерактивная документация доступна по адресу `http://localhost:8002/docs` (Swagger UI).

### Публичный API (`/api/v1`)

#### Товары (`/api/v1/products`)

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| `GET` | `/api/v1/products` | Список товаров (пагинация, сортировка, фильтрация по цене, категории, поиск по названию) | Публичный |
| `GET` | `/api/v1/products/{id}` | Детальная информация о товаре | Публичный |
| `POST` | `/api/v1/products` | Создать товар | Админ |
| `PATCH` | `/api/v1/products/{id}` | Обновить товар (частичное обновление) | Админ |
| `DELETE` | `/api/v1/products/{id}` | Удалить товар | Админ |

#### Категории (`/api/v1/categories`)

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| `GET` | `/api/v1/categories` | Список всех категорий | Публичный |
| `GET` | `/api/v1/categories/{id}` | Категория по ID | Публичный |
| `GET` | `/api/v1/categories/{id}/attributes` | Атрибуты категории | Публичный |
| `POST` | `/api/v1/categories` | Создать категорию | Админ |
| `PATCH` | `/api/v1/categories/{id}` | Обновить категорию | Админ |
| `DELETE` | `/api/v1/categories/{id}` | Удалить категорию | Админ |

#### Атрибуты (`/api/v1/attributes`)

| Метод | Путь | Описание | Доступ |
|---|---|---|---|
| `GET` | `/api/v1/attributes` | Список атрибутов (фильтр по категории) | Публичный |
| `GET` | `/api/v1/attributes/{id}` | Атрибут по ID | Публичный |
| `POST` | `/api/v1/attributes` | Создать атрибут | Публичный |
| `PATCH` | `/api/v1/attributes/{id}` | Обновить атрибут | Публичный |
| `DELETE` | `/api/v1/attributes/{id}` | Удалить атрибут | Публичный |

### Internal API (`/internal`)

Эндпоинты для межсервисного взаимодействия (используются Order Service).

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/internal/products/{id}` | Получить товар по ID |
| `POST` | `/internal/products/reserve` | Резервирование товаров (атомарное уменьшение stock) |
| `POST` | `/internal/products/confirm-reserve` | Подтверждение резерва |
| `POST` | `/internal/products/cancel-reserve` | Отмена резерва (восстановление stock) |

### Системные эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/health` | Health check |

## Очередь сообщений (RabbitMQ)

Сервис использует **FastStream** с RabbitMQ для асинхронной обработки событий.

| Очередь | Описание |
|---|---|
| `product.reserve.release` | Освобождение резерва по `order_id` (вызывается при отмене/истечении заказа) |

## Запуск

### Переменные окружения

Скопируйте `.env.example` в `.env` и настройте значения:

```bash
cp .env.example .env
```

```env
DB_HOST=localhost
DB_PORT=5433
DB_USER=product_service_user
DB_PASS=temppassword
DB_NAME=product_service

CART_SERVICE_URL=http://localhost:8003

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# SQLAdmin OAuth Authentication
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SESSION_SECRET_KEY=your-random-session-secret-key
AUTH_SERVICE_URL=http://localhost:8001
```

### Запуск через Docker Compose (production)

Поднимает PostgreSQL, автоматически выполняет миграции через **отдельный контейнер `migrator`** и запускает приложение:

```bash
docker compose up --build
```

> **Примечание:** Миграции Alembic выполняются автоматически — контейнер `migrator` запускает `alembic upgrade head` перед стартом приложения. Приложение (`app`) стартует только после успешного завершения миграций (`service_completed_successfully`).

Сервис будет доступен по адресу `http://localhost:8002`.

### Запуск для локальной разработки

1. **Поднять базу данных и выполнить миграции:**

```bash
docker compose -f docker-compose.dev.yml up --build
```

2. **Создать виртуальное окружение и установить зависимости:**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

3. **Запустить приложение:**

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload
```

## Тестирование

Проект содержит два вида тестов: **юнит-тесты** и **интеграционные тесты**.

### Юнит-тесты

Тестируют бизнес-логику (Service layer) в изоляции от базы данных с помощью моков (`unittest.mock`).

**Покрытие:**

| Модуль | Файл теста | Что проверяется |
|---|---|---|
| `ProductService` | `test_product_service.py` | CRUD товаров, пагинация, сортировка, фильтрация, webhook-уведомления |
| `CategoryService` | `test_category_service.py` | CRUD категорий, удаление с проверкой связанных товаров |
| `AttributeService` | `test_attribute_service.py` | CRUD атрибутов, фильтрация по категории |
| `ReservationService` | `test_reservation_service.py` | Резервирование, отмена резерва, атомарность операций |
| `CartWebhookService` | `test_cart_webhook.py` | Отправка webhook'ов при изменении/удалении товаров |
| Pydantic-схемы | `test_schemas.py` | Валидация входных/выходных данных |
| Утилиты | `test_utils.py` | Вспомогательные функции |

**Запуск юнит-тестов:**

```bash
pytest tests/unit -v
```

### Интеграционные тесты

Тестируют API-эндпоинты с реальной базой данных PostgreSQL. Используют `httpx.AsyncClient` + `ASGITransport` для запросов к FastAPI-приложению.

**Особенности:**
- Схема БД создаётся через **Alembic-миграции** (фикстура `_apply_migrations`)
- Таблицы очищаются (`TRUNCATE CASCADE`) после каждого теста
- RabbitMQ-брокер замокан (тесты не зависят от очереди сообщений)

**Покрытие:**

| Файл теста | Что проверяется |
|---|---|
| `test_products_api.py` | CRUD товаров через API, пагинация, фильтрация, авторизация |
| `test_categories_api.py` | CRUD категорий через API, авторизация, каскадные проверки |
| `test_attributes_api.py` | CRUD атрибутов через API, привязка к категориям |
| `test_internal_api.py` | Internal API: резервирование, подтверждение, отмена, атомарность |

**Запуск интеграционных тестов:**

1. **Поднять тестовую БД:**

```bash
docker compose -f docker-compose.test.yml up -d
```

2. **Запустить тесты:**

```bash
pytest tests/integration -v
```

### Запуск всех тестов

```bash
# Поднять тестовую БД (если не запущена)
docker compose -f docker-compose.test.yml up -d

# Запустить все тесты
pytest -v

# С отчётом о покрытии
pytest --cov=src --cov-report=term-missing
```

## Авторизация

Эндпоинты, требующие роль администратора, проверяют заголовок `X-User-Role`. Заголовок устанавливается API Gateway при проксировании запросов. Если заголовок отсутствует или значение отличается от `admin`, возвращается ответ `403 Forbidden`.

## Линтинг

Проект использует **Ruff** для линтинга и форматирования кода. Настроен pre-commit hook для автоматической проверки при коммитах.

```bash
# Проверка
ruff check .

# Автоисправление
ruff check --fix .

# Форматирование
ruff format .
```