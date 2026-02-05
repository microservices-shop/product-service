from sqladmin import ModelView
from src.db.models import ProductModel


class ProductAdmin(ModelView, model=ProductModel):
    """Административный интерфейс для управления товарами"""

    name = "Товар"
    name_plural = "Товары"
    icon = "fa-solid fa-box"

    column_list = [
        ProductModel.id,
        ProductModel.title,
        ProductModel.price,
        ProductModel.stock,
        ProductModel.status,
        ProductModel.category,
    ]

    column_searchable_list = [ProductModel.title, ProductModel.description]
    column_sortable_list = [
        ProductModel.id,
        ProductModel.title,
        ProductModel.price,
        ProductModel.stock,
        ProductModel.created_at,
    ]

    # Настройка отображения цены (конвертация копеек в рубли)
    column_formatters = {
        ProductModel.price: lambda m, a: f"₽{m.price / 100:,.2f}",
    }

    form_columns = [
        ProductModel.title,
        ProductModel.price,
        ProductModel.category,
        ProductModel.description,
        ProductModel.images,
        ProductModel.stock,
        ProductModel.status,
        ProductModel.attributes,
    ]

    # Подсказки для полей
    form_args = {
        "price": {"description": "Цена в копейках (135000 руб = 13500000)"},
        "stock": {"description": "Количество на складе"},
        "attributes": {
            "description": (
                'JSON формат: {"Ключ": "Значение", ...}\n'
                "Примеры:\n"
                '• Смартфоны: {"Экран": "6.7 OLED", "Процессор": "A17 Pro", "Память": "256ГБ"}\n'
                '• Ноутбуки: {"Процессор": "M3", "ОЗУ": "16ГБ", "Накопитель": "512ГБ SSD"}\n'
                '• Наушники: {"Тип": "Полноразмерные", "Шумоподавление": "Да", "Батарея": "30ч"}'
            )
        },
        "images": {
            "description": (
                "Список URL изображений через запятую.\n"
                'Пример: ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]'
            )
        },
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
