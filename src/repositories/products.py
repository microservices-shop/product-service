from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import ProductModel
from src.schemas.products import ProductCreateSchema, ProductUpdateSchema


class ProductRepository:
    """CRUD операции над товарами"""

    async def create(
        self, session: AsyncSession, product_data: ProductCreateSchema
    ) -> ProductModel:
        """Создать товар"""
        fields = product_data.model_dump()
        product = ProductModel(**fields)
        session.add(product)
        await session.flush()
        return product

    async def get_by_id(
        self, session: AsyncSession, product_id: int, with_category: bool = True
    ) -> ProductModel | None:
        """Получить товар по ID."""
        query = select(ProductModel).where(ProductModel.id == product_id)

        if with_category:
            query = query.options(selectinload(ProductModel.category))

        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_title(
        self, session: AsyncSession, product_title: str
    ) -> ProductModel | None:
        """Получить товар по названию"""
        query = select(ProductModel).where(ProductModel.title == product_title)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_from_category(
        self, session: AsyncSession, category_id: int
    ) -> list[ProductModel]:
        """Получить список всех товаров одной категории"""
        query = select(ProductModel).where(ProductModel.category_id == category_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_all(
        self, session: AsyncSession, limit: int = 20, offset: int = 0
    ) -> list[ProductModel]:
        """Получить список всех товаров"""
        query = (
            select(ProductModel).order_by(ProductModel.id).limit(limit).offset(offset)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_active(
        self, session: AsyncSession, limit: int = 20, offset: int = 0
    ) -> list[ProductModel]:
        """Получить список всех активных товаров"""
        query = (
            select(ProductModel)
            .where(ProductModel.status == "active")
            .order_by(ProductModel.id)
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    async def count_all(self, session: AsyncSession) -> int:
        """Подсчитать общее количество активных товаров."""
        query = select(func.count(ProductModel.id)).where(
            ProductModel.status == "active"
        )
        result = await session.execute(query)
        return result.scalar_one()

    async def update(
        self,
        session: AsyncSession,
        product: ProductModel,
        product_data: ProductUpdateSchema,
    ) -> ProductModel:
        """Обновление товара"""
        for field, value in product_data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await session.flush()
        return product

    async def delete(self, session: AsyncSession, product: ProductModel) -> None:
        """Удаление товара"""
        await session.delete(product)
        await session.flush()
