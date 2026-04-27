"""Общие фикстуры для юнит-тестов."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from src.db.models import ProductModel, CategoryModel, AttributeModel
from src.db.enums import ProductStatus, AttributeType


@pytest.fixture
def mock_session():
    """AsyncMock для AsyncSession — заглушка базы данных."""
    return AsyncMock()


@pytest.fixture
def make_category():
    """Фабрика для создания экземпляров CategoryModel."""

    def _factory(id=1, title="Смартфоны"):
        category = CategoryModel()
        category.id = id
        category.title = title
        return category

    return _factory


@pytest.fixture
def make_product():
    """Фабрика для создания экземпляров ProductModel."""

    def _factory(
        id=1,
        title="iPhone 15 Pro",
        price=99990,
        category_id=1,
        description="Тестовый товар",
        images=None,
        stock=10,
        status=ProductStatus.ACTIVE,
        attributes=None,
        created_at=None,
        updated_at=None,
    ):
        product = ProductModel()
        product.id = id
        product.title = title
        product.price = price
        product.category_id = category_id
        product.description = description
        product.images = (
            images if images is not None else ["https://example.com/img.jpg"]
        )
        product.stock = stock
        product.status = status
        product.attributes = attributes if attributes is not None else {}
        product.created_at = created_at or datetime(2025, 1, 1)
        product.updated_at = updated_at or datetime(2025, 1, 1)
        return product

    return _factory


@pytest.fixture
def make_attribute():
    """Фабрика для создания экземпляров AttributeModel."""

    def _factory(
        id=1,
        category_id=1,
        title="Цвет",
        type=AttributeType.STRING,
        required=False,
    ):
        attr = AttributeModel()
        attr.id = id
        attr.category_id = category_id
        attr.title = title
        attr.type = type
        attr.required = required
        return attr

    return _factory
