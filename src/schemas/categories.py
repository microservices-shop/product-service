from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.utils import normalize_title


class CategoryCreateSchema(BaseModel):
    """Схема для создания категории."""

    title: str = Field(
        ..., max_length=100, description="Название категории", example="Смартфоны"
    )

    @field_validator("title")
    @classmethod
    def validate_and_normalize_title(cls, v: str) -> str:
        """Нормализует название: удаляет лишние пробелы и капитализирует первую букву."""
        return normalize_title(v)


class CategoryUpdateSchema(BaseModel):
    """Схема для обновления категории."""

    title: str | None = Field(
        None,
        max_length=100,
        description="Название категории",
        example="Ноутбуки",
    )

    @field_validator("title")
    @classmethod
    def validate_and_normalize_title(cls, v: str | None) -> str | None:
        """Нормализует название: удаляет лишние пробелы и капитализирует первую букву."""
        if v is None:
            return None
        return normalize_title(v)


class CategoryResponseSchema(BaseModel):
    """Схема для ответа с данными категории."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID категории", example=1)
    title: str = Field(..., description="Название категории", example="Смартфоны")
