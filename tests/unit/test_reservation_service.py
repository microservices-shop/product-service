"""Юнит-тесты для ReservationService."""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.exceptions import BadRequestException
from src.schemas.internal import ReserveRequestSchema, ReserveItemSchema
from src.services.reservations import ReservationService


# ── Фикстуры ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_webhook():
    """Мок CartWebhookClient."""
    return AsyncMock()


@pytest.fixture
def mock_product_repo(mocker):
    """Мок ProductRepository (патчим в модуле services.reservations)."""
    return mocker.patch("src.services.reservations.ProductRepository")


@pytest.fixture
def mock_reservation_repo(mocker):
    """Мок ReservationRepository (патчим в модуле services.reservations)."""
    return mocker.patch("src.services.reservations.ReservationRepository")


@pytest.fixture
def service(mock_session, mock_webhook, mocker):
    """ReservationService с замоканными зависимостями."""
    mocker.patch(
        "src.services.reservations.CartWebhookClient",
        return_value=mock_webhook,
    )
    return ReservationService(mock_session)


def _make_reserve_request(items):
    """Создать ReserveRequestSchema с указанными товарами."""
    return ReserveRequestSchema(
        order_id=uuid.uuid4(),
        items=[ReserveItemSchema(product_id=pid, quantity=qty) for pid, qty in items],
    )


# ── Резервирование ────────────────────────────────────────────────────────────


class TestReserve:
    """Тесты для ReservationService.reserve."""

    async def test_success_single_item(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        make_product,
    ):
        """Успешное резервирование одного товара — stock уменьшается."""
        product = make_product(id=1, stock=10, title="iPhone", price=100)
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.create = AsyncMock()

        data = _make_reserve_request([(1, 3)])
        result = await service.reserve(data)

        assert len(result) == 1
        assert result[0].product_id == 1
        assert result[0].quantity == 3
        assert result[0].price == 100
        assert product.stock == 7  # 10 - 3
        mock_session.commit.assert_called_once()

    async def test_success_multiple_items(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        make_product,
    ):
        """Успешное резервирование нескольких товаров."""
        product1 = make_product(id=1, stock=10, title="iPhone", price=100)
        product2 = make_product(id=2, stock=5, title="Samsung", price=200)

        mock_product_repo.get_by_id = AsyncMock(
            side_effect=[product1, product2],
        )
        mock_reservation_repo.create = AsyncMock()

        data = _make_reserve_request([(1, 2), (2, 3)])
        result = await service.reserve(data)

        assert len(result) == 2
        assert product1.stock == 8
        assert product2.stock == 2
        mock_session.commit.assert_called_once()

    async def test_product_not_found(
        self,
        service,
        mock_product_repo,
    ):
        """BadRequestException если товар не найден."""
        mock_product_repo.get_by_id = AsyncMock(return_value=None)

        data = _make_reserve_request([(999, 1)])
        with pytest.raises(BadRequestException, match="не найден"):
            await service.reserve(data)

    async def test_insufficient_stock(
        self,
        service,
        mock_product_repo,
        make_product,
    ):
        """BadRequestException если недостаточно товара на складе."""
        product = make_product(id=1, stock=2, title="iPhone")
        mock_product_repo.get_by_id = AsyncMock(return_value=product)

        data = _make_reserve_request([(1, 5)])  # запрос 5, в наличии 2
        with pytest.raises(BadRequestException, match="Недостаточно"):
            await service.reserve(data)

    async def test_exact_stock_reserves_to_zero(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        mock_webhook,
        make_product,
    ):
        """Резервирование всего остатка — stock → 0."""
        product = make_product(id=1, stock=5, title="iPhone", price=100)
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.create = AsyncMock()

        data = _make_reserve_request([(1, 5)])
        result = await service.reserve(data)

        assert product.stock == 0
        assert len(result) == 1

    async def test_out_of_stock_webhook(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook notify_out_of_stock вызывается когда stock → 0."""
        product = make_product(id=42, stock=3, title="iPhone", price=100)
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.create = AsyncMock()

        data = _make_reserve_request([(42, 3)])  # забираем всё
        await service.reserve(data)

        assert product.stock == 0
        mock_webhook.notify_out_of_stock.assert_called_once_with(42)

    async def test_no_webhook_when_stock_remains(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook НЕ вызывается если stock > 0 после резервирования."""
        product = make_product(id=1, stock=10, title="iPhone", price=100)
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.create = AsyncMock()

        data = _make_reserve_request([(1, 3)])
        await service.reserve(data)

        assert product.stock == 7
        mock_webhook.notify_out_of_stock.assert_not_called()

    async def test_reservation_repo_create_called(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        make_product,
    ):
        """ReservationRepository.create вызывается с правильными параметрами."""
        product = make_product(id=5, stock=10, title="Test", price=100)
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.create = AsyncMock()

        data = _make_reserve_request([(5, 2)])
        await service.reserve(data)

        mock_reservation_repo.create.assert_called_once()
        call_kwargs = mock_reservation_repo.create.call_args.kwargs
        assert call_kwargs["product_id"] == 5
        assert call_kwargs["quantity"] == 2
        assert call_kwargs["order_id"] == data.order_id


# ── Освобождение резерва ──────────────────────────────────────────────────────


class TestReleaseByOrderId:
    """Тесты для ReservationService.release_by_order_id."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        make_product,
    ):
        """Успешное освобождение резерва — stock возвращается."""
        order_id = uuid.uuid4()

        reservation = MagicMock(product_id=1, quantity=3)
        product = make_product(id=1, stock=7)  # было 10, зарезервировано 3

        mock_reservation_repo.get_by_order_id = AsyncMock(
            return_value=[reservation],
        )
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.delete_by_order_id = AsyncMock()

        await service.release_by_order_id(order_id)

        assert product.stock == 10  # 7 + 3 = 10
        mock_reservation_repo.delete_by_order_id.assert_called_once_with(
            mock_session,
            order_id,
        )
        mock_session.commit.assert_called_once()

    async def test_idempotent_no_reservations(
        self,
        service,
        mock_session,
        mock_reservation_repo,
    ):
        """Повторный release — ничего не происходит (идемпотентность)."""
        order_id = uuid.uuid4()
        mock_reservation_repo.get_by_order_id = AsyncMock(return_value=[])

        await service.release_by_order_id(order_id)

        mock_session.commit.assert_not_called()
        mock_reservation_repo.delete_by_order_id.assert_not_called()

    async def test_back_in_stock_webhook(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook notify_back_in_stock вызывается когда stock 0 → N."""
        order_id = uuid.uuid4()

        reservation = MagicMock(product_id=1, quantity=5)
        product = make_product(id=1, stock=0)  # был 0 — товар закончился

        mock_reservation_repo.get_by_order_id = AsyncMock(
            return_value=[reservation],
        )
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.delete_by_order_id = AsyncMock()

        await service.release_by_order_id(order_id)

        assert product.stock == 5
        mock_webhook.notify_back_in_stock.assert_called_once_with(1)

    async def test_no_webhook_when_stock_was_positive(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        mock_webhook,
        make_product,
    ):
        """Webhook НЕ вызывается если stock был > 0 до release."""
        order_id = uuid.uuid4()

        reservation = MagicMock(product_id=1, quantity=3)
        product = make_product(id=1, stock=5)

        mock_reservation_repo.get_by_order_id = AsyncMock(
            return_value=[reservation],
        )
        mock_product_repo.get_by_id = AsyncMock(return_value=product)
        mock_reservation_repo.delete_by_order_id = AsyncMock()

        await service.release_by_order_id(order_id)

        assert product.stock == 8
        mock_webhook.notify_back_in_stock.assert_not_called()

    async def test_multiple_reservations(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
        make_product,
    ):
        """Освобождение нескольких резервов одного заказа."""
        order_id = uuid.uuid4()

        res1 = MagicMock(product_id=1, quantity=2)
        res2 = MagicMock(product_id=2, quantity=3)
        product1 = make_product(id=1, stock=8)
        product2 = make_product(id=2, stock=7)

        mock_reservation_repo.get_by_order_id = AsyncMock(
            return_value=[res1, res2],
        )
        mock_product_repo.get_by_id = AsyncMock(
            side_effect=[product1, product2],
        )
        mock_reservation_repo.delete_by_order_id = AsyncMock()

        await service.release_by_order_id(order_id)

        assert product1.stock == 10
        assert product2.stock == 10
        mock_session.commit.assert_called_once()

    async def test_product_deleted_graceful(
        self,
        service,
        mock_session,
        mock_product_repo,
        mock_reservation_repo,
    ):
        """Если товар удалён — резерв просто удаляется без ошибки."""
        order_id = uuid.uuid4()

        reservation = MagicMock(product_id=999, quantity=5)
        mock_reservation_repo.get_by_order_id = AsyncMock(
            return_value=[reservation],
        )
        mock_product_repo.get_by_id = AsyncMock(return_value=None)
        mock_reservation_repo.delete_by_order_id = AsyncMock()

        await service.release_by_order_id(order_id)

        mock_reservation_repo.delete_by_order_id.assert_called_once()
        mock_session.commit.assert_called_once()
