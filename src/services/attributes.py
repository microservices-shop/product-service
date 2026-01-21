from fastapi import status, HTTPException
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AttributeModel
from src.repositories.attributes import AttributeRepository

from src.schemas.attributes import AttributeCreateSchema, AttributeUpdateSchema


class AttributeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AttributeRepository()

    def _normalize_title(self, title: str) -> str:
        return title.strip().capitalize()

    async def create(self, data: AttributeCreateSchema) -> AttributeModel:
        """
        Создать новый атрибут

        Правила:
        - Название атрибута должно быть уникальным
        """

        existing = await self.repo.get_by_title(self.session, data.title)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Атрибут '{data.title}' уже существует",
            )

        try:
            attribute = await self.repo.create(self.session, data)
            await self.session.commit()

            # Перезагружаем объект
            await self.session.refresh(attribute)

            return attribute
        except IntegrityError as e:
            await self.session.rollback()

            if "attribute_definitions_category_id_fkey" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Категория с ID {data.category_id} не найдена",
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка целостности данных",
            )

    async def get_by_id(self, attribute_id: int) -> AttributeModel:
        """
        Получить атрибут по ID

        :raises HTTPException 404: Если атрибут не найден
        """

        attribute = await self.repo.get_by_id(self.session, attribute_id)

        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Атрибут с ID '{attribute_id}' не найден",
            )

        return attribute

    async def get_by_title(self, attribute: str) -> AttributeModel:
        """
        Получить атрибут по названию

        :raises HTTPException 404: Если атрибут не найден
        """

        normalized_title = self._normalize_title(attribute)
        attribute = await self.repo.get_by_title(self.session, normalized_title)

        if not attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Атрибут с названием '{normalized_title}' не найден",
            )

        return attribute

    async def get_all_from_category(self, category_id: int) -> list[AttributeModel]:
        """Получить список всех атрибутов из конкретной категории"""
        return await self.repo.get_all_from_category(self.session, category_id)

    async def get_all(self) -> list[AttributeModel]:
        """Получить список всех атрибутов"""
        return await self.repo.get_all(self.session)

    async def update(
        self, attribute_id: int, data: AttributeUpdateSchema
    ) -> AttributeModel:
        """
        Обновить атрибут

        Правила:
        - Атрибут должен существовать
        - Название должно быть уникальным
        """

        attribute = await self.get_by_id(attribute_id)

        # Проверка уникальности при смене названия
        if data.title and data.title != attribute.title:
            existing = await self.repo.get_by_title(self.session, data.title)

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Атрибут с названием '{data.title}' уже существует",
                )

        updated = await self.repo.update(self.session, attribute, data)
        await self.session.commit()
        await self.session.refresh(updated)

        return updated

    async def delete(self, attribute_id: int) -> None:
        """
        Удалить атрибут

        Правила:
        - Атрибут должен существовать
        """

        attribute = await self.get_by_id(attribute_id)

        await self.repo.delete(self.session, attribute)
        await self.session.commit()
