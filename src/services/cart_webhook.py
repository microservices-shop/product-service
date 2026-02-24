import httpx

from src.config import settings
from src.logging import logger

# Таймауты: 3 секунды на подключение, 5 на чтение
_TIMEOUT = httpx.Timeout(timeout=5.0, connect=3.0)


class CartWebhookClient:
    """
    Fire-and-forget клиент для отправки webhook-уведомлений в Cart Service.

    Все ошибки ловятся и логируются — НЕ прокидываются наружу.
    Операции Product Service не должны зависеть от доступности Cart Service.
    """

    def __init__(self) -> None:
        self._base_url = settings.CART_SERVICE_URL.rstrip("/")

    @property
    def _enabled(self) -> bool:
        """Webhook'и отключены если CART_SERVICE_URL не задан."""
        return bool(self._base_url)

    async def notify_product_updated(
        self,
        product_id: int,
        title: str,
        price: int,
        image_url: str | None,
    ) -> None:
        """Уведомить Cart Service об обновлении товара (цена, название, фото)."""
        if not self._enabled:
            return

        url = f"{self._base_url}/internal/cart/products/{product_id}/updated"
        payload = {"title": title, "price": price, "image_url": image_url}

        await self._send(url, payload, event="product_updated", product_id=product_id)

    async def notify_out_of_stock(self, product_id: int) -> None:
        """Уведомить Cart Service что товар закончился (stock → 0)."""
        if not self._enabled:
            return

        url = f"{self._base_url}/internal/cart/products/{product_id}/out-of-stock"
        await self._send(url, payload=None, event="out_of_stock", product_id=product_id)

    async def notify_back_in_stock(self, product_id: int) -> None:
        """Уведомить Cart Service что товар снова в наличии (stock 0 → >0)."""
        if not self._enabled:
            return

        url = f"{self._base_url}/internal/cart/products/{product_id}/back-in-stock"
        await self._send(
            url, payload=None, event="back_in_stock", product_id=product_id
        )

    async def notify_product_deleted(self, product_id: int) -> None:
        """Уведомить Cart Service что товар удалён из каталога."""
        if not self._enabled:
            return

        url = f"{self._base_url}/internal/cart/products/{product_id}/deleted"
        await self._send(
            url, payload=None, event="product_deleted", product_id=product_id
        )

    async def _send(
        self,
        url: str,
        payload: dict | None,
        *,
        event: str,
        product_id: int,
    ) -> None:
        """
        Отправить POST-запрос. Fire-and-forget: все ошибки ловим и логируем.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                if payload is not None:
                    response = await client.post(url, json=payload)
                else:
                    response = await client.post(url)

            response.raise_for_status()

            logger.info(
                f"Webhook отправлен: {event}",
                product_id=product_id,
                status_code=response.status_code,
            )

        except Exception as exc:
            logger.error(
                f"Ошибка отправки webhook: {event}",
                product_id=product_id,
                url=url,
                error=str(exc),
            )
