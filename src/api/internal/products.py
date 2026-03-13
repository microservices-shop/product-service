from fastapi import APIRouter, status

from src.api.dependencies import ProductServiceDep, ReservationServiceDep
from src.schemas.internal import (
    ReserveRequestSchema,
    ReservedProductSchema,
)
from src.schemas.products import ProductResponseSchema

router = APIRouter(prefix="/products", tags=["Internal — Products"])


@router.get(
    "/{product_id}",
    response_model=ProductResponseSchema,
    summary="[Internal] Получить товар по ID",
)
async def get_product_internal(
    product_id: int,
    service: ProductServiceDep,
) -> ProductResponseSchema:
    """Получить товар по ID (для межсервисного взаимодействия)."""
    return await service.get_by_id(product_id)


@router.post(
    "/reserve",
    response_model=list[ReservedProductSchema],
    summary="[Internal] Резервирование товаров",
)
async def reserve_products(
    data: ReserveRequestSchema,
    service: ReservationServiceDep,
) -> list[ReservedProductSchema]:
    """
    Резервирование товаров (уменьшение stock).

    Используется Order Service при оформлении заказа.
    Если хотя бы один товар не может быть зарезервирован,
    ни один товар не резервируется (атомарная операция).
    """
    return await service.reserve(data)


@router.post(
    "/confirm-reserve",
    status_code=status.HTTP_200_OK,
    summary="[Internal] Подтверждение резерва",
)
async def confirm_reserve(
    data: ReserveRequestSchema,
    service: ProductServiceDep,
) -> dict:
    """
    Подтверждение резерва (no-op в текущей реализации).

    Stock уже был уменьшен при резервировании.
    """
    return await service.confirm_reserve(data)


@router.post(
    "/cancel-reserve",
    status_code=status.HTTP_200_OK,
    summary="[Internal] Отмена резерва",
)
async def cancel_reserve(
    data: ReserveRequestSchema,
    service: ReservationServiceDep,
) -> dict:
    """
    Отмена резерва (восстановление stock).

    Вызывается при ошибке после успешного резервирования.
    """
    await service.release_by_order_id(data.order_id)
    return {"status": "ok"}
