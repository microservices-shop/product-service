from sqladmin import ModelView
from src.db.models import AttributeModel


class AttributeAdmin(ModelView, model=AttributeModel):
    """Административный интерфейс для управления определениями атрибутов"""

    name = "Атрибут"
    name_plural = "Атрибуты"
    icon = "fa-solid fa-tags"

    column_list = [
        AttributeModel.id,
        AttributeModel.title,
        AttributeModel.type,
        AttributeModel.required,
        AttributeModel.category,
    ]

    column_sortable_list = [AttributeModel.id, AttributeModel.title]
    column_searchable_list = [AttributeModel.title]

    form_columns = [
        AttributeModel.title,
        AttributeModel.type,
        AttributeModel.required,
        AttributeModel.category,
    ]

    can_create = True
    can_edit = True
    can_delete = True
