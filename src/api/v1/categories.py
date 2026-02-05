from fastapi import APIRouter, status

from src.api.dependencies import CategoryServiceDep
from src.schemas.attributes import AttributeResponseSchema
from src.schemas.categories import (
    CategoryCreateSchema,
    CategoryUpdateSchema,
    CategoryResponseSchema,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryResponseSchema,
    summary="Создать категорию",
    description="Создаёт новую категорию товаров.",
)
async def create_category(
    data: CategoryCreateSchema,
    service: CategoryServiceDep,
) -> CategoryResponseSchema:
    """
    Создать новую категорию

    Бизнес-правила:
    - Название должно быть уникальным
    """
    return await service.create(data)


@router.get(
    "/{category_id}",
    response_model=CategoryResponseSchema,
    summary="Получить категорию по ID",
    description="Возвращает информацию о категории по её идентификатору.",
)
async def get_category(
    category_id: int,
    service: CategoryServiceDep,
) -> CategoryResponseSchema:
    """Получить категорию по ID"""
    return await service.get_by_id(category_id)


@router.get(
    "",
    response_model=list[CategoryResponseSchema],
    summary="Получить список всех категорий",
    description="Возвращает список всех доступных категорий товаров.",
)
async def get_all_categories(
    service: CategoryServiceDep,
) -> list[CategoryResponseSchema]:
    """Получить список всех категорий"""
    return await service.get_all()


@router.get(
    "/{category_id}/attributes",
    response_model=list[AttributeResponseSchema],
    summary="Получить атрибуты категории",
    description="Возвращает список определений атрибутов для указанной категории.",
)
async def get_category_attributes(
    category_id: int,
    service: CategoryServiceDep,
):
    """Получить список атрибутов для категории"""
    return await service.get_attributes(category_id)


@router.patch(
    "/{category_id}",
    response_model=CategoryResponseSchema,
    summary="Обновить категорию",
    description="Частичное обновление информации о категории. Можно передать только те поля, которые нужно изменить.",
)
async def update_category(
    category_id: int,
    data: CategoryUpdateSchema,
    service: CategoryServiceDep,
) -> CategoryResponseSchema:
    """
    Обновить категорию

    Частичное обновление (PATCH) - можно передать только те поля, которые нужно изменить
    """
    return await service.update(category_id, data)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить категорию",
)
async def delete_category(
    category_id: int,
    service: CategoryServiceDep,
) -> None:
    """Удалить категорию"""
    await service.delete(category_id)
