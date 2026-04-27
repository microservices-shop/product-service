"""Интеграционные тесты для API /api/v1/categories."""


# ── Создание категории ────────────────────────────────────────────────────────


class TestCreateCategory:
    """POST /api/v1/categories."""

    async def test_create_201(self, client, admin_headers):
        """Успешное создание категории — 201 + корректный JSON."""
        response = await client.post(
            "/api/v1/categories",
            json={"title": "Смартфоны"},
            headers=admin_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Смартфоны"
        assert "id" in body

    async def test_create_normalizes_title(self, client, admin_headers):
        """Нормализация title при создании (strip + capitalize)."""
        response = await client.post(
            "/api/v1/categories",
            json={"title": "  ноутбуки  "},
            headers=admin_headers,
        )

        assert response.status_code == 201
        assert response.json()["title"] == "Ноутбуки"

    async def test_create_duplicate_409(self, client, admin_headers):
        """Создание категории с существующим названием — 409 conflict."""
        # Первая — ОК
        resp1 = await client.post(
            "/api/v1/categories",
            json={"title": "Планшеты"},
            headers=admin_headers,
        )
        assert resp1.status_code == 201

        # Дубль — конфликт
        resp2 = await client.post(
            "/api/v1/categories",
            json={"title": "Планшеты"},
            headers=admin_headers,
        )
        assert resp2.status_code == 409
        assert resp2.json()["error_type"] == "conflict"

    async def test_create_without_admin_403(self, client):
        """Создание без X-User-Role — 403."""
        response = await client.post(
            "/api/v1/categories",
            json={"title": "Тест"},
        )

        assert response.status_code == 403

    async def test_create_wrong_role_403(self, client):
        """Создание с X-User-Role: user — 403."""
        response = await client.post(
            "/api/v1/categories",
            json={"title": "Тест"},
            headers={"X-User-Role": "user"},
        )

        assert response.status_code == 403

    async def test_create_empty_title_422(self, client, admin_headers):
        """Пустое тело запроса — 422."""
        response = await client.post(
            "/api/v1/categories",
            json={},
            headers=admin_headers,
        )

        assert response.status_code == 422

    async def test_create_title_too_long_422(self, client, admin_headers):
        """Слишком длинное название (>100 символов) — 422."""
        response = await client.post(
            "/api/v1/categories",
            json={"title": "А" * 101},
            headers=admin_headers,
        )

        assert response.status_code == 422


# ── Получение категории ──────────────────────────────────────────────────────


class TestGetCategory:
    """GET /api/v1/categories/{category_id}."""

    async def test_get_200(self, client, admin_headers):
        """Успешное получение категории — 200."""
        create_resp = await client.post(
            "/api/v1/categories",
            json={"title": "Телевизоры"},
            headers=admin_headers,
        )
        category_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/categories/{category_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == category_id
        assert body["title"] == "Телевизоры"

    async def test_get_not_found_404(self, client):
        """Несуществующий ID — 404."""
        response = await client.get("/api/v1/categories/99999")

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"


# ── Список категорий ─────────────────────────────────────────────────────────


class TestGetAllCategories:
    """GET /api/v1/categories."""

    async def test_list_200(self, client, admin_headers):
        """Получение списка — 200 со всеми категориями."""
        # Создаём 3 категории
        for title in ["Категория X", "Категория Y", "Категория Z"]:
            await client.post(
                "/api/v1/categories",
                json={"title": title},
                headers=admin_headers,
            )

        response = await client.get("/api/v1/categories")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 3
        titles = {cat["title"] for cat in body}
        assert titles == {"Категория x", "Категория y", "Категория z"}

    async def test_list_empty(self, client):
        """Пустая БД — пустой список."""
        response = await client.get("/api/v1/categories")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_no_auth_required(self, client, admin_headers):
        """Получение списка не требует авторизации."""
        await client.post(
            "/api/v1/categories",
            json={"title": "Публичная"},
            headers=admin_headers,
        )

        response = await client.get("/api/v1/categories")

        assert response.status_code == 200
        assert len(response.json()) == 1


# ── Атрибуты категории ───────────────────────────────────────────────────────


class TestGetCategoryAttributes:
    """GET /api/v1/categories/{category_id}/attributes."""

    async def test_attributes_empty(self, client, admin_headers):
        """Категория без атрибутов — пустой список."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Без атрибутов"},
                headers=admin_headers,
            )
        ).json()

        response = await client.get(
            f"/api/v1/categories/{cat['id']}/attributes",
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_attributes_with_data(self, client, admin_headers):
        """Категория с атрибутами — возвращает список."""
        # Создаём категорию
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "С атрибутами"},
                headers=admin_headers,
            )
        ).json()

        # Создаём атрибуты
        for attr in [
            {"title": "Цвет", "type": "string", "category_id": cat["id"]},
            {
                "title": "Вес",
                "type": "number",
                "category_id": cat["id"],
                "required": True,
            },
        ]:
            resp = await client.post("/api/v1/attributes", json=attr)
            assert resp.status_code == 201, resp.text

        # Получаем атрибуты категории
        response = await client.get(
            f"/api/v1/categories/{cat['id']}/attributes",
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        titles = {a["title"] for a in body}
        assert titles == {"Цвет", "Вес"}
        # Проверяем поля ответа
        attr_vес = next(a for a in body if a["title"] == "Вес")
        assert attr_vес["type"] == "number"
        assert attr_vес["required"] is True
        assert attr_vес["category_id"] == cat["id"]

    async def test_attributes_category_not_found_404(self, client):
        """Получение атрибутов несуществующей категории — 404."""
        response = await client.get("/api/v1/categories/99999/attributes")

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"


# ── Обновление категории ─────────────────────────────────────────────────────


class TestUpdateCategory:
    """PATCH /api/v1/categories/{category_id}."""

    async def test_update_200(self, client, admin_headers):
        """Успешное обновление — 200 + обновлённые данные."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Старое название"},
                headers=admin_headers,
            )
        ).json()

        response = await client.patch(
            f"/api/v1/categories/{cat['id']}",
            json={"title": "Новое название"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Новое название"
        assert body["id"] == cat["id"]

    async def test_update_normalizes_title(self, client, admin_headers):
        """Обновление title — нормализация (strip + capitalize)."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Тестовая"},
                headers=admin_headers,
            )
        ).json()

        response = await client.patch(
            f"/api/v1/categories/{cat['id']}",
            json={"title": "  обновлённая  "},
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Обновлённая"

    async def test_update_duplicate_title_409(self, client, admin_headers):
        """Обновление на уже занятое название — 409 conflict."""
        # Создаём 2 категории
        await client.post(
            "/api/v1/categories",
            json={"title": "Существующая"},
            headers=admin_headers,
        )
        cat2 = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Другая"},
                headers=admin_headers,
            )
        ).json()

        # Пытаемся переименовать вторую в первую
        response = await client.patch(
            f"/api/v1/categories/{cat2['id']}",
            json={"title": "Существующая"},
            headers=admin_headers,
        )

        assert response.status_code == 409
        assert response.json()["error_type"] == "conflict"

    async def test_update_same_title_200(self, client, admin_headers):
        """Обновление с тем же названием — 200 (не конфликт с самим собой)."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Моя категория"},
                headers=admin_headers,
            )
        ).json()

        response = await client.patch(
            f"/api/v1/categories/{cat['id']}",
            json={"title": "Моя категория"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Моя категория"

    async def test_update_not_found_404(self, client, admin_headers):
        """Обновление несуществующей категории — 404."""
        response = await client.patch(
            "/api/v1/categories/99999",
            json={"title": "Тест"},
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"

    async def test_update_without_admin_403(self, client, admin_headers):
        """Обновление без admin — 403."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Защищённая"},
                headers=admin_headers,
            )
        ).json()

        response = await client.patch(
            f"/api/v1/categories/{cat['id']}",
            json={"title": "Взлом"},
        )

        assert response.status_code == 403


# ── Удаление категории ───────────────────────────────────────────────────────


class TestDeleteCategory:
    """DELETE /api/v1/categories/{category_id}."""

    async def test_delete_204(self, client, admin_headers):
        """Успешное удаление — 204 + повторный GET — 404."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "На удаление"},
                headers=admin_headers,
            )
        ).json()

        response = await client.delete(
            f"/api/v1/categories/{cat['id']}",
            headers=admin_headers,
        )
        assert response.status_code == 204

        get_resp = await client.get(f"/api/v1/categories/{cat['id']}")
        assert get_resp.status_code == 404

    async def test_delete_cascades_attributes(self, client, admin_headers):
        """Удаление категории каскадно удаляет атрибуты."""
        # Создаём категорию + атрибут
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "С атрибутом"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={
                    "title": "Атрибут X",
                    "type": "string",
                    "category_id": cat["id"],
                },
            )
        ).json()

        # Удаляем категорию
        await client.delete(
            f"/api/v1/categories/{cat['id']}",
            headers=admin_headers,
        )

        # Атрибут тоже удалён
        attr_resp = await client.get(f"/api/v1/attributes/{attr['id']}")
        assert attr_resp.status_code == 404

    async def test_delete_not_found_404(self, client, admin_headers):
        """Удаление несуществующей категории — 404."""
        response = await client.delete(
            "/api/v1/categories/99999",
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"

    async def test_delete_without_admin_403(self, client, admin_headers):
        """Удаление без admin — 403."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Защищённая удаление"},
                headers=admin_headers,
            )
        ).json()

        response = await client.delete(
            f"/api/v1/categories/{cat['id']}",
        )

        assert response.status_code == 403


# ── Полный цикл CRUD ─────────────────────────────────────────────────────────


class TestCategoryCRUDCycle:
    """E2E тест: создание → чтение → обновление → удаление."""

    async def test_full_lifecycle(self, client, admin_headers):
        """Полный жизненный цикл категории через API."""
        # 1. Create
        create_resp = await client.post(
            "/api/v1/categories",
            json={"title": "Lifecycle категория"},
            headers=admin_headers,
        )
        assert create_resp.status_code == 201
        cat_id = create_resp.json()["id"]
        assert create_resp.json()["title"] == "Lifecycle категория"

        # 2. Read
        get_resp = await client.get(f"/api/v1/categories/{cat_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Lifecycle категория"

        # 3. Read all
        list_resp = await client.get("/api/v1/categories")
        assert list_resp.status_code == 200
        ids = [c["id"] for c in list_resp.json()]
        assert cat_id in ids

        # 4. Update
        update_resp = await client.patch(
            f"/api/v1/categories/{cat_id}",
            json={"title": "Обновлённая lifecycle"},
            headers=admin_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Обновлённая lifecycle"

        # 5. Verify update
        verify_resp = await client.get(f"/api/v1/categories/{cat_id}")
        assert verify_resp.json()["title"] == "Обновлённая lifecycle"

        # 6. Delete
        delete_resp = await client.delete(
            f"/api/v1/categories/{cat_id}",
            headers=admin_headers,
        )
        assert delete_resp.status_code == 204

        # 7. Verify deletion
        gone_resp = await client.get(f"/api/v1/categories/{cat_id}")
        assert gone_resp.status_code == 404

    async def test_category_with_attributes_lifecycle(self, client, admin_headers):
        """Жизненный цикл: категория → атрибуты → проверка → удаление."""
        # 1. Создаём категорию
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Электроника"},
                headers=admin_headers,
            )
        ).json()

        # 2. Добавляем атрибуты
        await client.post(
            "/api/v1/attributes",
            json={"title": "Бренд", "type": "string", "category_id": cat["id"]},
        )
        await client.post(
            "/api/v1/attributes",
            json={
                "title": "Мощность",
                "type": "number",
                "category_id": cat["id"],
                "required": True,
            },
        )

        # 3. Получаем атрибуты через endpoint категории
        attrs_resp = await client.get(
            f"/api/v1/categories/{cat['id']}/attributes",
        )
        assert attrs_resp.status_code == 200
        assert len(attrs_resp.json()) == 2

        # 4. Удаляем категорию — атрибуты каскадно удалены
        await client.delete(
            f"/api/v1/categories/{cat['id']}",
            headers=admin_headers,
        )

        # 5. Проверяем что атрибуты из /attributes тоже пропали
        all_attrs = await client.get(
            f"/api/v1/attributes?category_id={cat['id']}",
        )
        assert all_attrs.status_code == 200
        assert all_attrs.json() == []
