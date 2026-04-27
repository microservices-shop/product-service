"""Юнит-тесты для CartWebhookClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.cart_webhook import CartWebhookClient


# ── Фикстуры ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_httpx(mocker):
    """Мок httpx.AsyncClient как async context manager."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    # Создаём async context manager
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)

    mocker.patch("src.services.cart_webhook.httpx.AsyncClient", return_value=cm)
    return mock_client


@pytest.fixture
def webhook_client():
    """CartWebhookClient с активным base URL (минуя __init__ и settings)."""
    client = CartWebhookClient.__new__(CartWebhookClient)
    client._base_url = "http://cart-service:8001"
    return client


@pytest.fixture
def disabled_client():
    """CartWebhookClient с пустым base URL (webhook'и выключены)."""
    client = CartWebhookClient.__new__(CartWebhookClient)
    client._base_url = ""
    return client


# ── Отправка уведомлений ──────────────────────────────────────────────────────


class TestNotifyProductUpdated:
    """Тесты для CartWebhookClient.notify_product_updated."""

    async def test_sends_correct_request(self, webhook_client, mock_httpx):
        """POST с правильным URL и payload."""
        await webhook_client.notify_product_updated(
            product_id=42,
            title="iPhone 15",
            price=99990,
            image_url="https://img.jpg",
        )

        mock_httpx.post.assert_called_once_with(
            "http://cart-service:8001/internal/cart/products/42/updated",
            json={
                "title": "iPhone 15",
                "price": 99990,
                "image_url": "https://img.jpg",
            },
        )

    async def test_sends_null_image(self, webhook_client, mock_httpx):
        """image_url=None корректно передаётся в payload."""
        await webhook_client.notify_product_updated(
            product_id=1,
            title="Test",
            price=100,
            image_url=None,
        )

        call_kwargs = mock_httpx.post.call_args
        assert call_kwargs.kwargs["json"]["image_url"] is None


class TestNotifyOutOfStock:
    """Тесты для CartWebhookClient.notify_out_of_stock."""

    async def test_sends_correct_request(self, webhook_client, mock_httpx):
        """POST без payload на правильный URL."""
        await webhook_client.notify_out_of_stock(product_id=42)

        mock_httpx.post.assert_called_once_with(
            "http://cart-service:8001/internal/cart/products/42/out-of-stock",
        )


class TestNotifyBackInStock:
    """Тесты для CartWebhookClient.notify_back_in_stock."""

    async def test_sends_correct_request(self, webhook_client, mock_httpx):
        """POST без payload на правильный URL."""
        await webhook_client.notify_back_in_stock(product_id=42)

        mock_httpx.post.assert_called_once_with(
            "http://cart-service:8001/internal/cart/products/42/back-in-stock",
        )


class TestNotifyProductDeleted:
    """Тесты для CartWebhookClient.notify_product_deleted."""

    async def test_sends_correct_request(self, webhook_client, mock_httpx):
        """POST без payload на правильный URL."""
        await webhook_client.notify_product_deleted(product_id=42)

        mock_httpx.post.assert_called_once_with(
            "http://cart-service:8001/internal/cart/products/42/deleted",
        )


# ── Webhook'и выключены ───────────────────────────────────────────────────────


class TestWebhookDisabled:
    """Тесты: webhook'и не отправляются при пустом CART_SERVICE_URL."""

    async def test_notify_product_updated_noop(self, disabled_client, mock_httpx):
        """notify_product_updated ничего не делает."""
        await disabled_client.notify_product_updated(
            product_id=1,
            title="T",
            price=1,
            image_url=None,
        )
        mock_httpx.post.assert_not_called()

    async def test_notify_out_of_stock_noop(self, disabled_client, mock_httpx):
        """notify_out_of_stock ничего не делает."""
        await disabled_client.notify_out_of_stock(product_id=1)
        mock_httpx.post.assert_not_called()

    async def test_notify_back_in_stock_noop(self, disabled_client, mock_httpx):
        """notify_back_in_stock ничего не делает."""
        await disabled_client.notify_back_in_stock(product_id=1)
        mock_httpx.post.assert_not_called()

    async def test_notify_product_deleted_noop(self, disabled_client, mock_httpx):
        """notify_product_deleted ничего не делает."""
        await disabled_client.notify_product_deleted(product_id=1)
        mock_httpx.post.assert_not_called()


# ── Обработка ошибок ──────────────────────────────────────────────────────────


class TestWebhookErrorHandling:
    """Тесты: ошибки HTTP не прокидываются наружу."""

    async def test_connection_error_does_not_raise(
        self,
        webhook_client,
        mock_httpx,
        mocker,
    ):
        """Ошибка подключения — логируется, не прокидывается."""
        mock_httpx.post = AsyncMock(side_effect=ConnectionError("refused"))
        mock_logger = mocker.patch("src.services.cart_webhook.logger")

        # Не должно вызвать исключение
        await webhook_client.notify_product_updated(
            product_id=1,
            title="T",
            price=1,
            image_url=None,
        )

        mock_logger.error.assert_called_once()

    async def test_timeout_error_does_not_raise(
        self,
        webhook_client,
        mock_httpx,
        mocker,
    ):
        """Таймаут — логируется, не прокидывается."""
        mock_httpx.post = AsyncMock(side_effect=TimeoutError("timeout"))
        mock_logger = mocker.patch("src.services.cart_webhook.logger")

        await webhook_client.notify_out_of_stock(product_id=1)

        mock_logger.error.assert_called_once()

    async def test_http_error_does_not_raise(
        self,
        webhook_client,
        mock_httpx,
        mocker,
    ):
        """HTTP 500 — raise_for_status вызывает ошибку, она ловится."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=Exception("500 Internal Server Error"),
        )
        mock_httpx.post = AsyncMock(return_value=mock_response)
        mock_logger = mocker.patch("src.services.cart_webhook.logger")

        await webhook_client.notify_product_deleted(product_id=1)

        mock_logger.error.assert_called_once()

    async def test_generic_exception_does_not_raise(
        self,
        webhook_client,
        mock_httpx,
        mocker,
    ):
        """Любое исключение — логируется, не прокидывается."""
        mock_httpx.post = AsyncMock(side_effect=RuntimeError("unexpected"))
        mock_logger = mocker.patch("src.services.cart_webhook.logger")

        await webhook_client.notify_back_in_stock(product_id=1)

        mock_logger.error.assert_called_once()
