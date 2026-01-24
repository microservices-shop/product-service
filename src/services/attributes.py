from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AttributeModel
from src.exceptions import NotFoundException, BadRequestException, ConflictException
from src.repositories.attributes import AttributeRepository
from src.schemas.attributes import AttributeCreateSchema, AttributeUpdateSchema


class AttributeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: AttributeCreateSchema) -> AttributeModel:
        """
        Создать новый атрибут

        Правила:
        - Название атрибута должно быть уникальным в рамках категории
        """
        existing = await AttributeRepository.get_by_title_in_category(
            self.session, data.category_id, data.title
        )

        if existing:
            raise ConflictException(
                f"Атрибут '{data.title}' уже существует в этой категории"
            )

        try:
            attribute = await AttributeRepository.create(self.session, data)
            await self.session.commit()
            await self.session.refresh(attribute)
            return attribute
        except IntegrityError as e:
            await self.session.rollback()

            if "attribute_definitions_category_id_fkey" in str(e):
                raise NotFoundException(f"Категория с ID {data.category_id} не найдена")

            raise BadRequestException("Ошибка целостности данных")

    async def get_by_id(self, attribute_id: int) -> AttributeModel:
        """
        Получить атрибут по ID

        :raises NotFoundException: Если атрибут не найден
        """
        attribute = await AttributeRepository.get_by_id(self.session, attribute_id)

        if not attribute:
            raise NotFoundException(f"Атрибут с ID '{attribute_id}' не найден")

        return attribute

    async def get_by_title(self, attribute: str) -> AttributeModel:
        """
        Получить атрибут по названию

        :raises NotFoundException: Если атрибут не найден
        """
        attribute = await AttributeRepository.get_by_title(self.session, attribute)

        if not attribute:
            raise NotFoundException(f"Атрибут с названием '{attribute}' не найден")

        return attribute

    async def get_all_from_category(self, category_id: int) -> list[AttributeModel]:
        """Получить список всех атрибутов из конкретной категории"""
        return await AttributeRepository.get_all_from_category(
            self.session, category_id
        )

    async def get_all(self) -> list[AttributeModel]:
        """Получить список всех атрибутов"""
        return await AttributeRepository.get_all(self.session)

    async def update(
        self, attribute_id: int, data: AttributeUpdateSchema
    ) -> AttributeModel:
        """
        Обновить атрибут

        Правила:
        - Атрибут должен существовать
        - Название должно быть уникальным в рамках категории
        """
        attribute = await self.get_by_id(attribute_id)

        # Определяем целевую категорию
        target_category_id = data.category_id or attribute.category_id

        # Проверка уникальности при смене названия
        if data.title and data.title != attribute.title:
            existing = await AttributeRepository.get_by_title_in_category(
                self.session, target_category_id, data.title
            )

            if existing:
                raise ConflictException(
                    f"Атрибут с названием '{data.title}' уже существует в этой категории"
                )

        updated = await AttributeRepository.update(self.session, attribute, data)
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

        await AttributeRepository.delete(self.session, attribute)
        await self.session.commit()
