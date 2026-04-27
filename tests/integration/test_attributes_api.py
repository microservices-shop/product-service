"""Интеграционные тесты для API /api/v1/attributes."""


# ── Создание атрибута ─────────────────────────────────────────────────────────


class TestCreateAttribute:
    """POST /api/v1/attributes."""

    async def test_create_201(self, client, admin_headers):
        """Успешное создание атрибута — 201 + корректный JSON."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Смартфоны"},
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/api/v1/attributes",
            json={
                "title": "Цвет",
                "type": "string",
                "category_id": cat["id"],
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Цвет"
        assert body["type"] == "string"
        assert body["category_id"] == cat["id"]
        assert body["required"] is False
        assert "id" in body

    async def test_create_required_attribute(self, client, admin_headers):
        """Создание обязательного атрибута — required=True."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Ноутбуки"},
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/api/v1/attributes",
            json={
                "title": "Процессор",
                "type": "string",
                "category_id": cat["id"],
                "required": True,
            },
        )

        assert response.status_code == 201
        assert response.json()["required"] is True

    async def test_create_all_types(self, client, admin_headers):
        """Создание атрибутов всех типов — string, number, boolean, enum, array."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Типы"},
                headers=admin_headers,
            )
        ).json()

        types = ["string", "number", "boolean", "enum", "array"]
        for attr_type in types:
            resp = await client.post(
                "/api/v1/attributes",
                json={
                    "title": f"Attr {attr_type}",
                    "type": attr_type,
                    "category_id": cat["id"],
                },
            )
            assert resp.status_code == 201, f"Failed for type {attr_type}: {resp.text}"
            assert resp.json()["type"] == attr_type

    async def test_create_normalizes_title(self, client, admin_headers):
        """Нормализация title при создании (strip + capitalize)."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Нормализация"},
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/api/v1/attributes",
            json={
                "title": "  размер экрана  ",
                "type": "number",
                "category_id": cat["id"],
            },
        )

        assert response.status_code == 201
        assert response.json()["title"] == "Размер экрана"

    async def test_create_duplicate_in_category_409(self, client, admin_headers):
        """Создание дубликата в той же категории — 409 conflict."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Дубликаты"},
                headers=admin_headers,
            )
        ).json()

        # Первый — ОК
        resp1 = await client.post(
            "/api/v1/attributes",
            json={"title": "Вес", "type": "number", "category_id": cat["id"]},
        )
        assert resp1.status_code == 201

        # Дубль — конфликт
        resp2 = await client.post(
            "/api/v1/attributes",
            json={"title": "Вес", "type": "string", "category_id": cat["id"]},
        )
        assert resp2.status_code == 409
        assert resp2.json()["error_type"] == "conflict"

    async def test_create_same_title_different_categories(self, client, admin_headers):
        """Одинаковое название в разных категориях — ОК."""
        cat1 = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Категория 1"},
                headers=admin_headers,
            )
        ).json()
        cat2 = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Категория 2"},
                headers=admin_headers,
            )
        ).json()

        resp1 = await client.post(
            "/api/v1/attributes",
            json={"title": "Бренд", "type": "string", "category_id": cat1["id"]},
        )
        resp2 = await client.post(
            "/api/v1/attributes",
            json={"title": "Бренд", "type": "string", "category_id": cat2["id"]},
        )

        assert resp1.status_code == 201
        assert resp2.status_code == 201

    async def test_create_category_not_found_404(self, client):
        """Создание с несуществующей категорией — 404."""
        response = await client.post(
            "/api/v1/attributes",
            json={
                "title": "Несуществующая",
                "type": "string",
                "category_id": 99999,
            },
        )

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"

    async def test_create_invalid_type_422(self, client, admin_headers):
        """Невалидный тип атрибута — 422."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Валидация типа"},
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/api/v1/attributes",
            json={
                "title": "Bad",
                "type": "invalid_type",
                "category_id": cat["id"],
            },
        )

        assert response.status_code == 422

    async def test_create_missing_fields_422(self, client):
        """Отсутствие обязательных полей — 422."""
        response = await client.post(
            "/api/v1/attributes",
            json={"title": "Без типа"},
        )

        assert response.status_code == 422

    async def test_create_title_too_long_422(self, client, admin_headers):
        """Слишком длинное название (>50 символов) — 422."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Длинные названия"},
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/api/v1/attributes",
            json={
                "title": "А" * 51,
                "type": "string",
                "category_id": cat["id"],
            },
        )

        assert response.status_code == 422


# ── Получение атрибута ───────────────────────────────────────────────────────


class TestGetAttribute:
    """GET /api/v1/attributes/{attribute_id}."""

    async def test_get_200(self, client, admin_headers):
        """Успешное получение атрибута — 200."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Get-категория"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Память", "type": "number", "category_id": cat["id"]},
            )
        ).json()

        response = await client.get(f"/api/v1/attributes/{attr['id']}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == attr["id"]
        assert body["title"] == "Память"
        assert body["type"] == "number"
        assert body["category_id"] == cat["id"]

    async def test_get_not_found_404(self, client):
        """Несуществующий ID — 404."""
        response = await client.get("/api/v1/attributes/99999")

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"


# ── Список атрибутов ─────────────────────────────────────────────────────────


class TestGetAttributes:
    """GET /api/v1/attributes."""

    async def test_list_all_200(self, client, admin_headers):
        """Получение списка всех атрибутов — 200."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Листинг"},
                headers=admin_headers,
            )
        ).json()
        for title in ["Атрибут A", "Атрибут B", "Атрибут C"]:
            await client.post(
                "/api/v1/attributes",
                json={"title": title, "type": "string", "category_id": cat["id"]},
            )

        response = await client.get("/api/v1/attributes")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 3

    async def test_list_empty(self, client):
        """Пустая БД — пустой список."""
        response = await client.get("/api/v1/attributes")

        assert response.status_code == 200
        assert response.json() == []

    async def test_filter_by_category(self, client, admin_headers):
        """Фильтрация по category_id — только атрибуты нужной категории."""
        cat1 = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Фильтр A"},
                headers=admin_headers,
            )
        ).json()
        cat2 = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Фильтр B"},
                headers=admin_headers,
            )
        ).json()

        # 2 атрибута в cat1, 1 в cat2
        await client.post(
            "/api/v1/attributes",
            json={"title": "Цвет", "type": "string", "category_id": cat1["id"]},
        )
        await client.post(
            "/api/v1/attributes",
            json={"title": "Размер", "type": "number", "category_id": cat1["id"]},
        )
        await client.post(
            "/api/v1/attributes",
            json={"title": "Материал", "type": "string", "category_id": cat2["id"]},
        )

        # Фильтр по cat1
        resp1 = await client.get(f"/api/v1/attributes?category_id={cat1['id']}")
        assert resp1.status_code == 200
        assert len(resp1.json()) == 2
        for attr in resp1.json():
            assert attr["category_id"] == cat1["id"]

        # Фильтр по cat2
        resp2 = await client.get(f"/api/v1/attributes?category_id={cat2['id']}")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 1
        assert resp2.json()[0]["title"] == "Материал"

    async def test_filter_empty_category(self, client, admin_headers):
        """Фильтр по категории без атрибутов — пустой список."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Пустая фильтр"},
                headers=admin_headers,
            )
        ).json()

        response = await client.get(
            f"/api/v1/attributes?category_id={cat['id']}",
        )

        assert response.status_code == 200
        assert response.json() == []


# ── Обновление атрибута ──────────────────────────────────────────────────────


class TestUpdateAttribute:
    """PATCH /api/v1/attributes/{attribute_id}."""

    async def test_update_title_200(self, client, admin_headers):
        """Успешное обновление title — 200."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Обновление"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Старый", "type": "string", "category_id": cat["id"]},
            )
        ).json()

        response = await client.patch(
            f"/api/v1/attributes/{attr['id']}",
            json={"title": "Новый"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Новый"
        assert body["id"] == attr["id"]
        assert body["type"] == "string"
        assert body["category_id"] == cat["id"]

    async def test_update_type_200(self, client, admin_headers):
        """Обновление type — 200."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Смена типа"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={
                    "title": "Количество",
                    "type": "string",
                    "category_id": cat["id"],
                },
            )
        ).json()

        response = await client.patch(
            f"/api/v1/attributes/{attr['id']}",
            json={"type": "number"},
        )

        assert response.status_code == 200
        assert response.json()["type"] == "number"

    async def test_update_required_200(self, client, admin_headers):
        """Обновление required — 200."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Обязательность"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Гарантия", "type": "boolean", "category_id": cat["id"]},
            )
        ).json()
        assert attr["required"] is False

        response = await client.patch(
            f"/api/v1/attributes/{attr['id']}",
            json={"required": True},
        )

        assert response.status_code == 200
        assert response.json()["required"] is True

    async def test_update_normalizes_title(self, client, admin_headers):
        """Обновление title — нормализация (strip + capitalize)."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Нормализация upd"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Тест", "type": "string", "category_id": cat["id"]},
            )
        ).json()

        response = await client.patch(
            f"/api/v1/attributes/{attr['id']}",
            json={"title": "  обновлённый тест  "},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Обновлённый тест"

    async def test_update_duplicate_title_409(self, client, admin_headers):
        """Обновление на занятое название в той же категории — 409 conflict."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Конфликт upd"},
                headers=admin_headers,
            )
        ).json()

        await client.post(
            "/api/v1/attributes",
            json={"title": "Существующий", "type": "string", "category_id": cat["id"]},
        )
        attr2 = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Другой", "type": "string", "category_id": cat["id"]},
            )
        ).json()

        response = await client.patch(
            f"/api/v1/attributes/{attr2['id']}",
            json={"title": "Существующий"},
        )

        assert response.status_code == 409
        assert response.json()["error_type"] == "conflict"

    async def test_update_same_title_200(self, client, admin_headers):
        """Обновление с тем же названием — 200."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Самоконфликт"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={
                    "title": "Неизменный",
                    "type": "string",
                    "category_id": cat["id"],
                },
            )
        ).json()

        response = await client.patch(
            f"/api/v1/attributes/{attr['id']}",
            json={"title": "Неизменный"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Неизменный"

    async def test_update_not_found_404(self, client):
        """Обновление несуществующего атрибута — 404."""
        response = await client.patch(
            "/api/v1/attributes/99999",
            json={"title": "Тест"},
        )

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"


# ── Удаление атрибута ────────────────────────────────────────────────────────


class TestDeleteAttribute:
    """DELETE /api/v1/attributes/{attribute_id}."""

    async def test_delete_204(self, client, admin_headers):
        """Успешное удаление — 204 + повторный GET — 404."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "На удаление attr"},
                headers=admin_headers,
            )
        ).json()
        attr = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Удаляемый", "type": "string", "category_id": cat["id"]},
            )
        ).json()

        # Удаляем
        response = await client.delete(f"/api/v1/attributes/{attr['id']}")
        assert response.status_code == 204

        # Проверяем что удалён
        get_resp = await client.get(f"/api/v1/attributes/{attr['id']}")
        assert get_resp.status_code == 404

    async def test_delete_not_found_404(self, client):
        """Удаление несуществующего атрибута — 404."""
        response = await client.delete("/api/v1/attributes/99999")

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"

    async def test_delete_does_not_affect_others(self, client, admin_headers):
        """Удаление одного атрибута не затрагивает другие в той же категории."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Частичное удаление"},
                headers=admin_headers,
            )
        ).json()

        attr1 = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Остаётся", "type": "string", "category_id": cat["id"]},
            )
        ).json()
        attr2 = (
            await client.post(
                "/api/v1/attributes",
                json={"title": "Удаляется", "type": "number", "category_id": cat["id"]},
            )
        ).json()

        # Удаляем второй
        await client.delete(f"/api/v1/attributes/{attr2['id']}")

        # Первый на месте
        resp = await client.get(f"/api/v1/attributes/{attr1['id']}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Остаётся"

        # В категории остался один атрибут
        list_resp = await client.get(
            f"/api/v1/attributes?category_id={cat['id']}",
        )
        assert len(list_resp.json()) == 1


# ── Полный цикл CRUD ─────────────────────────────────────────────────────────


class TestAttributeCRUDCycle:
    """E2E тест: создание → чтение → обновление → удаление."""

    async def test_full_lifecycle(self, client, admin_headers):
        """Полный жизненный цикл атрибута через API."""
        # 0. Подготовка — создаём категорию
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Lifecycle attr"},
                headers=admin_headers,
            )
        ).json()

        # 1. Create
        create_resp = await client.post(
            "/api/v1/attributes",
            json={
                "title": "Диагональ",
                "type": "number",
                "category_id": cat["id"],
                "required": True,
            },
        )
        assert create_resp.status_code == 201
        attr_id = create_resp.json()["id"]
        assert create_resp.json()["title"] == "Диагональ"
        assert create_resp.json()["type"] == "number"
        assert create_resp.json()["required"] is True

        # 2. Read by ID
        get_resp = await client.get(f"/api/v1/attributes/{attr_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Диагональ"

        # 3. Read in list
        list_resp = await client.get(
            f"/api/v1/attributes?category_id={cat['id']}",
        )
        assert list_resp.status_code == 200
        ids = [a["id"] for a in list_resp.json()]
        assert attr_id in ids

        # 4. Update
        update_resp = await client.patch(
            f"/api/v1/attributes/{attr_id}",
            json={"title": "Размер экрана", "required": False},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Размер экрана"
        assert update_resp.json()["required"] is False
        assert update_resp.json()["type"] == "number"  # не изменился

        # 5. Verify update
        verify_resp = await client.get(f"/api/v1/attributes/{attr_id}")
        assert verify_resp.json()["title"] == "Размер экрана"

        # 6. Delete
        delete_resp = await client.delete(f"/api/v1/attributes/{attr_id}")
        assert delete_resp.status_code == 204

        # 7. Verify deletion
        gone_resp = await client.get(f"/api/v1/attributes/{attr_id}")
        assert gone_resp.status_code == 404

    async def test_multiple_attributes_per_category(self, client, admin_headers):
        """Работа с несколькими атрибутами одной категории."""
        cat = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Мульти-атрибуты"},
                headers=admin_headers,
            )
        ).json()

        # Создаём атрибуты разных типов
        attrs_data = [
            {"title": "Бренд", "type": "string", "required": True},
            {"title": "Цена", "type": "number"},
            {"title": "В наличии", "type": "boolean"},
            {"title": "Цвета", "type": "array"},
        ]
        created_ids = []
        for data in attrs_data:
            resp = await client.post(
                "/api/v1/attributes",
                json={**data, "category_id": cat["id"]},
            )
            assert resp.status_code == 201
            created_ids.append(resp.json()["id"])

        # Проверяем что все 4 в категории
        list_resp = await client.get(
            f"/api/v1/attributes?category_id={cat['id']}",
        )
        assert len(list_resp.json()) == 4

        # Удаляем один
        await client.delete(f"/api/v1/attributes/{created_ids[1]}")

        # Осталось 3
        list_resp2 = await client.get(
            f"/api/v1/attributes?category_id={cat['id']}",
        )
        assert len(list_resp2.json()) == 3
        remaining_ids = [a["id"] for a in list_resp2.json()]
        assert created_ids[1] not in remaining_ids
