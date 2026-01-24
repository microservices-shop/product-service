from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AttributeModel
from src.schemas.attributes import AttributeCreateSchema, AttributeUpdateSchema


class AttributeRepository:
    """CRUD операции над атрибутами товаров"""

    @staticmethod
    async def create(
        session: AsyncSession, attribute_data: AttributeCreateSchema
    ) -> AttributeModel:
        """Создать атрибут"""
        fields = attribute_data.model_dump()
        attribute = AttributeModel(**fields)
        session.add(attribute)
        await session.flush()
        return attribute

    @staticmethod
    async def get_by_id(
        session: AsyncSession, attribute_id: int
    ) -> AttributeModel | None:
        """Получить атрибут по его ID"""
        query = select(AttributeModel).where(AttributeModel.id == attribute_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_title(
        session: AsyncSession, attribute_title: str
    ) -> AttributeModel | None:
        query = select(AttributeModel).where(AttributeModel.title == attribute_title)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_title_in_category(
        session: AsyncSession, category_id: int, attribute_title: str
    ) -> AttributeModel | None:
        """Получить атрибут по названию в рамках конкретной категории"""
        query = select(AttributeModel).where(
            AttributeModel.category_id == category_id,
            AttributeModel.title == attribute_title,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_from_category(
        session: AsyncSession, category_id: int
    ) -> list[AttributeModel]:
        """Получить список всех атрибутов конкретной категории"""
        query = select(AttributeModel).where(AttributeModel.category_id == category_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all(session: AsyncSession) -> list[AttributeModel]:
        """Получить список всех атрибутов"""
        query = select(AttributeModel).order_by(AttributeModel.id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        session: AsyncSession,
        attribute: AttributeModel,
        attribute_data: AttributeUpdateSchema,
    ) -> AttributeModel:
        """Обновление атрибута"""
        for field, value in attribute_data.model_dump(exclude_unset=True).items():
            setattr(attribute, field, value)

        await session.flush()
        return attribute

    @staticmethod
    async def delete(session: AsyncSession, attribute: AttributeModel) -> None:
        """Удаление атрибута"""
        await session.delete(attribute)
        await session.flush()
