from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Параметры пагинации."""

    page: int = Field(default=1, ge=1, description="Номер страницы")
    page_size: int = Field(
        default=9, ge=1, le=100, description="Количество элементов на странице"
    )


class PaginatedResponse(BaseModel):
    """Базовая схема для пагинированного ответа."""

    total: int = Field(..., description="Общее количество элементов")
    page: int = Field(..., description="Текущая страница")
    page_size: int = Field(..., description="Размер страницы")
    total_pages: int = Field(..., description="Всего страниц")
