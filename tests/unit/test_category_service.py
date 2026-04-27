"""Юнит-тесты для CategoryService."""

import pytest
from unittest.mock import AsyncMock

from src.exceptions import NotFoundException, ConflictException
from src.schemas.categories import CategoryCreateSchema, CategoryUpdateSchema
from src.services.categories import CategoryService


# ── Фикстуры ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_category_repo(mocker):
    """Мок CategoryRepository (патчим в модуле services.categories)."""
    return mocker.patch("src.services.categories.CategoryRepository")


@pytest.fixture
def service(mock_session):
    """CategoryService с замоканной сессией."""
    return CategoryService(mock_session)


# ── Создание категории ────────────────────────────────────────────────────────


class TestCreateCategory:
    """Тесты для CategoryService.create."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_category_repo,
        make_category,
    ):
        """Успешное создание категории."""
        category = make_category(title="Смартфоны")
        mock_category_repo.get_by_title = AsyncMock(return_value=None)
        mock_category_repo.create = AsyncMock(return_value=category)

        data = CategoryCreateSchema(title="Смартфоны")
        result = await service.create(data)

        assert result == category
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_duplicate_raises_conflict(
        self,
        service,
        mock_session,
        mock_category_repo,
        make_category,
    ):
        """ConflictException при дубликате названия."""
        existing = make_category(title="Смартфоны")
        mock_category_repo.get_by_title = AsyncMock(return_value=existing)

        data = CategoryCreateSchema(title="Смартфоны")
        with pytest.raises(ConflictException):
            await service.create(data)

        mock_session.commit.assert_not_called()


# ── Получение категории ───────────────────────────────────────────────────────


class TestGetCategory:
    """Тесты для CategoryService.get_by_id, get_by_title, get_all."""

    async def test_get_by_id_success(
        self,
        service,
        mock_category_repo,
        make_category,
    ):
        """Успешное получение категории по ID."""
        category = make_category()
        mock_category_repo.get_by_id = AsyncMock(return_value=category)

        result = await service.get_by_id(1)
        assert result == category

    async def test_get_by_id_not_found(self, service, mock_category_repo):
        """NotFoundException если категория не найдена по ID."""
        mock_category_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_by_id(999)

    async def test_get_by_title_success(
        self,
        service,
        mock_category_repo,
        make_category,
    ):
        """Успешное получение категории по названию."""
        category = make_category(title="Ноутбуки")
        mock_category_repo.get_by_title = AsyncMock(return_value=category)

        result = await service.get_by_title("Ноутбуки")
        assert result.title == "Ноутбуки"

    async def test_get_by_title_not_found(self, service, mock_category_repo):
        """NotFoundException если категория не найдена по названию."""
        mock_category_repo.get_by_title = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_by_title("Несуществующая")

    async def test_get_all(self, service, mock_category_repo, make_category):
        """Получение списка всех категорий."""
        categories = [
            make_category(id=1, title="Смартфоны"),
            make_category(id=2, title="Ноутбуки"),
            make_category(id=3, title="Планшеты"),
        ]
        mock_category_repo.get_all = AsyncMock(return_value=categories)

        result = await service.get_all()
        assert len(result) == 3

    async def test_get_all_empty(self, service, mock_category_repo):
        """Пустой список категорий."""
        mock_category_repo.get_all = AsyncMock(return_value=[])

        result = await service.get_all()
        assert result == []


# ── Обновление категории ──────────────────────────────────────────────────────


class TestUpdateCategory:
    """Тесты для CategoryService.update."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_category_repo,
        make_category,
    ):
        """Успешное обновление категории."""
        category = make_category(id=1, title="Старое название")
        updated = make_category(id=1, title="Новое название")

        mock_category_repo.get_by_id = AsyncMock(return_value=category)
        mock_category_repo.get_by_title = AsyncMock(return_value=None)
        mock_category_repo.update = AsyncMock(return_value=updated)

        data = CategoryUpdateSchema(title="Новое название")
        result = await service.update(1, data)

        assert result == updated
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_same_title_no_conflict_check(
        self,
        service,
        mock_session,
        mock_category_repo,
        make_category,
    ):
        """Обновление без смены названия не проверяет уникальность."""
        category = make_category(id=1, title="Смартфоны")
        mock_category_repo.get_by_id = AsyncMock(return_value=category)
        mock_category_repo.update = AsyncMock(return_value=category)

        data = CategoryUpdateSchema(title="Смартфоны")
        await service.update(1, data)

        # get_by_title НЕ должен вызываться для проверки уникальности
        mock_category_repo.get_by_title.assert_not_called()

    async def test_duplicate_title_raises_conflict(
        self,
        service,
        mock_category_repo,
        make_category,
    ):
        """ConflictException при обновлении на уже существующее название."""
        category = make_category(id=1, title="Смартфоны")
        existing = make_category(id=2, title="Ноутбуки")

        mock_category_repo.get_by_id = AsyncMock(return_value=category)
        mock_category_repo.get_by_title = AsyncMock(return_value=existing)

        data = CategoryUpdateSchema(title="Ноутбуки")
        with pytest.raises(ConflictException):
            await service.update(1, data)

    async def test_not_found(self, service, mock_category_repo):
        """NotFoundException при обновлении несуществующей категории."""
        mock_category_repo.get_by_id = AsyncMock(return_value=None)

        data = CategoryUpdateSchema(title="New")
        with pytest.raises(NotFoundException):
            await service.update(999, data)


# ── Удаление категории ────────────────────────────────────────────────────────


class TestDeleteCategory:
    """Тесты для CategoryService.delete."""

    async def test_success(
        self,
        service,
        mock_session,
        mock_category_repo,
        make_category,
    ):
        """Успешное удаление категории."""
        category = make_category()
        mock_category_repo.get_by_id = AsyncMock(return_value=category)
        mock_category_repo.delete = AsyncMock()

        await service.delete(1)
        mock_session.commit.assert_called_once()

    async def test_not_found(self, service, mock_category_repo):
        """NotFoundException при удалении несуществующей категории."""
        mock_category_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.delete(999)


# ── Атрибуты категории ────────────────────────────────────────────────────────


class TestGetCategoryAttributes:
    """Тесты для CategoryService.get_attributes."""

    async def test_success(
        self,
        service,
        mock_category_repo,
        make_category,
        make_attribute,
    ):
        """Успешное получение атрибутов категории."""
        attrs = [
            make_attribute(id=1, title="Цвет"),
            make_attribute(id=2, title="Память"),
        ]
        category = make_category()
        category.attribute_definitions = attrs

        mock_category_repo.get_with_attributes = AsyncMock(return_value=category)

        result = await service.get_attributes(1)
        assert len(result) == 2

    async def test_category_not_found(self, service, mock_category_repo):
        """NotFoundException для несуществующей категории."""
        mock_category_repo.get_with_attributes = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await service.get_attributes(999)

    async def test_no_attributes(
        self,
        service,
        mock_category_repo,
        make_category,
    ):
        """Категория без атрибутов возвращает пустой список."""
        category = make_category()
        category.attribute_definitions = []

        mock_category_repo.get_with_attributes = AsyncMock(return_value=category)

        result = await service.get_attributes(1)
        assert result == []
