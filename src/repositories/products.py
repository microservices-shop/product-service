from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.enums import ProductStatus
from src.db.models import ProductModel
from src.schemas.products import ProductCreateSchema, ProductUpdateSchema


class ProductRepository:
    """CRUD операции над товарами"""

    @staticmethod
    def _build_filters(
        search: str | None = None,
        category_id: int | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
    ) -> list:
        """Построить список условий WHERE для фильтрации товаров."""
        conditions = []

        if search:
            conditions.append(ProductModel.title.ilike(f"%{search}%"))
        if category_id is not None:
            conditions.append(ProductModel.category_id == category_id)
        if price_min is not None:
            conditions.append(ProductModel.price >= price_min)
        if price_max is not None:
            conditions.append(ProductModel.price <= price_max)

        return conditions

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
        search: str | None = None,
        category_id: int | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
    ) -> list[ProductModel]:
        """Получить список товаров с сортировкой и фильтрацией."""
        sort_column = getattr(ProductModel, sort_by, ProductModel.id)
        order_func = desc if sort_order == "desc" else asc

        conditions = ProductRepository._build_filters(
            search=search,
            category_id=category_id,
            price_min=price_min,
            price_max=price_max,
        )

        query = (
            select(ProductModel)
            .where(*conditions)
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
    async def count_filtered(
        session: AsyncSession,
        search: str | None = None,
        category_id: int | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
    ) -> int:
        """Подсчитать количество товаров с учётом фильтров."""
        conditions = ProductRepository._build_filters(
            search=search,
            category_id=category_id,
            price_min=price_min,
            price_max=price_max,
        )

        query = select(func.count(ProductModel.id)).where(*conditions)
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
