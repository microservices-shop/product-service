from sqladmin import ModelView
from src.db.models import CategoryModel


class CategoryAdmin(ModelView, model=CategoryModel):
    """Административный интерфейс для управления категориями"""

    name = "Категория"
    name_plural = "Категории"
    icon = "fa-solid fa-folder"

    column_list = [
        CategoryModel.id,
        CategoryModel.title,
    ]

    column_searchable_list = [CategoryModel.title]
    column_sortable_list = [CategoryModel.id, CategoryModel.title]

    form_columns = [CategoryModel.title]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
