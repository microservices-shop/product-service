from pydantic import BaseModel, Field


class ReserveItemSchema(BaseModel):
    """Один товар для резервирования."""

    product_id: int = Field(..., gt=0, description="ID товара")
    quantity: int = Field(..., gt=0, description="Количество для резервирования")


class ReserveRequestSchema(BaseModel):
    """Запрос на резервирование товаров."""

    items: list[ReserveItemSchema] = Field(
        ..., min_length=1, description="Список товаров для резервирования"
    )


class ReserveResponseSchema(BaseModel):
    """Ответ на запрос резервирования."""

    success: bool = Field(..., description="Успешность резервирования")
    reserved_items: list[ReserveItemSchema] = Field(
        default_factory=list, description="Список зарезервированных товаров"
    )
    errors: list[str] = Field(
        default_factory=list, description="Список ошибок при резервировании"
    )
