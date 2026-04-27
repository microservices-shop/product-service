"""Юнит-тесты для AttributeService."""

import pytest
from unittest.mock import AsyncMock

from sqlalchemy.exc import IntegrityError

from src.db.enums import AttributeType
from src.exceptions import NotFoundException, BadRequestException, ConflictException
from src.schemas.attributes import AttributeCreateSchema, AttributeUpdateSchema
from src.services.attributes import AttributeService


# ── Фикстуры ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_attribute_repo(mocker):
    """Мок AttributeRepository (патчим в модуле services.attributes)."""
    return mocker.patch("src.services.attributes.AttributeRepository")


@pytest.fixture
def service(mock_session):
    """AttributeService с замоканной сессией."""
    return AttributeService(mock_session)


# ── Создание атрибута ─────────────────────────────────────────────────────────


class TestCreateAttribute:
    """Тесты для AttributeService.create."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_attribute_repo,
        make_attribute,
    ):
        """Успешное создание атрибута."""
        attribute = make_attribute(title="Цвет", type=AttributeType.STRING)

        mock_attribute_repo.get_by_title_in_category = AsyncMock(return_value=None)
        mock_attribute_repo.create = AsyncMock(return_value=attribute)

        data = AttributeCreateSchema(
            category_id=1,
            title="Цвет",
            type=AttributeType.STRING,
        )
        result = await service.create(data)

        assert result == attribute
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_duplicate_in_category_raises_conflict(
        self,
        service,
        mock_session,
        mock_attribute_repo,
        make_attribute,
    ):
        """ConflictException при дубликате названия в рамках категории."""
        existing = make_attribute(title="Цвет")
        mock_attribute_repo.get_by_title_in_category = AsyncMock(
            return_value=existing,
        )

        data = AttributeCreateSchema(
            category_id=1,
            title="Цвет",
            type=AttributeType.STRING,
        )
        with pytest.raises(ConflictException):
            await service.create(data)

        mock_session.commit.assert_not_called()

    async def test_category_not_found_fk_error(
        self,
        service,
        mock_session,
        mock_attribute_repo,
    ):
        """IntegrityError по FK → NotFoundException."""
        mock_attribute_repo.get_by_title_in_category = AsyncMock(return_value=None)
        mock_attribute_repo.create = AsyncMock(
            side_effect=IntegrityError(
                "INSERT",
                {},
                Exception("attribute_definitions_category_id_fkey"),
            ),
        )

        data = AttributeCreateSchema(
            category_id=999,
            title="Цвет",
            type=AttributeType.STRING,
        )
        with pytest.raises(NotFoundException):
            await service.create(data)

        mock_session.rollback.assert_called_once()

    async def test_integrity_error_generic(
        self,
        service,
        mock_session,
        mock_attribute_repo,
    ):
        """IntegrityError без FK → BadRequestException."""
        mock_attribute_repo.get_by_title_in_category = AsyncMock(return_value=None)
        mock_attribute_repo.create = AsyncMock(
            side_effect=IntegrityError(
                "INSERT",
                {},
                Exception("some_other_constraint"),
            ),
        )

        data = AttributeCreateSchema(
            category_id=1,
            title="Цвет",
            type=AttributeType.STRING,
        )
        with pytest.raises(BadRequestException):
            await service.create(data)


# ── Получение атрибута ────────────────────────────────────────────────────────


class TestGetAttribute:
    """Тесты для AttributeService.get_by_id, get_by_title, get_all*."""

    async def test_get_by_id_success(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """Успешное получение атрибута по ID."""
        attribute = make_attribute(id=1)
        mock_attribute_repo.get_by_id = AsyncMock(return_value=attribute)

        result = await service.get_by_id(1)
        assert result == attribute

    async def test_get_by_id_not_found(self, service, mock_attribute_repo):
        """NotFoundException если атрибут не найден по ID."""
        mock_attribute_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_by_id(999)

    async def test_get_by_title_success(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """Успешное получение атрибута по названию."""
        attribute = make_attribute(title="Память")
        mock_attribute_repo.get_by_title = AsyncMock(return_value=attribute)

        result = await service.get_by_title("Память")
        assert result.title == "Память"

    async def test_get_by_title_not_found(self, service, mock_attribute_repo):
        """NotFoundException если атрибут не найден по названию."""
        mock_attribute_repo.get_by_title = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_by_title("Несуществующий")

    async def test_get_all_from_category(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """Получение списка атрибутов конкретной категории."""
        attrs = [
            make_attribute(id=1, title="Цвет"),
            make_attribute(id=2, title="Память"),
        ]
        mock_attribute_repo.get_all_from_category = AsyncMock(return_value=attrs)

        result = await service.get_all_from_category(1)
        assert len(result) == 2

    async def test_get_all(self, service, mock_attribute_repo, make_attribute):
        """Получение списка всех атрибутов."""
        attrs = [make_attribute(id=i, title=f"Attr {i}") for i in range(1, 4)]
        mock_attribute_repo.get_all = AsyncMock(return_value=attrs)

        result = await service.get_all()
        assert len(result) == 3

    async def test_get_all_empty(self, service, mock_attribute_repo):
        """Пустой список атрибутов."""
        mock_attribute_repo.get_all = AsyncMock(return_value=[])

        result = await service.get_all()
        assert result == []


# ── Обновление атрибута ───────────────────────────────────────────────────────


class TestUpdateAttribute:
    """Тесты для AttributeService.update."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_attribute_repo,
        make_attribute,
    ):
        """Успешное обновление атрибута."""
        attribute = make_attribute(id=1, category_id=1, title="Цвет")
        updated = make_attribute(id=1, category_id=1, title="Оттенок")

        mock_attribute_repo.get_by_id = AsyncMock(return_value=attribute)
        mock_attribute_repo.get_by_title_in_category = AsyncMock(return_value=None)
        mock_attribute_repo.update = AsyncMock(return_value=updated)

        data = AttributeUpdateSchema(title="Оттенок")
        result = await service.update(1, data)

        assert result == updated
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_same_title_no_conflict_check(
        self,
        service,
        mock_session,
        mock_attribute_repo,
        make_attribute,
    ):
        """Обновление без смены названия не проверяет уникальность."""
        attribute = make_attribute(id=1, title="Цвет")
        mock_attribute_repo.get_by_id = AsyncMock(return_value=attribute)
        mock_attribute_repo.update = AsyncMock(return_value=attribute)

        data = AttributeUpdateSchema(title="Цвет")
        await service.update(1, data)

        mock_attribute_repo.get_by_title_in_category.assert_not_called()

    async def test_duplicate_title_raises_conflict(
        self,
        service,
        mock_attribute_repo,
        make_attribute,
    ):
        """ConflictException при обновлении на существующее название."""
        attribute = make_attribute(id=1, category_id=1, title="Цвет")
        existing = make_attribute(id=2, category_id=1, title="Память")

        mock_attribute_repo.get_by_id = AsyncMock(return_value=attribute)
        mock_attribute_repo.get_by_title_in_category = AsyncMock(
            return_value=existing,
        )

        data = AttributeUpdateSchema(title="Память")
        with pytest.raises(ConflictException):
            await service.update(1, data)

    async def test_not_found(self, service, mock_attribute_repo):
        """NotFoundException при обновлении несуществующего атрибута."""
        mock_attribute_repo.get_by_id = AsyncMock(return_value=None)

        data = AttributeUpdateSchema(title="New")
        with pytest.raises(NotFoundException):
            await service.update(999, data)

    async def test_change_category(
        self,
        service,
        mock_session,
        mock_attribute_repo,
        make_attribute,
    ):
        """Обновление с переносом в другую категорию."""
        attribute = make_attribute(id=1, category_id=1, title="Цвет")
        updated = make_attribute(id=1, category_id=2, title="Цвет")

        mock_attribute_repo.get_by_id = AsyncMock(return_value=attribute)
        mock_attribute_repo.update = AsyncMock(return_value=updated)

        # title не меняется — проверка уникальности не нужна
        data = AttributeUpdateSchema(category_id=2)
        result = await service.update(1, data)

        assert result == updated
        mock_session.commit.assert_called_once()


# ── Удаление атрибута ─────────────────────────────────────────────────────────


class TestDeleteAttribute:
    """Тесты для AttributeService.delete."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_attribute_repo,
        make_attribute,
    ):
        """Успешное удаление атрибута."""
        attribute = make_attribute()
        mock_attribute_repo.get_by_id = AsyncMock(return_value=attribute)
        mock_attribute_repo.delete = AsyncMock()

        await service.delete(1)
        mock_session.commit.assert_called_once()

    async def test_not_found(self, service, mock_attribute_repo):
        """NotFoundException при удалении несуществующего атрибута."""
        mock_attribute_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.delete(999)
