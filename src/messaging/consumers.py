from faststream.rabbit import RabbitRouter

from src.db.database import session_factory
from src.logging import logger
from src.messaging.schemas import ReserveReleaseMessage
from src.services.reservations import ReservationService

router = RabbitRouter()


@router.subscriber("product.reserve.release")
async def handle_reserve_release(msg: ReserveReleaseMessage) -> None:
    """
    Освобождение резерва по заказу.
    """
    logger.info(
        f"[MQ] reserve.release: order_id={msg.order_id}, message_id={msg.message_id}"
    )
    async with session_factory() as session:
        service = ReservationService(session)
        await service.release_by_order_id(msg.order_id)
    logger.info(f"[MQ] reserve.release: order_id={msg.order_id} — выполнено")
