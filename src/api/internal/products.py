from fastapi import APIRouter, status

from src.api.dependencies import ProductServiceDep, SessionDep
from src.schemas.internal import (
    ReserveRequestSchema,
    ReserveResponseSchema,
    ReserveItemSchema,
)
from src.schemas.products import ProductResponseSchema
from src.repositories.products import ProductRepository

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
    response_model=ReserveResponseSchema,
    summary="[Internal] Резервирование товаров",
)
async def reserve_products(
    data: ReserveRequestSchema,
    session: SessionDep,
) -> ReserveResponseSchema:
    """
    Резервирование товаров (уменьшение stock).

    Используется Order Service при оформлении заказа.
    Если хотя бы один товар не может быть зарезервирован,
    ни один товар не резервируется (атомарная операция).
    """
    errors = []
    products_to_reserve = []

    for item in data.items:
        product = await ProductRepository.get_by_id(
            session, item.product_id, with_category=False
        )
        if not product:
            errors.append(f"Товар с ID {item.product_id} не найден")
            continue
        if product.stock < item.quantity:
            errors.append(
                f"Недостаточно товара '{product.title}' "
                f"(запрошено: {item.quantity}, в наличии: {product.stock})"
            )
            continue
        products_to_reserve.append((product, item.quantity))

    if errors:
        return ReserveResponseSchema(success=False, errors=errors)

    reserved = []
    for product, quantity in products_to_reserve:
        product.stock -= quantity
        reserved.append(ReserveItemSchema(product_id=product.id, quantity=quantity))

    await session.commit()
    return ReserveResponseSchema(success=True, reserved_items=reserved)


@router.post(
    "/confirm-reserve",
    status_code=status.HTTP_200_OK,
    summary="[Internal] Подтверждение резерва",
)
async def confirm_reserve(
    data: ReserveRequestSchema,
) -> dict:
    """
    Подтверждение резерва (no-op в текущей реализации).

    Stock уже был уменьшен при резервировании.
    """
    return {"status": "confirmed", "items_count": len(data.items)}


@router.post(
    "/cancel-reserve",
    response_model=ReserveResponseSchema,
    summary="[Internal] Отмена резерва",
)
async def cancel_reserve(
    data: ReserveRequestSchema,
    session: SessionDep,
) -> ReserveResponseSchema:
    """
    Отмена резерва (восстановление stock).

    Вызывается при ошибке после успешного резервирования.
    """
    restored = []
    errors = []

    for item in data.items:
        product = await ProductRepository.get_by_id(
            session, item.product_id, with_category=False
        )
        if not product:
            errors.append(f"Товар с ID {item.product_id} не найден")
            continue

        product.stock += item.quantity
        restored.append(
            ReserveItemSchema(product_id=product.id, quantity=item.quantity)
        )

    await session.commit()
    return ReserveResponseSchema(
        success=len(errors) == 0,
        reserved_items=restored,
        errors=errors,
    )
