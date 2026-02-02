from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.enums import ProductStatus
from src.db.models import ProductModel
from src.schemas.products import ProductCreateSchema, ProductUpdateSchema


class ProductRepository:
    """CRUD операции над товарами"""

    @staticmethod
    async def create(
        session: AsyncSession, product_data: ProductCreateSchema
    ) -> ProductModel:
        """Создать товар"""
        fields = product_data.model_dump()
        product = ProductModel(**fields)
        session.add(product)
        await session.flush()
        return product

    @staticmethod
    async def get_by_id(
        session: AsyncSession, product_id: int, with_category: bool = True
    ) -> ProductModel | None:
        """Получить товар по ID."""
        query = select(ProductModel).where(ProductModel.id == product_id)

        if with_category:
            query = query.options(selectinload(ProductModel.category))

        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_title(
        session: AsyncSession, product_title: str
    ) -> ProductModel | None:
        """Получить товар по названию"""
        query = select(ProductModel).where(ProductModel.title == product_title)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_from_category(
        session: AsyncSession, category_id: int
    ) -> list[ProductModel]:
        """Получить список всех товаров одной категории"""
        query = select(ProductModel).where(ProductModel.category_id == category_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all(
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "id",
        sort_order: str = "asc",
    ) -> list[ProductModel]:
        """Получить список всех товаров с сортировкой"""
        # Определяем колонку для сортировки
        sort_column = getattr(ProductModel, sort_by, ProductModel.id)
        order_func = desc if sort_order == "desc" else asc

        query = (
            select(ProductModel)
            .order_by(order_func(sort_column))
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_active(
        session: AsyncSession, limit: int = 20, offset: int = 0
    ) -> list[ProductModel]:
        """Получить список всех активных товаров"""
        query = (
            select(ProductModel)
            .where(ProductModel.status == ProductStatus.ACTIVE)
            .order_by(ProductModel.id)
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_all(session: AsyncSession) -> int:
        """Подсчитать общее количество всех товаров (независимо от статуса)."""
        query = select(func.count(ProductModel.id))
        result = await session.execute(query)
        return result.scalar_one()

    @staticmethod
    async def count_active(session: AsyncSession) -> int:
        """Подсчитать общее количество активных товаров."""
        query = select(func.count(ProductModel.id)).where(
            ProductModel.status == ProductStatus.ACTIVE
        )
        result = await session.execute(query)
        return result.scalar_one()

    @staticmethod
    async def update(
        session: AsyncSession,
        product: ProductModel,
        product_data: ProductUpdateSchema,
    ) -> ProductModel:
        """Обновление товара"""
        for field, value in product_data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await session.flush()
        return product

    @staticmethod
    async def delete(session: AsyncSession, product: ProductModel) -> None:
        """Удаление товара"""
        await session.delete(product)
        await session.flush()
