from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import session_factory
from src.services.categories import CategoryService
from src.services.products import ProductService
from src.services.attributes import AttributeService


async def get_db() -> AsyncSession:
    """Открывает сессию, отдаёт её и закрывает после запроса"""
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_category_service(session: SessionDep) -> CategoryService:
    """Фабрика для создания сервиса категорий"""
    return CategoryService(session)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


async def get_product_service(session: SessionDep) -> ProductService:
    """Фабрика для создания сервиса продуктов"""
    return ProductService(session)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


async def get_attribute_service(session: SessionDep) -> AttributeService:
    """Фабрика для создания сервиса атрибутов"""
    return AttributeService(session)


AttributeServiceDep = Annotated[AttributeService, Depends(get_attribute_service)]
