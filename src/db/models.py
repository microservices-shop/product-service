from datetime import datetime


from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.database import Base
from src.db.enums import AttributeType, ProductStatus
from sqlalchemy import Enum as SAEnum, text

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Float,
    func,
    UniqueConstraint,
    Index,
    CheckConstraint,
)


class ProductModel(Base):
    """
    Модель товара в магазине.

    Поля:
        id: int - первичный ключ
        title: str - название товара (максимум 255 символов)
        price: int - цена в копейках (неотрицательное значение)
        category_id: int - внешний ключ на категорию товаров
        description: str - описание товара (опционально)
        images: list[str] - список URL изображений товара
        stock: int - количество товара в наличии
        rating: float - рейтинг товара (0-5)
        status: ProductStatus - статус товара (active/archived), по умолчанию active
        attributes: dict - динамические атрибуты товара в формате JSONB
        created_at: datetime - дата и время создания записи
        updated_at: datetime - дата и время последнего обновления записи

    Связи:
        category - связь с CategoryModel
    """

    __tablename__ = "products"

    __table_args__ = (
        Index("idx_products_category_price", "category_id", "price"),
        Index("idx_products_attributes_gin", "attributes", postgresql_using="gin"),
        CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, doc="ID товара")
    title: Mapped[str] = mapped_column(
        String(255), doc="Название товара с ограничением на длину в 255 символов"
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False, doc="Цена в копейках")
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK: категория товаров",
    )
    description: Mapped[str] = mapped_column(Text, nullable=True, doc="Описание товара")
    images: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'"),
        doc="Список URL изображений товара",
    )
    stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        doc="Количество товара в наличии",
    )
    rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default=text("0.0"),
        doc="Рейтинг товара (0-5)",
    )
    status: Mapped[ProductStatus] = mapped_column(
        SAEnum(ProductStatus, name="product_status"),
        nullable=False,
        server_default=text(f"'{ProductStatus.ACTIVE.value}'"),
        doc="Статус товара",
    )
    attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Динамические атрибуты товара в JSONB",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Дата и время создания записи",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        doc="Дата и время последнего обновления записи",
    )

    category = relationship("CategoryModel", back_populates="products")

    def __str__(self) -> str:
        return self.title


class CategoryModel(Base):
    """
    Модель категории товаров.

    Поля:
        id: int - первичный ключ
        title: str - название категории (максимум 100 символов)

    Связи:
        products - связь с ProductModel
        attribute_definitions - связь с AttributeModel
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, doc="ID категории")
    title: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Название категории"
    )

    products = relationship("ProductModel", back_populates="category")
    attribute_definitions = relationship(
        "AttributeModel", back_populates="category", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.title


class AttributeModel(Base):
    """
    Модель определения атрибута для категории товаров.

    Определяет структуру динамических атрибутов, которые могут быть у товаров
    данной категории. Атрибуты сохраняются в JSONB поле attributes модели ProductModel.

    Поля:
        id: int - первичный ключ
        category_id: int - внешний ключ на категорию товаров
        title: str - имя атрибута (уникально в рамках категории, максимум 50 символов)
        type: AttributeType - тип данных атрибута (string, number, boolean, enum, array)
        required: bool - обязательность заполнения атрибута при создании товара

    Связи:
        category - связь с CategoryModel

    Ограничения:
        Уникальность комбинации (category_id, title) гарантирует,
        что в рамках одной категории не может быть двух атрибутов с одинаковым именем.
    """

    __tablename__ = "attribute_definitions"
    __table_args__ = (
        UniqueConstraint("category_id", "title", name="uq_attribute_category"),
        Index("idx_attributes_category", "category_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, doc="PK: идентификатор атрибута")

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        doc="FK на categories.id - к какой категории относится атрибут",
    )

    title: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Имя атрибута, уникально в рамках category_id"
    )

    type: Mapped[AttributeType] = mapped_column(
        SAEnum(AttributeType, name="attribute_type"),
        nullable=False,
        doc="Тип атрибута (enum AttributeType)",
    )

    required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Обязателен ли атрибут при создании товара",
    )

    category = relationship("CategoryModel", back_populates="attribute_definitions")
