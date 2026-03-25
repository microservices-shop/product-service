from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.exceptions import BadRequestException
from src.repositories.products import ProductRepository
from src.repositories.reservations import ReservationRepository
from src.schemas.internal import (
    ReserveRequestSchema,
    ReservedProductSchema,
)
from src.services.cart_webhook import CartWebhookClient


class ReservationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cart_webhook = CartWebhookClient()

    async def reserve(self, data: ReserveRequestSchema) -> list[ReservedProductSchema]:
        """
        Резервирование товаров: уменьшение stock и создание записей.
        """
        products_to_reserve = []

        for item in data.items:
            product = await ProductRepository.get_by_id(
                self.session, item.product_id, with_category=False
            )
            if not product:
                raise BadRequestException(f"Товар с ID {item.product_id} не найден")

            if product.stock < item.quantity:
                raise BadRequestException(
                    f"Недостаточно товара '{product.title}' "
                    f"(запрошено: {item.quantity}, в наличии: {product.stock})"
                )
            products_to_reserve.append((product, item.quantity))

        reserved_items = []
        for product, quantity in products_to_reserve:
            product.stock -= quantity
            await ReservationRepository.create(
                self.session,
                order_id=data.order_id,
                product_id=product.id,
                quantity=quantity,
            )
            reserved_items.append(
                ReservedProductSchema(
                    product_id=product.id,
                    name=product.title,
                    price=product.price,
                    quantity=quantity,
                    image_url=product.images[0] if product.images else "",
                )
            )

        await self.session.commit()

        # Webhook: уведомить Cart Service о товарах, которые закончились
        for product, _ in products_to_reserve:
            if product.stock == 0:
                await self._cart_webhook.notify_out_of_stock(product.id)

        return reserved_items

    async def release_by_order_id(self, order_id: UUID) -> None:
        """
        Найти резервы по order_id, вернуть stock += quantity, удалить записи.
        """
        reservations = await ReservationRepository.get_by_order_id(
            self.session, order_id
        )
        if not reservations:
            # Идемпотентность
            return

        was_out_of_stock = []

        for reservation in reservations:
            product = await ProductRepository.get_by_id(
                self.session, reservation.product_id, with_category=False
            )
            if product:
                if product.stock == 0:
                    was_out_of_stock.append(product.id)
                product.stock += reservation.quantity

        await ReservationRepository.delete_by_order_id(self.session, order_id)
        await self.session.commit()

        for product_id in was_out_of_stock:
            await self._cart_webhook.notify_back_in_stock(product_id)
