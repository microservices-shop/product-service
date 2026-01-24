from fastapi import APIRouter, Query, status

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


@router.get(
    "",
    response_model=ProductListResponse,
    summary="Получить список товаров",
    description="Возвращает пагинированный список всех активных товаров для каталога.",
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
) -> ProductListResponse:
    """
    Получить список товаров с пагинацией
    """
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.get_all(pagination)


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
    "/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить товар"
)
async def delete_product(
    product_id: int,
    service: ProductServiceDep,
) -> None:
    """Удалить товар из каталога"""
    await service.delete(product_id)
