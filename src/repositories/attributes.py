from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AttributeModel
from src.schemas.attributes import AttributeCreateSchema, AttributeUpdateSchema


class AttributesRepository:
    """CRUD операции над атрибутами товаров"""

    async def create(
        self, session: AsyncSession, attribute_data: AttributeCreateSchema
    ) -> AttributeModel:
        """Создать атрибут"""
        fields = attribute_data.model_dump()
        attribute = AttributeModel(**fields)
        session.add(attribute)
        await session.flush()
        return attribute

    async def get_by_id(
        self, session: AsyncSession, attribute_id: int
    ) -> AttributeModel | None:
        """Получить атрибут по его ID"""
        query = select(AttributeModel).where(AttributeModel.id == attribute_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_from_category(
        self, session: AsyncSession, category_id: int
    ) -> list[AttributeModel]:
        """Получить список всех атрибутов конкретной категории"""
        query = select(AttributeModel).where(AttributeModel.category_id == category_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_all(self, session: AsyncSession) -> list[AttributeModel]:
        """Получить список всех атрибутов"""
        query = select(AttributeModel).order_by(AttributeModel.id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        session: AsyncSession,
        attribute: AttributeModel,
        attribute_data: AttributeUpdateSchema,
    ) -> AttributeModel:
        """Обновление атрибута"""
        for field, value in attribute_data.model_dump(exclude_unset=True).items():
            setattr(attribute, field, value)

        await session.flush()
        return attribute

    async def delete(self, session: AsyncSession, attribute: AttributeModel) -> None:
        """Удаление атрибута"""
        await session.delete(attribute)
        await session.flush()
