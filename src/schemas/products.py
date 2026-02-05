from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator

from src.db.enums import ProductStatus
from src.schemas.categories import CategoryResponseSchema
from src.schemas.common import PaginatedResponse
from src.utils import normalize_title


class ProductCreateSchema(BaseModel):
    """Схема для создания продукта."""

    title: str = Field(
        ..., max_length=255, description="Название товара", example="iPhone 15 Pro"
    )
    price: int = Field(..., ge=0, description="Цена в копейках", example=99990)
    category_id: int = Field(..., gt=0, description="ID категории товара", example=1)
    description: str | None = Field(
        None,
        description="Описание товара",
        example="Новый смартфон от Apple с титановым корпусом",
    )
    images: list[str] = Field(
        default_factory=list,
        description="Список URL изображений товара",
        example=["https://example.com/image1.jpg"],
    )
    stock: int = Field(
        default=0,
        ge=0,
        description="Количество товара в наличии",
        example=100,
    )
    status: ProductStatus = Field(
        default=ProductStatus.ACTIVE,
        description="Статус товара",
        example=ProductStatus.ACTIVE.value,
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Динамические атрибуты товара в формате JSONB",
        example={"color": "Титановый", "memory": "256GB"},
    )

    @field_validator("title")
    @classmethod
    def validate_and_normalize_title(cls, v: str) -> str:
        """Нормализует название: удаляет лишние пробелы и капитализирует первую букву."""
        return normalize_title(v)


class ProductUpdateSchema(BaseModel):
    """Схема для обновления продукта."""

    title: str | None = Field(
        None, max_length=255, description="Название товара", example="iPhone 15 Pro"
    )
    price: int | None = Field(None, ge=0, description="Цена в копейках", example=99990)
    category_id: int | None = Field(
        None, gt=0, description="ID категории товара", example=1
    )
    description: str | None = Field(
        None,
        description="Описание товара",
        example="Новый смартфон от Apple с титановым корпусом",
    )
    images: list[str] | None = Field(
        None,
        description="Список URL изображений товара",
    )
    stock: int | None = Field(
        None,
        ge=0,
        description="Количество товара в наличии",
    )
    status: ProductStatus | None = Field(
        None, description="Статус товара", example=ProductStatus.ACTIVE.value
    )
    attributes: dict[str, Any] | None = Field(
        None,
        description="Динамические атрибуты товара в формате JSONB",
        example={"color": "Титановый", "memory": "256GB"},
    )

    @field_validator("title")
    @classmethod
    def validate_and_normalize_title(cls, v: str | None) -> str | None:
        """Нормализует название: удаляет лишние пробелы и капитализирует первую букву."""
        if v is None:
            return None
        return normalize_title(v)


class ProductResponseSchema(BaseModel):
    """Схема ответа с данными продукта."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID товара", example=1)
    title: str = Field(..., description="Название товара", example="iPhone 15 Pro")
    price: int = Field(..., description="Цена в копейках", example=99990)
    category_id: int = Field(..., description="ID категории", example=1)
    description: str | None = Field(None, description="Описание товара")
    images: list[str] = Field(
        default_factory=list, description="Список URL изображений товара"
    )
    stock: int = Field(..., description="Количество товара в наличии", example=100)
    status: ProductStatus = Field(
        ..., description="Статус товара", example=ProductStatus.ACTIVE.value
    )
    attributes: dict[str, Any] = Field(..., description="Динамические атрибуты товара")
    created_at: datetime = Field(..., description="Дата и время создания")
    updated_at: datetime = Field(..., description="Дата и время последнего обновления")


class ProductDetailResponseSchema(ProductResponseSchema):
    """Схема детальной информации о товаре."""

    category: CategoryResponseSchema = Field(..., description="Категория товара")


class ProductListResponse(PaginatedResponse):
    """Ответ со списком товаров."""

    items: list[ProductResponseSchema] = Field(..., description="Список товаров")
