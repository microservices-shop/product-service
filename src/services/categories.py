from fastapi import status, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import CategoryModel
from src.repositories.categories import CategoryRepository

from src.schemas.categories import CategoryCreateSchema, CategoryUpdateSchema


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CategoryRepository()

    def _normalize_title(self, title: str) -> str:
        return title.strip().capitalize()

    async def create(self, data: CategoryCreateSchema) -> CategoryModel:
        """
        Создать новую категорию

        Правила:
        - Название категории должно быть уникальным
        """

        existing = await self.repo.get_by_title(self.session, data.title)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Категория '{data.title}' уже существует",
            )

        category = await self.repo.create(self.session, data)
        await self.session.commit()
        return category

    async def get_by_id(self, category_id: int) -> CategoryModel:
        """
        Получить категорию по ID

        :raises HTTPException 404: Если категория не найдена
        """

        category = await self.repo.get_by_id(self.session, category_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Категория с ID '{category_id}' не найдена",
            )

        return category

    async def get_by_title(self, category_title: str) -> CategoryModel:
        """
        Получить категорию по названию

        :raises HTTPException 404: Если категория не найдена
        """

        normalized_title = self._normalize_title(category_title)
        category = await self.repo.get_by_title(self.session, normalized_title)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Категория с названием '{normalized_title}' не найдена",
            )

        return category

    async def get_all(self) -> list[CategoryModel]:
        """Получить список всех категорий"""
        return await self.repo.get_all(self.session)

    async def update(
        self, category_id: int, data: CategoryUpdateSchema
    ) -> CategoryModel:
        """
        Обновить категорию

        Правила:
        - Категория должна существовать
        - Название должно быть уникальным
        """

        category = await self.get_by_id(category_id)

        # Проверка уникальности при смене названия
        if data.title and data.title != category.title:
            existing = await self.repo.get_by_title(self.session, data.title)

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Категория с названием '{data.title}' уже существует",
                )

        updated = await self.repo.update(self.session, category, data)
        await self.session.commit()

        return updated

    async def delete(self, category_id: int) -> None:
        """
        Удалить категорию

        Правила:
        - Категория должна существовать
        """

        category = await self.get_by_id(category_id)

        await self.repo.delete(self.session, category)
        await self.session.commit()
