from fastapi import APIRouter, Query, status

from src.api.dependencies import AttributeServiceDep
from src.schemas.attributes import (
    AttributeCreateSchema,
    AttributeUpdateSchema,
    AttributeResponseSchema,
)

router = APIRouter(prefix="/attributes", tags=["Attributes"])


@router.get(
    "",
    response_model=list[AttributeResponseSchema],
    summary="Получить список атрибутов",
    description="Возвращает список всех атрибутов. Опционально можно фильтровать по категории.",
)
async def get_attributes(
    service: AttributeServiceDep,
    category_id: int | None = Query(None, gt=0, description="Фильтр по ID категории"),
) -> list[AttributeResponseSchema]:
    """
    Получить список атрибутов.

    Если указан category_id, возвращает только атрибуты этой категории
    """
    if category_id:
        return await service.get_all_from_category(category_id)
    return await service.get_all()


@router.get(
    "/{attribute_id}",
    response_model=AttributeResponseSchema,
    summary="Получить атрибут по ID",
    description="Возвращает информацию об атрибуте по его идентификатору.",
)
async def get_attribute(
    attribute_id: int,
    service: AttributeServiceDep,
) -> AttributeResponseSchema:
    """
    Получить атрибут по ID.

    Возвращает детальную информацию об определении атрибута
    """
    return await service.get_by_id(attribute_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributeResponseSchema,
    summary="Создать атрибут",
    description="Создаёт новое определение атрибута для категории товаров.",
)
async def create_attribute(
    data: AttributeCreateSchema,
    service: AttributeServiceDep,
) -> AttributeResponseSchema:
    """
    Создать новый атрибут

    Определяет структуру динамического атрибута для товаров конкретной категории
    """
    return await service.create(data)


@router.patch(
    "/{attribute_id}",
    response_model=AttributeResponseSchema,
    summary="Обновить атрибут",
    description="Частичное обновление информации об атрибуте. Можно передать только те поля, которые нужно изменить.",
)
async def update_attribute(
    attribute_id: int,
    data: AttributeUpdateSchema,
    service: AttributeServiceDep,
) -> AttributeResponseSchema:
    """
    Обновить атрибут

    Можно передать только те поля, которые нужно изменить
    """
    return await service.update(attribute_id, data)


@router.delete(
    "/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить атрибут"
)
async def delete_attribute(
    attribute_id: int,
    service: AttributeServiceDep,
) -> None:
    """Удалить определение атрибута"""
    await service.delete(attribute_id)
