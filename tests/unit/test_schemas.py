"""Юнит-тесты для Pydantic-схем валидации."""

import uuid

import pytest
from pydantic import ValidationError

from src.schemas.products import ProductCreateSchema, ProductUpdateSchema
from src.schemas.categories import CategoryCreateSchema, CategoryUpdateSchema
from src.schemas.internal import ReserveItemSchema, ReserveRequestSchema
from src.schemas.common import PaginationParams


# ── ProductCreateSchema ──────────────────────────────────────────────────────


class TestProductCreateSchema:
    """Тесты для ProductCreateSchema."""

    def test_valid_minimal_fields(self):
        """Создание с минимальным набором обязательных полей."""
        schema = ProductCreateSchema(title="iPhone 15", price=99990, category_id=1)
        assert schema.title == "Iphone 15"  # capitalize
        assert schema.price == 99990
        assert schema.category_id == 1
        assert schema.images == []
        assert schema.stock == 0
        assert schema.attributes == {}

    def test_valid_all_fields(self):
        """Создание с полным набором полей."""
        schema = ProductCreateSchema(
            title="iPhone 15",
            price=99990,
            category_id=1,
            description="Описание",
            images=["https://example.com/img.jpg"],
            stock=50,
            attributes={"color": "black"},
        )
        assert schema.description == "Описание"
        assert schema.stock == 50
        assert len(schema.images) == 1

    def test_negative_price_raises(self):
        """Отрицательная цена — ValidationError."""
        with pytest.raises(ValidationError):
            ProductCreateSchema(title="Test", price=-1, category_id=1)

    def test_zero_price_valid(self):
        """Нулевая цена допустима (ge=0)."""
        schema = ProductCreateSchema(title="Free item", price=0, category_id=1)
        assert schema.price == 0

    def test_title_normalization(self):
        """Название нормализуется: strip() + capitalize()."""
        schema = ProductCreateSchema(title="  test product  ", price=100, category_id=1)
        assert schema.title == "Test product"

    def test_empty_title_raises(self):
        """Пустое название — ошибка."""
        with pytest.raises((ValidationError, ValueError)):
            ProductCreateSchema(title="", price=100, category_id=1)

    def test_spaces_only_title_raises(self):
        """Название из одних пробелов — ошибка."""
        with pytest.raises((ValidationError, ValueError)):
            ProductCreateSchema(title="   ", price=100, category_id=1)

    def test_category_id_zero_raises(self):
        """category_id=0 — ValidationError (gt=0)."""
        with pytest.raises(ValidationError):
            ProductCreateSchema(title="Test", price=100, category_id=0)

    def test_category_id_negative_raises(self):
        """Отрицательный category_id — ValidationError."""
        with pytest.raises(ValidationError):
            ProductCreateSchema(title="Test", price=100, category_id=-1)


# ── ProductUpdateSchema ──────────────────────────────────────────────────────


class TestProductUpdateSchema:
    """Тесты для ProductUpdateSchema."""

    def test_all_fields_optional(self):
        """Все поля опциональны — пустой объект валиден."""
        schema = ProductUpdateSchema()
        assert schema.title is None
        assert schema.price is None
        assert schema.category_id is None

    def test_title_normalization(self):
        """Название нормализуется при обновлении."""
        schema = ProductUpdateSchema(title="  updated name  ")
        assert schema.title == "Updated name"

    def test_none_title_stays_none(self):
        """None не нормализуется."""
        schema = ProductUpdateSchema(title=None)
        assert schema.title is None

    def test_negative_price_raises(self):
        """Отрицательная цена при обновлении — ValidationError."""
        with pytest.raises(ValidationError):
            ProductUpdateSchema(price=-10)


# ── CategoryCreateSchema ─────────────────────────────────────────────────────


class TestCategoryCreateSchema:
    """Тесты для CategoryCreateSchema."""

    def test_valid(self):
        """Валидная категория."""
        schema = CategoryCreateSchema(title="Смартфоны")
        assert schema.title == "Смартфоны"

    def test_title_normalization(self):
        """Нормализация названия категории."""
        schema = CategoryCreateSchema(title="  ноутбуки  ")
        assert schema.title == "Ноутбуки"

    def test_empty_title_raises(self):
        """Пустое название — ошибка."""
        with pytest.raises((ValidationError, ValueError)):
            CategoryCreateSchema(title="")

    def test_spaces_only_raises(self):
        """Название из одних пробелов — ошибка."""
        with pytest.raises((ValidationError, ValueError)):
            CategoryCreateSchema(title="   ")


# ── CategoryUpdateSchema ─────────────────────────────────────────────────────


class TestCategoryUpdateSchema:
    """Тесты для CategoryUpdateSchema."""

    def test_all_fields_optional(self):
        """Все поля опциональны."""
        schema = CategoryUpdateSchema()
        assert schema.title is None

    def test_title_normalization(self):
        """Нормализация при обновлении."""
        schema = CategoryUpdateSchema(title="  тест  ")
        assert schema.title == "Тест"


# ── ReserveItemSchema ────────────────────────────────────────────────────────


class TestReserveItemSchema:
    """Тесты для ReserveItemSchema."""

    def test_valid(self):
        """Валидный элемент резерва."""
        item = ReserveItemSchema(product_id=1, quantity=5)
        assert item.product_id == 1
        assert item.quantity == 5

    def test_zero_quantity_raises(self):
        """quantity=0 — ValidationError (gt=0)."""
        with pytest.raises(ValidationError):
            ReserveItemSchema(product_id=1, quantity=0)

    def test_negative_quantity_raises(self):
        """Отрицательное количество — ValidationError."""
        with pytest.raises(ValidationError):
            ReserveItemSchema(product_id=1, quantity=-1)

    def test_zero_product_id_raises(self):
        """product_id=0 — ValidationError (gt=0)."""
        with pytest.raises(ValidationError):
            ReserveItemSchema(product_id=0, quantity=1)


# ── ReserveRequestSchema ─────────────────────────────────────────────────────


class TestReserveRequestSchema:
    """Тесты для ReserveRequestSchema."""

    def test_valid(self):
        """Валидный запрос на резервирование."""
        req = ReserveRequestSchema(
            order_id=uuid.uuid4(),
            items=[ReserveItemSchema(product_id=1, quantity=2)],
        )
        assert len(req.items) == 1

    def test_multiple_items(self):
        """Несколько товаров в одном запросе."""
        req = ReserveRequestSchema(
            order_id=uuid.uuid4(),
            items=[
                ReserveItemSchema(product_id=1, quantity=2),
                ReserveItemSchema(product_id=3, quantity=1),
            ],
        )
        assert len(req.items) == 2

    def test_empty_items_raises(self):
        """Пустой список товаров — ValidationError (min_length=1)."""
        with pytest.raises(ValidationError):
            ReserveRequestSchema(order_id=uuid.uuid4(), items=[])


# ── PaginationParams ─────────────────────────────────────────────────────────


class TestPaginationParams:
    """Тесты для PaginationParams."""

    def test_defaults(self):
        """Значения по умолчанию: page=1, page_size=20."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_custom_values(self):
        """Пользовательские значения пагинации."""
        params = PaginationParams(page=3, page_size=50)
        assert params.page == 3
        assert params.page_size == 50

    def test_page_zero_raises(self):
        """page=0 — ValidationError (ge=1)."""
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_negative_page_raises(self):
        """Отрицательная страница — ValidationError."""
        with pytest.raises(ValidationError):
            PaginationParams(page=-1)

    def test_page_size_exceeds_max_raises(self):
        """page_size больше MAX_PAGE_SIZE (1000) — ValidationError."""
        with pytest.raises(ValidationError):
            PaginationParams(page=1, page_size=9999)
