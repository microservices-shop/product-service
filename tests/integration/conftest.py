"""Фикстуры для интеграционных тестов."""

import os
import subprocess
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.db.database import Base
from src.api.dependencies import get_db


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5434/product_test_db",
)


# ── БД: schema через Alembic ─────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations():
    """
    Применяет Alembic-миграции к тестовой БД (один раз на сессию).
    """
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    env = os.environ.copy()
    env["DB_HOST"] = "localhost"
    env["DB_PORT"] = "5434"
    env["DB_USER"] = "test_user"
    env["DB_PASS"] = "test_pass"
    env["DB_NAME"] = "product_test_db"

    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=project_root,
        env=env,
        check=False,
    )

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Alembic upgrade failed:\n{result.stdout}\n{result.stderr}")


# ── Очистка таблиц + engine per test ─────────────────────────────────────────


@pytest.fixture
async def _test_engine():
    """Async engine для тестовой БД (per-test)."""
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
    await engine.dispose()


@pytest.fixture
def test_session_factory(_test_engine):
    """Фабрика сессий для тестовой БД."""
    return async_sessionmaker(_test_engine, expire_on_commit=False)


# ── Тестовое приложение + httpx клиент ────────────────────────────────────────


@pytest.fixture
async def client(test_session_factory, mocker):
    """
    httpx.AsyncClient с тестовым приложением FastAPI.
    """
    mock_broker = mocker.patch("src.main.broker")
    mock_broker.connect = AsyncMock()
    mock_broker.start = AsyncMock()
    mock_broker.close = AsyncMock()
    mock_broker.include_router = MagicMock()
    mocker.patch("src.main.consumers")

    from src.main import create_app

    app = create_app()

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Вспомогательные фикстуры ─────────────────────────────────────────────────


@pytest.fixture
def admin_headers():
    """Заголовки для авторизованных запросов (admin)."""
    return {"X-User-Role": "admin"}


@pytest.fixture
async def created_category(client, admin_headers):
    """Предсоздать категорию через API. Возвращает JSON ответа."""
    response = await client.post(
        "/api/v1/categories",
        json={"title": "Смартфоны"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def created_product(client, admin_headers, created_category):
    """Предсоздать товар через API. Возвращает JSON ответа."""
    response = await client.post(
        "/api/v1/products",
        json={
            "title": "iPhone 15 Pro",
            "price": 99990,
            "category_id": created_category["id"],
            "description": "Тестовый товар",
            "stock": 10,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
