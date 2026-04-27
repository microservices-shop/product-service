"""Юнит-тесты для ProductService."""

import pytest
from unittest.mock import AsyncMock

from sqlalchemy.exc import IntegrityError

from src.db.enums import AttributeType
from src.exceptions import (
    NotFoundException,
    BadRequestException,
    ValidationException,
)
from src.schemas.products import ProductCreateSchema, ProductUpdateSchema
from src.schemas.common import PaginationParams
from src.services.products import ProductService


# ── Фикстуры ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_webhook():
    """Мок CartWebhookClient."""
    return AsyncMock()


@pytest.fixture
def mock_product_repo(mocker):
    """Мок ProductRepository (патчим в модуле services.products)."""
    return mocker.patch("src.services.products.ProductRepository")


@pytest.fixture
def mock_category_repo(mocker):
    """Мок CategoryRepository (патчим в модуле services.products)."""
    return mocker.patch("src.services.products.CategoryRepository")


@pytest.fixture
def mock_attribute_repo(mocker):
    """Мок AttributeRepository (патчим в модуле services.products)."""
    return mocker.patch("src.services.products.AttributeRepository")


@pytest.fixture
def service(mock_session, mock_webhook, mocker):
    """ProductService с замоканными зависимостями."""
    mocker.patch(
        "src.services.products.CartWebhookClient",
        return_value=mock_webhook,
    )
    return ProductService(mock_session)


# ── Создание товара ───────────────────────────────────────────────────────────


class TestCreateProduct:
    """Тесты для ProductService.create."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_category_repo,
        make_product,
        make_category,
    ):
        """Успешное создание товара при существующей категории."""
        category = make_category()
        product = make_product()

        mock_category_repo.get_by_id = AsyncMock(return_value=category)
        mock_product_repo.create = AsyncMock(return_value=product)

        data = ProductCreateSchema(title="iPhone 15", price=99990, category_id=1)
        result = await service.create(data)

        assert result == product
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_category_not_found(
        self,
        service,
        mock_session,
        mock_category_repo,
    ):
        """NotFoundException если категория не существует."""
        mock_category_repo.get_by_id = AsyncMock(return_value=None)

        data = ProductCreateSchema(title="Test", price=100, category_id=999)
        with pytest.raises(NotFoundException):
            await service.create(data)

        mock_session.commit.assert_not_called()

    async def test_integrity_error_fk_constraint(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_category_repo,
        make_category,
    ):
        """IntegrityError по FK products_category_id_fkey → NotFoundException."""
        mock_category_repo.get_by_id = AsyncMock(return_value=make_category())
        mock_product_repo.create = AsyncMock(
            side_effect=IntegrityError(
                "INSERT",
                {},
                Exception("products_category_id_fkey"),
            ),
        )

        data = ProductCreateSchema(title="Test", price=100, category_id=1)
        with pytest.raises(NotFoundException):
            await service.create(data)

        mock_session.rollback.assert_called_once()

    async def test_integrity_error_generic(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_category_repo,
        make_category,
    ):
        """IntegrityError без FK → BadRequestException."""
        mock_category_repo.get_by_id = AsyncMock(return_value=make_category())
        mock_product_repo.create = AsyncMock(
            side_effect=IntegrityError(
                "INSERT",
                {},
                Exception("some_other_constraint"),
            ),
        )

        data = ProductCreateSchema(title="Test", price=100, category_id=1)
        with pytest.raises(BadRequestException):
            await service.create(data)

    async def test_with_valid_attributes(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_category_repo,
        mock_attribute_repo,
        make_product,
        make_category,
        make_attribute,
    ):
        """Создание товара с валидными атрибутами проходит успешно."""
        category = make_category()
        product = make_product(attributes={"Цвет": "Красный"})
        attr_def = make_attribute(
            title="Цвет",
            type=AttributeType.STRING,
            required=False,
        )

        mock_category_repo.get_by_id = AsyncMock(return_value=category)
        mock_product_repo.create = AsyncMock(return_value=product)
        mock_attribute_repo.get_all_from_category = AsyncMock(
            return_value=[attr_def],
        )

        data = ProductCreateSchema(
            title="Test",
            price=100,
            category_id=1,
            attributes={"Цвет": "Красный"},
        )
        result = await service.create(data)
        assert result == product


# ── Получение товара ──────────────────────────────────────────────────────────


class TestGetProduct:
    """Тесты для ProductService.get_by_id и get_by_title."""

    async def test_get_by_id_success(self, service, mock_product_repo, make_product):
        """Успешное получение товара по ID."""
        product = make_product()
        mock_product_repo.get_by_id = AsyncMock(return_value=product)

        result = await service.get_by_id(1)
        assert result == product

    async def test_get_by_id_not_found(self, service, mock_product_repo):
        """NotFoundException если товар не найден по ID."""
        mock_product_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_by_id(999)

    async def test_get_by_title_success(
        self,
        service,
        mock_product_repo,
        make_product,
    ):
        """Успешное получение товара по названию."""
        product = make_product(title="iPhone 15")
        mock_product_repo.get_by_title = AsyncMock(return_value=product)

        result = await service.get_by_title("iPhone 15")
        assert result.title == "iPhone 15"

    async def test_get_by_title_not_found(self, service, mock_product_repo):
        """NotFoundException если товар не найден по названию."""
        mock_product_repo.get_by_title = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_by_title("Несуществующий")


# ── Список товаров с пагинацией ───────────────────────────────────────────────


class TestGetAllProducts:
    """Тесты для ProductService.get_all (пагинация, фильтрация)."""

    async def test_pagination_calculation(
        self,
        service,
        mock_product_repo,
        make_product,
    ):
        """Корректный расчёт offset и total_pages."""
        products = [make_product(id=i) for i in range(1, 4)]
        mock_product_repo.count_filtered = AsyncMock(return_value=25)
        mock_product_repo.get_all = AsyncMock(return_value=products)

        pagination = PaginationParams(page=2, page_size=10)
        result = await service.get_all(pagination)

        assert result.total == 25
        assert result.page == 2
        assert result.page_size == 10
        assert result.total_pages == 3

        call_kwargs = mock_product_repo.get_all.call_args
        assert call_kwargs.kwargs["offset"] == 10
        assert call_kwargs.kwargs["limit"] == 10

    async def test_first_page(self, service, mock_product_repo, make_product):
        """Первая страница — offset=0."""
        mock_product_repo.count_filtered = AsyncMock(return_value=5)
        mock_product_repo.get_all = AsyncMock(
            return_value=[make_product(id=i) for i in range(1, 6)],
        )

        pagination = PaginationParams(page=1, page_size=20)
        result = await service.get_all(pagination)

        assert result.total_pages == 1
        call_kwargs = mock_product_repo.get_all.call_args
        assert call_kwargs.kwargs["offset"] == 0

    async def test_empty_result(self, service, mock_product_repo):
        """Пустой результат — total_pages=1 (не 0)."""
        mock_product_repo.count_filtered = AsyncMock(return_value=0)
        mock_product_repo.get_all = AsyncMock(return_value=[])

        pagination = PaginationParams(page=1, page_size=20)
        result = await service.get_all(pagination)

        assert result.total == 0
        assert result.total_pages == 1
        assert result.items == []


# ── Обновление товара ─────────────────────────────────────────────────────────


class TestUpdateProduct:
    """Тесты для ProductService.update."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_product_repo,
        make_product,
    ):
        """Успешное обновление товара."""
        product = make_product(title="iPhone", price=100, stock=5)
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_product_repo.update = AsyncMock(return_value=product)

        data = ProductUpdateSchema(description="Новое описание")
        result = await service.update(1, data)

        assert result == product
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_not_found(self, service, mock_product_repo):
        """NotFoundException при обновлении несуществующего товара."""
        mock_product_repo.get_by_id = AsyncMock(return_value=None)

        data = ProductUpdateSchema(title="New")
        with pytest.raises(NotFoundException):
            await service.update(999, data)

    async def test_price_change_triggers_webhook(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook notify_product_updated вызывается при изменении цены."""
        old_product = make_product(title="Test", price=100, stock=5)
        updated_product = make_product(title="Test", price=200, stock=5)

        mock_product_repo.get_by_id = AsyncMock(return_value=old_product)
        mock_product_repo.update = AsyncMock(return_value=updated_product)

        data = ProductUpdateSchema(price=200)
        await service.update(1, data)

        mock_webhook.notify_product_updated.assert_called_once()

    async def test_title_change_triggers_webhook(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook notify_product_updated вызывается при изменении названия."""
        old_product = make_product(title="Old Name", price=100, stock=5)
        updated_product = make_product(title="New Name", price=100, stock=5)

        mock_product_repo.get_by_id = AsyncMock(return_value=old_product)
        mock_product_repo.update = AsyncMock(return_value=updated_product)

        data = ProductUpdateSchema(title="New Name")
        await service.update(1, data)

        mock_webhook.notify_product_updated.assert_called_once()

    async def test_stock_to_zero_triggers_out_of_stock(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook notify_out_of_stock вызывается при stock → 0."""
        old_product = make_product(stock=5)
        updated_product = make_product(stock=0)

        mock_product_repo.get_by_id = AsyncMock(return_value=old_product)
        mock_product_repo.update = AsyncMock(return_value=updated_product)

        data = ProductUpdateSchema(stock=0)
        await service.update(1, data)

        mock_webhook.notify_out_of_stock.assert_called_once_with(1)

    async def test_stock_from_zero_triggers_back_in_stock(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook notify_back_in_stock вызывается при stock 0 → N."""
        old_product = make_product(stock=0)
        updated_product = make_product(stock=10)

        mock_product_repo.get_by_id = AsyncMock(return_value=old_product)
        mock_product_repo.update = AsyncMock(return_value=updated_product)

        data = ProductUpdateSchema(stock=10)
        await service.update(1, data)

        mock_webhook.notify_back_in_stock.assert_called_once_with(1)

    async def test_no_webhook_when_nothing_changed(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook НЕ вызывается если title/price/images не изменились."""
        product = make_product(title="Same", price=100, stock=5)

        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_product_repo.update = AsyncMock(return_value=product)

        data = ProductUpdateSchema(description="Updated desc")
        await service.update(1, data)

        mock_webhook.notify_product_updated.assert_not_called()
        mock_webhook.notify_out_of_stock.assert_not_called()
        mock_webhook.notify_back_in_stock.assert_not_called()

    async def test_change_to_nonexistent_category(
        self,
        service,
        mock_product_repo,
        mock_category_repo,
        make_product,
    ):
        """NotFoundException при смене на несуществующую категорию."""
        product = make_product(category_id=1)
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_category_repo.get_by_id = AsyncMock(return_value=None)

        data = ProductUpdateSchema(category_id=999)
        with pytest.raises(NotFoundException):
            await service.update(1, data)


# ── Удаление товара ───────────────────────────────────────────────────────────


class TestDeleteProduct:
    """Тесты для ProductService.delete."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_webhook,
        make_product,
    ):
        """Успешное удаление товара + webhook."""
        product = make_product()
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_product_repo.delete = AsyncMock()

        await service.delete(1)

        mock_session.commit.assert_called_once()
        mock_webhook.notify_product_deleted.assert_called_once_with(1)

    async def test_not_found(self, service, mock_product_repo):
        """NotFoundException при удалении несуществующего товара."""
        mock_product_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.delete(999)


# ── Валидация атрибутов ───────────────────────────────────────────────────────


class TestValidateAttributes:
    """Тесты для ProductService._validate_product_attributes и _validate_attribute_type."""

    async def test_required_attribute_missing(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """ValidationException если обязательный атрибут не указан."""
        attr_def = make_attribute(
            title="Цвет",
            type=AttributeType.STRING,
            required=True,
        )
        mock_attribute_repo.get_all_from_category = AsyncMock(
            return_value=[attr_def],
        )

        with pytest.raises(ValidationException):
            await service._validate_product_attributes(
                category_id=1,
                attributes={},
            )

    async def test_wrong_type_string(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """ValidationException если передали число вместо строки."""
        attr_def = make_attribute(
            title="Цвет",
            type=AttributeType.STRING,
            required=False,
        )
        mock_attribute_repo.get_all_from_category = AsyncMock(
            return_value=[attr_def],
        )

        with pytest.raises(ValidationException):
            await service._validate_product_attributes(
                category_id=1,
                attributes={"Цвет": 123},
            )

    async def test_wrong_type_number(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """ValidationException если передали строку вместо числа."""
        attr_def = make_attribute(
            title="Вес",
            type=AttributeType.NUMBER,
            required=False,
        )
        mock_attribute_repo.get_all_from_category = AsyncMock(
            return_value=[attr_def],
        )

        with pytest.raises(ValidationException):
            await service._validate_product_attributes(
                category_id=1,
                attributes={"Вес": "сто"},
            )

    async def test_wrong_type_boolean(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """ValidationException если передали строку вместо bool."""
        attr_def = make_attribute(
            title="NFC",
            type=AttributeType.BOOLEAN,
            required=False,
        )
        mock_attribute_repo.get_all_from_category = AsyncMock(
            return_value=[attr_def],
        )

        with pytest.raises(ValidationException):
            await service._validate_product_attributes(
                category_id=1,
                attributes={"NFC": "yes"},
            )

    async def test_valid_attributes_pass(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """Валидные атрибуты проходят без ошибки."""
        attr_def = make_attribute(
            title="Цвет",
            type=AttributeType.STRING,
            required=True,
        )
        mock_attribute_repo.get_all_from_category = AsyncMock(
            return_value=[attr_def],
        )

        await service._validate_product_attributes(
            category_id=1,
            attributes={"Цвет": "Красный"},
        )

    def test_validate_attribute_type_correct_string(self, service):
        """STRING: строка проходит валидацию → None."""
        result = service._validate_attribute_type("color", "Red", AttributeType.STRING)
        assert result is None

    def test_validate_attribute_type_correct_number(self, service):
        """NUMBER: число проходит валидацию → None."""
        result = service._validate_attribute_type("weight", 100, AttributeType.NUMBER)
        assert result is None

    def test_validate_attribute_type_correct_float(self, service):
        """NUMBER: float проходит валидацию → None."""
        result = service._validate_attribute_type("weight", 3.14, AttributeType.NUMBER)
        assert result is None

    def test_validate_attribute_type_correct_boolean(self, service):
        """BOOLEAN: bool проходит валидацию → None."""
        result = service._validate_attribute_type("active", True, AttributeType.BOOLEAN)
        assert result is None

    def test_validate_attribute_type_correct_array(self, service):
        """ARRAY: список проходит валидацию → None."""
        result = service._validate_attribute_type(
            "tags", ["a", "b"], AttributeType.ARRAY
        )
        assert result is None

    def test_validate_attribute_type_incorrect_returns_error(self, service):
        """Некорректный тип возвращает словарь с ошибкой."""
        result = service._validate_attribute_type("color", 123, AttributeType.STRING)
        assert result is not None
        assert result["field"] == "color"
        assert "message" in result
