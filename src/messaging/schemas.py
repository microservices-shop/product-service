from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReserveReleaseMessage(BaseModel):
    """Сообщение об освобождении резерва по заказу."""

    message_id: UUID
    timestamp: datetime
    order_id: UUID
