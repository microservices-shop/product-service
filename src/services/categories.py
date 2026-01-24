from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import CategoryModel
from src.exceptions import NotFoundException, ConflictException
from src.repositories.categories import CategoryRepository
from src.schemas.categories import CategoryCreateSchema, CategoryUpdateSchema


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: CategoryCreateSchema) -> CategoryModel:
        """
        Создать новую категорию

        Правила:
        - Название категории должно быть уникальным
        """
        existing = await CategoryRepository.get_by_title(self.session, data.title)

        if existing:
            raise ConflictException(f"Категория '{data.title}' уже существует")

        category = await CategoryRepository.create(self.session, data)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_by_id(self, category_id: int) -> CategoryModel:
        """
        Получить категорию по ID

        :raises NotFoundException: Если категория не найдена
        """
        category = await CategoryRepository.get_by_id(self.session, category_id)

        if not category:
            raise NotFoundException(f"Категория с ID '{category_id}' не найдена")

        return category

    async def get_by_title(self, category_title: str) -> CategoryModel:
        """
        Получить категорию по названию

        :raises NotFoundException: Если категория не найдена
        """
        category = await CategoryRepository.get_by_title(self.session, category_title)

        if not category:
            raise NotFoundException(
                f"Категория с названием '{category_title}' не найдена"
            )

        return category

    async def get_all(self) -> list[CategoryModel]:
        """Получить список всех категорий"""
        return await CategoryRepository.get_all(self.session)

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
            existing = await CategoryRepository.get_by_title(self.session, data.title)

            if existing:
                raise ConflictException(
                    f"Категория с названием '{data.title}' уже существует"
                )

        updated = await CategoryRepository.update(self.session, category, data)
        await self.session.commit()
        await self.session.refresh(updated)

        return updated

    async def delete(self, category_id: int) -> None:
        """
        Удалить категорию

        Правила:
        - Категория должна существовать
        """
        category = await self.get_by_id(category_id)

        await CategoryRepository.delete(self.session, category)
        await self.session.commit()
