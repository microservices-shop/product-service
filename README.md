# Product Service

Микросервис каталога товаров для интернет-магазина электроники. Отвечает за управление товарами, категориями и динамическими атрибутами товаров.

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
| SQLAdmin | 0.20.1 | Админ-панель |
| Loguru | 0.7.3 | Логирование |
| Uvicorn | 0.40.0 | ASGI-сервер |

## Структура проекта

```
product-service/
├── src/
│   ├── main.py              # Точка входа, фабрика приложения
│   ├── config.py            # Конфигурация (переменные окружения)
│   ├── exceptions.py        # Кастомные исключения
│   ├── logging.py           # Настройка логирования
│   ├── utils.py             # Утилиты
│   ├── admin/               # Админ-панель (SQLAdmin)
│   ├── api/
│   │   ├── dependencies.py  # Dependency Injection (сервисы, сессии)
│   │   ├── v1/              # Публичный API v1
│   │   │   ├── products.py      # Эндпоинты товаров
│   │   │   ├── categories.py    # Эндпоинты категорий
│   │   │   └── attributes.py    # Эндпоинты атрибутов
│   │   └── internal/        # Internal API (межсервисное взаимодействие)
│   │       └── products.py      # Резервирование товаров
│   ├── db/                  # Настройка БД и модели
│   ├── repositories/        # Слой доступа к данным
│   ├── schemas/             # Pydantic-схемы
│   ├── services/            # Бизнес-логика
│   └── integrations/        # Интеграции с другими сервисами
├── alembic/                 # Миграции базы данных
├── tests/                   # Тесты
├── Dockerfile
├── docker-compose.yml       # Production-конфигурация
├── docker-compose.dev.yml   # Dev-конфигурация (только БД)
├── requirements.txt
└── pyproject.toml           # Настройки Ruff (линтер)
```

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

Эндпоинты для межсервисного взаимодействия (используются, например, Order Service).

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/internal/products/{id}` | Получить товар по ID |
| `POST` | `/internal/products/reserve` | Резервирование товаров (атомарное уменьшение stock) |
| `POST` | `/internal/products/confirm-reserve` | Подтверждение резерва |
| `POST` | `/internal/products/cancel-reserve` | Отмена резерва (восстановление stock) |

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
```

### Запуск через Docker Compose (production)

Поднимает PostgreSQL, выполняет миграции и запускает приложение:

```bash
docker compose up --build
```

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

### Миграции базы данных

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание миграции"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

## Авторизация

Эндпоинты, требующие роль администратора, проверяют заголовок `X-User-Role`. Если значение заголовка отличается от `admin`, возвращается ответ `403 Forbidden`. Если заголовок не передан — доступ разрешён (обратная совместимость до внедрения API Gateway).

## Админ-панель

SQLAdmin доступна по адресу `http://localhost:8002/admin` и позволяет управлять данными через веб-интерфейс.