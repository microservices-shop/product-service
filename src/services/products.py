import math
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.db.models import ProductModel
from src.db.enums import AttributeType
from src.exceptions import NotFoundException, BadRequestException, ValidationException
from src.repositories.categories import CategoryRepository
from src.repositories.products import ProductRepository
from src.repositories.attributes import AttributeRepository
from src.schemas.common import PaginationParams
from src.schemas.internal import (
    ReserveRequestSchema,
    ReserveResponseSchema,
    ReserveItemSchema,
)
from src.schemas.products import (
    ProductCreateSchema,
    ProductUpdateSchema,
    ProductListResponse,
)
from src.services.cart_webhook import CartWebhookClient


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cart_webhook = CartWebhookClient()

    async def _validate_product_attributes(
        self, category_id: int, attributes: dict[str, Any]
    ) -> None:
        """
        Валидация атрибутов товара на соответствие определениям категории.

        :raises ValidationException: Если атрибуты не соответствуют определениям
        """
        # Получаем определения атрибутов для категории
        attribute_definitions = await AttributeRepository.get_all_from_category(
            self.session, category_id
        )

        errors = []

        # Создаём словарь определений для быстрого доступа
        definitions_map = {attr.title.lower(): attr for attr in attribute_definitions}

        # Проверяем обязательные атрибуты
        for attr_def in attribute_definitions:
            if attr_def.required:
                # Ищем атрибут без учёта регистра
                found = any(
                    key.lower() == attr_def.title.lower() for key in attributes.keys()
                )
                if not found:
                    errors.append(
                        {
                            "field": attr_def.title,
                            "message": f"Обязательный атрибут '{attr_def.title}' не указан",
                        }
                    )

        # Валидация типов атрибутов
        for attr_name, attr_value in attributes.items():
            attr_def = definitions_map.get(attr_name.lower())

            if attr_def:
                type_error = self._validate_attribute_type(
                    attr_name, attr_value, attr_def.type
                )
                if type_error:
                    errors.append(type_error)

        if errors:
            raise ValidationException(
                message="Ошибки валидации атрибутов товара",
                errors=errors,
            )

    def _validate_attribute_type(
        self, name: str, value: Any, expected_type: AttributeType
    ) -> dict | None:
        """Проверка соответствия типа атрибута."""
        type_checks = {
            AttributeType.STRING: lambda v: isinstance(v, str),
            AttributeType.NUMBER: lambda v: isinstance(v, (int, float)),
            AttributeType.BOOLEAN: lambda v: isinstance(v, bool),
            AttributeType.ARRAY: lambda v: isinstance(v, list),
            AttributeType.ENUM: lambda v: isinstance(v, str),  # enum как строка
        }

        check_fn = type_checks.get(expected_type)
        if check_fn and not check_fn(value):
            return {
                "field": name,
                "message": f"Атрибут '{name}' должен быть типа {expected_type.value}",
            }
        return None

    async def create(self, data: ProductCreateSchema) -> ProductModel:
        """Создать новый товар."""
        category = await CategoryRepository.get_by_id(self.session, data.category_id)

        if not category:
            raise NotFoundException(f"Категория с ID {data.category_id} не найдена")

        # Валидация атрибутов
        if data.attributes:
            await self._validate_product_attributes(data.category_id, data.attributes)

        try:
            product = await ProductRepository.create(self.session, data)
            await self.session.commit()
            await self.session.refresh(product, ["category"])
            return product
        except IntegrityError as e:
            await self.session.rollback()

            if "products_category_id_fkey" in str(e):
                raise NotFoundException(f"Категория с ID {data.category_id} не найдена")

            raise BadRequestException("Ошибка целостности данных")

    async def get_by_id(self, product_id: int) -> ProductModel:
        """
        Получить товар по ID

        :raises NotFoundException: Если товар не найден
        """
        product = await ProductRepository.get_by_id(self.session, product_id)

        if not product:
            raise NotFoundException(f"Товар с ID '{product_id}' не найден")

        return product

    async def get_by_title(self, product: str) -> ProductModel:
        """
        Получить товар по названию

        :raises NotFoundException: Если товар не найден
        """
        product = await ProductRepository.get_by_title(self.session, product)

        if not product:
            raise NotFoundException(f"Товар с названием '{product}' не найден")

        return product

    async def get_all_from_category(self, category_id: int) -> list[ProductModel]:
        """Получить список всех товаров из конкретной категории"""
        return await ProductRepository.get_all_from_category(self.session, category_id)

    async def get_all(
        self,
        pagination: PaginationParams,
        sort_by: str = "id",
        sort_order: str = "asc",
        search: str | None = None,
        category_id: int | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
    ) -> ProductListResponse:
        """Получить список всех товаров с пагинацией, сортировкой и фильтрацией."""
        total = await ProductRepository.count_filtered(
            self.session,
            search=search,
            category_id=category_id,
            price_min=price_min,
            price_max=price_max,
        )

        # Вычисляем offset
        offset = (pagination.page - 1) * pagination.page_size

        products = await ProductRepository.get_all(
            self.session,
            limit=pagination.page_size,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            category_id=category_id,
            price_min=price_min,
            price_max=price_max,
        )

        # Вычисляем количество страниц
        total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1

        return ProductListResponse(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            items=products,
        )

    async def get_active(self, pagination: PaginationParams) -> ProductListResponse:
        """Получить список всех активных товаров с пагинацией."""
        total = await ProductRepository.count_active(self.session)
        offset = (pagination.page - 1) * pagination.page_size

        products = await ProductRepository.get_active(
            self.session, limit=pagination.page_size, offset=offset
        )

        # Вычисляем количество страниц
        total_pages = math.ceil(total / pagination.page_size) if total > 0 else 1

        return ProductListResponse(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            items=products,
        )

    async def update(self, product_id: int, data: ProductUpdateSchema) -> ProductModel:
        """Обновить товар."""
        product = await ProductRepository.get_by_id(
            self.session, product_id, with_category=False
        )

        if not product:
            raise NotFoundException(f"Товар с ID {product_id} не найден")

        # Запоминаем старые значения ДО обновления (для webhook'ов)
        old_title = product.title
        old_price = product.price
        old_images = list(product.images) if product.images else []
        old_stock = product.stock

        # Определяем category_id для валидации атрибутов
        target_category_id = data.category_id or product.category_id

        # Если меняется категория, проверяем её существование
        if data.category_id and data.category_id != product.category_id:
            category = await CategoryRepository.get_by_id(
                self.session, data.category_id
            )

            if not category:
                raise NotFoundException(f"Категория с ID {data.category_id} не найдена")

        if data.attributes:
            await self._validate_product_attributes(target_category_id, data.attributes)

        updated = await ProductRepository.update(self.session, product, data)
        await self.session.commit()
        await self.session.refresh(updated)

        # --- Отправка webhook'ов ПОСЛЕ успешного коммита ---

        # Если изменился title, price или images → notify_product_updated
        if (
            updated.title != old_title
            or updated.price != old_price
            or list(updated.images or []) != old_images
        ):
            await self._cart_webhook.notify_product_updated(
                product_id=product_id,
                title=updated.title,
                price=updated.price,
                image_url=updated.images[0] if updated.images else None,
            )

        # Если stock стал 0 (и раньше был > 0) → out_of_stock
        if updated.stock == 0 and old_stock > 0:
            await self._cart_webhook.notify_out_of_stock(product_id)

        # Если stock стал > 0 (и раньше был 0) → back_in_stock
        if updated.stock > 0 and old_stock == 0:
            await self._cart_webhook.notify_back_in_stock(product_id)

        return updated

    async def delete(self, product_id: int) -> None:
        """
        Удалить товар

        Правила:
        - Товар должен существовать
        """
        product = await self.get_by_id(product_id)

        await ProductRepository.delete(self.session, product)
        await self.session.commit()

        # Webhook ПОСЛЕ успешного коммита
        await self._cart_webhook.notify_product_deleted(product_id)

    async def reserve(self, data: ReserveRequestSchema) -> ReserveResponseSchema:
        """
        Резервирование товаров (уменьшение stock).

        Используется Order Service при оформлении заказа.
        Если хотя бы один товар не может быть зарезервирован,
        ни один товар не резервируется (атомарная операция).
        """
        errors = []
        products_to_reserve = []

        for item in data.items:
            product = await ProductRepository.get_by_id(
                self.session, item.product_id, with_category=False
            )
            if not product:
                errors.append(f"Товар с ID {item.product_id} не найден")
                continue
            if product.stock < item.quantity:
                errors.append(
                    f"Недостаточно товара '{product.title}' "
                    f"(запрошено: {item.quantity}, в наличии: {product.stock})"
                )
                continue
            products_to_reserve.append((product, item.quantity))

        if errors:
            return ReserveResponseSchema(success=False, errors=errors)

        reserved = []
        for product, quantity in products_to_reserve:
            product.stock -= quantity
            reserved.append(ReserveItemSchema(product_id=product.id, quantity=quantity))

        await self.session.commit()

        # Webhook: уведомить Cart Service о товарах, которые закончились (stock стал 0)
        for product, quantity in products_to_reserve:
            if product.stock == 0:
                await self._cart_webhook.notify_out_of_stock(product.id)

        return ReserveResponseSchema(success=True, reserved_items=reserved)

    async def confirm_reserve(self, data: ReserveRequestSchema) -> dict:
        """
        Подтверждение резерва.

        Stock уже был уменьшен при резервировании.
        """
        return {"status": "confirmed", "items_count": len(data.items)}

    async def cancel_reserve(self, data: ReserveRequestSchema) -> ReserveResponseSchema:
        """
        Отмена резерва.

        Вызывается при ошибке после успешного резервирования.
        """
        restored = []
        errors = []
        was_out_of_stock = []

        for item in data.items:
            product = await ProductRepository.get_by_id(
                self.session, item.product_id, with_category=False
            )
            if not product:
                errors.append(f"Товар с ID {item.product_id} не найден")
                continue

            # Запоминаем, если товар был out-of-stock до восстановления
            if product.stock == 0:
                was_out_of_stock.append(product.id)

            product.stock += item.quantity
            restored.append(
                ReserveItemSchema(product_id=product.id, quantity=item.quantity)
            )

        await self.session.commit()

        # Webhook: уведомить Cart Service о товарах, которые снова в наличии
        for product_id in was_out_of_stock:
            await self._cart_webhook.notify_back_in_stock(product_id)

        return ReserveResponseSchema(
            success=len(errors) == 0,
            reserved_items=restored,
            errors=errors,
        )
