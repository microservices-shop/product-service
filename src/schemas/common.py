from pydantic import BaseModel, Field

from src.config import settings


class PaginationParams(BaseModel):
    """Параметры пагинации."""

    page: int = Field(default=1, ge=1, description="Номер страницы")
    page_size: int = Field(
        default=settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Количество элементов на странице",
    )


class PaginatedResponse(BaseModel):
    """Базовая схема для пагинированного ответа."""

    total: int = Field(..., description="Общее количество элементов")
    page: int = Field(..., description="Текущая страница")
    page_size: int = Field(..., description="Размер страницы")
    total_pages: int = Field(..., description="Всего страниц")
