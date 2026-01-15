from fastapi import status, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ProductModel
from src.repositories.products import ProductRepository

from src.schemas.products import ProductCreateSchema, ProductUpdateSchema


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductRepository()

    def _normalize_title(self, title: str) -> str:
        return title.strip().capitalize()

    async def create(self, data: ProductCreateSchema) -> ProductModel:
        """
        Создать новый товар
        """
        product = await self.repo.create(self.session, data)
        await self.session.commit()
        return product

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

    async def get_all_from_category(self, product_id: int) -> list[ProductModel]:
        """Получить список всех товаров из конкретной категории"""
        return await self.repo.get_all_from_category(self.session, product_id)

    async def get_all(self) -> list[ProductModel]:
        """Получить список всех товаров"""
        return await self.repo.get_all(self.session)

    async def update(self, product_id: int, data: ProductUpdateSchema) -> ProductModel:
        """
        Обновить товар

        Правила:
        - Товар должен существовать
        """

        product = await self.get_by_id(product_id)

        updated = await self.repo.update(self.session, product, data)
        await self.session.commit()

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
