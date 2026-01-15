from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from src.db.models import CategoryModel
from src.schemas.categories import CategoryCreateSchema, CategoryUpdateSchema


class CategoryRepository:
    """CRUD операции над категориями товаров"""

    async def create(
        self, session: AsyncSession, category_data: CategoryCreateSchema
    ) -> CategoryModel:
        """Создать категорию"""
        fields = category_data.model_dump()
        category = CategoryModel(**fields)
        session.add(category)
        await session.flush()
        return category

    async def get_by_id(
        self, session: AsyncSession, category_id: int
    ) -> CategoryModel | None:
        """Получить категорию по её ID"""
        query = select(CategoryModel).where(CategoryModel.id == category_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_title(
        self, session: AsyncSession, category_title: str
    ) -> CategoryModel | None:
        """Получить категорию по её названию"""
        query = select(CategoryModel).where(CategoryModel.title == category_title)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession) -> list[CategoryModel]:
        """Получить список всех категорий"""
        query = select(CategoryModel).order_by(CategoryModel.id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        session: AsyncSession,
        category: CategoryModel,
        category_data: CategoryUpdateSchema,
    ) -> CategoryModel:
        """Обновление категории"""
        for field, value in category_data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)

        await session.flush()
        return category

    async def delete(self, session: AsyncSession, category: CategoryModel) -> None:
        """Удаление категории"""
        await session.delete(category)
        await session.flush()
