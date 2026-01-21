import math

from fastapi import status, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ProductModel
from src.repositories.categories import CategoryRepository
from src.repositories.products import ProductRepository
from src.schemas.common import PaginationParams
from sqlalchemy.exc import IntegrityError


from src.schemas.products import (
    ProductCreateSchema,
    ProductUpdateSchema,
    ProductListResponse,
)


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductRepository()
        self.category_repo = CategoryRepository()

    def _normalize_title(self, title: str) -> str:
        return title.strip().capitalize()

    async def create(self, data: ProductCreateSchema) -> ProductModel:
        """Создать новый товар."""
        category = await self.category_repo.get_by_id(self.session, data.category_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Категория с ID {data.category_id} не найдена",
            )

        try:
            product = await self.repo.create(self.session, data)
            await self.session.commit()

            await self.session.refresh(product, ["category"])

            return product
        except IntegrityError as e:
            await self.session.rollback()

            if "products_category_id_fkey" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Категория с ID {data.category_id} не найдена",
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка целостности данных",
            )

    async def get_by_id(self, product_id: int) -> ProductModel:
        """
        Получить товар по ID

        :raises HTTPException 404: Если атрибут не найден
        """

        product = await self.repo.get_by_id(self.session, product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Товар с ID '{product_id}' не найден",
            )

        return product

    async def get_by_title(self, product: str) -> ProductModel:
        """
        Получить товар по названию

        :raises HTTPException 404: Если товар не найден
        """

        normalized_title = self._normalize_title(product)
        product = await self.repo.get_by_title(self.session, normalized_title)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Товар с названием '{normalized_title}' не найден",
            )

        return product

    async def get_all_from_category(self, category_id: int) -> list[ProductModel]:
        """Получить список всех товаров из конкретной категории"""
        return await self.repo.get_all_from_category(self.session, category_id)

    async def get_all(self, pagination: PaginationParams) -> ProductListResponse:
        """Получить список всех товаров с пагинацией."""
        total = await self.repo.count_all(self.session)

        # Вычисляем offset
        offset = (pagination.page - 1) * pagination.page_size

        products = await self.repo.get_all(
            self.session, limit=pagination.page_size, offset=offset
        )

        # Вычисляем количество страниц
        total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1

        return ProductListResponse(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            items=products,
        )

    async def get_active(self, pagination: PaginationParams) -> ProductListResponse:
        """Получить список всех активных товаров с пагинацией."""
        # Подсчитываем общее количество
        total = await self.repo.count_all(self.session)

        # Вычисляем offset
        offset = (pagination.page - 1) * pagination.page_size

        # Получаем товары
        products = await self.repo.get_active(
            self.session, limit=pagination.page_size, offset=offset
        )

        # Вычисляем количество страниц
        total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1

        return ProductListResponse(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            items=products,
        )

    async def update(self, product_id: int, data: ProductUpdateSchema) -> ProductModel:
        """Обновить товар."""
        product = await self.repo.get_by_id(
            self.session, product_id, with_category=False
        )

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Товар с ID {product_id} не найден",
            )

        # Если меняется категория, проверяем её существование
        if data.category_id and data.category_id != product.category_id:
            category = await self.category_repo.get_by_id(
                self.session, data.category_id
            )

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Категория с ID {data.category_id} не найдена",
                )

        updated = await self.repo.update(self.session, product, data)
        await self.session.commit()
        await self.session.refresh(updated)

        return updated

    async def delete(self, product_id: int) -> None:
        """
        Удалить товар

        Правила:
        - Товар должен существовать
        """

        product = await self.get_by_id(product_id)

        await self.repo.delete(self.session, product)
        await self.session.commit()
