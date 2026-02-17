from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.api.dependencies import ProductServiceDep
from src.config import settings
from src.schemas.products import (
    ProductCreateSchema,
    ProductUpdateSchema,
    ProductResponseSchema,
    ProductDetailResponseSchema,
    ProductListResponse,
)
from src.schemas.common import PaginationParams

router = APIRouter(prefix="/products", tags=["Products"])


async def _require_admin(
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> str:
    """
    Проверяет роль администратора из заголовка X-User-Role.

    Если заголовок отсутствует — доступ разрешён
    (обратная совместимость до внедрения API Gateway).
    Если указана роль, отличная от admin — 403.
    """
    if x_user_role is not None and x_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Требуется роль администратора.",
        )
    return x_user_role or "anonymous"


@router.get(
    "",
    response_model=ProductListResponse,
    summary="Получить список товаров",
    description="Возвращает пагинированный список товаров с фильтрацией и сортировкой.",
)
async def get_products(
    service: ProductServiceDep,
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(
        default=settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Количество товаров на странице",
    ),
    sort_by: Literal["price", "id", "title", "created_at"] = Query(
        default="id",
        description="Поле для сортировки",
    ),
    sort_order: Literal["asc", "desc"] = Query(
        default="asc",
        description="Порядок сортировки (asc - по возрастанию, desc - по убыванию)",
    ),
    search: str | None = Query(
        default=None,
        max_length=255,
        description="Поиск по названию товара (частичное совпадение, без учёта регистра)",
    ),
    category_id: int | None = Query(
        default=None,
        gt=0,
        description="Фильтрация по ID категории",
    ),
    price_min: int | None = Query(
        default=None,
        ge=0,
        description="Минимальная цена (в копейках)",
    ),
    price_max: int | None = Query(
        default=None,
        ge=0,
        description="Максимальная цена (в копейках)",
    ),
) -> ProductListResponse:
    """
    Получить список товаров с пагинацией, сортировкой и фильтрацией
    """
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.get_all(
        pagination,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        category_id=category_id,
        price_min=price_min,
        price_max=price_max,
    )


@router.get(
    "/{product_id}",
    response_model=ProductDetailResponseSchema,
    summary="Получить детальную информацию о товаре",
    description="Возвращает полную информацию о товаре включая категорию.",
)
async def get_product(
    product_id: int,
    service: ProductServiceDep,
) -> ProductDetailResponseSchema:
    """
    Получить товар по ID

    Возвращает детальную информацию о товаре
    """
    return await service.get_by_id(product_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductResponseSchema,
    summary="Создать товар",
    description="Создаёт новый товар в каталоге.",
    dependencies=[Depends(_require_admin)],
)
async def create_product(
    data: ProductCreateSchema,
    service: ProductServiceDep,
) -> ProductResponseSchema:
    """
    Создать новый товар

    Проверяет существование категории перед созданием
    """
    return await service.create(data)


@router.patch(
    "/{product_id}",
    response_model=ProductResponseSchema,
    summary="Обновить товар",
    description="Частичное обновление информации о товаре.",
    dependencies=[Depends(_require_admin)],
)
async def update_product(
    product_id: int,
    data: ProductUpdateSchema,
    service: ProductServiceDep,
) -> ProductResponseSchema:
    """
    Обновить товар

    Можно передать только те поля, которые нужно изменить
    """
    return await service.update(product_id, data)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить товар",
    dependencies=[Depends(_require_admin)],
)
async def delete_product(
    product_id: int,
    service: ProductServiceDep,
) -> None:
    """Удалить товар из каталога"""
    await service.delete(product_id)
