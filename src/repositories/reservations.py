from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import ReservationModel


class ReservationRepository:
    """CRUD операции над резервами товаров."""

    @staticmethod
    async def create(
        session: AsyncSession, order_id: UUID, product_id: int, quantity: int
    ) -> ReservationModel:
        """Создать запись о резерве."""
        reservation = ReservationModel(
            order_id=order_id, product_id=product_id, quantity=quantity
        )
        session.add(reservation)
        await session.flush()
        return reservation

    @staticmethod
    async def get_by_order_id(
        session: AsyncSession, order_id: UUID
    ) -> list[ReservationModel]:
        """Получить все резервы по ID заказа."""
        query = select(ReservationModel).where(ReservationModel.order_id == order_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_by_order_id(session: AsyncSession, order_id: UUID) -> None:
        """Удалить все резервы по ID заказа."""
        query = select(ReservationModel).where(ReservationModel.order_id == order_id)
        result = await session.execute(query)
        reservations = result.scalars().all()
        for reservation in reservations:
            await session.delete(reservation)
        await session.flush()
