"""
Модуль администрирования (SQLAdmin)

Предоставляет веб-интерфейс для управления товарами и категориями.
Доступен по адресу: /admin
Защищён аутентификацией через Google OAuth.
"""

from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine

from src.admin.views.categories import CategoryAdmin
from src.admin.views.products import ProductAdmin
from src.admin.views.attributes import AttributeAdmin
from src.admin.admin_auth import AdminAuth


def setup_admin(app, engine: AsyncEngine) -> Admin:
    """
    Настраивает и подключает SQLAdmin к FastAPI приложению.
    """
    authentication_backend = AdminAuth(secret_key="admin-auth")

    admin = Admin(
        app,
        engine,
        title="DevicesShop Admin",
        base_url="/admin",
        authentication_backend=authentication_backend,
    )

    # Регистрируем модели
    admin.add_view(CategoryAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(AttributeAdmin)

    return admin
