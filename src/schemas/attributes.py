from pydantic import BaseModel, Field, ConfigDict, field_validator

from src.db.enums import AttributeType
from src.utils import normalize_title


class AttributeCreateSchema(BaseModel):
    """Схема для создания атрибута"""

    category_id: int = Field(
        ...,
        gt=0,
        description="ID категории продукта",
        example=2,
    )
    title: str = Field(
        ..., max_length=50, description="Название атрибута", example="Цвет"
    )
    type: AttributeType = Field(
        ..., description="Тип атрибута", example=AttributeType.STRING.value
    )
    required: bool = Field(
        default=False, description="Обязателен ли атрибут", example=False
    )

    @field_validator("title")
    @classmethod
    def validate_and_normalize_title(cls, v: str) -> str:
        """Нормализует название: удаляет лишние пробелы и капитализирует первую букву."""
        return normalize_title(v)


class AttributeUpdateSchema(BaseModel):
    """Схема для обновления атрибута"""

    category_id: int | None = Field(
        None, gt=0, description="ID категории продукта", example=2
    )
    title: str | None = Field(
        None, max_length=50, description="Название атрибута", example="Цвет"
    )
    type: AttributeType | None = Field(
        None, description="Тип атрибута", example=AttributeType.STRING.value
    )
    required: bool | None = Field(
        None, description="Обязателен ли атрибут", example=False
    )

    @field_validator("title")
    @classmethod
    def validate_and_normalize_title(cls, v: str | None) -> str | None:
        """Нормализует название: удаляет лишние пробелы и капитализирует первую букву."""
        if v is None:
            return None
        return normalize_title(v)


class AttributeResponseSchema(BaseModel):
    """Определение атрибута категории товаров"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID атрибута", example=1)
    category_id: int = Field(..., description="ID категории", example=2)
    title: str = Field(..., max_length=50, description="Название", example="Цвет")
    type: AttributeType = Field(
        ..., description="Тип данных", example=AttributeType.STRING.value
    )
    required: bool = Field(..., description="Обязательность атрибута", example=False)
