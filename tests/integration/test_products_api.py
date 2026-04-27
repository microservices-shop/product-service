"""Интеграционные тесты для API /api/v1/products."""


# ── Создание товара ───────────────────────────────────────────────────────────


class TestCreateProduct:
    """POST /api/v1/products."""

    async def test_create_201(self, client, admin_headers, created_category):
        """Успешное создание товара — 201 + корректный JSON."""
        response = await client.post(
            "/api/v1/products",
            json={
                "title": "Samsung Galaxy S24",
                "price": 79990,
                "category_id": created_category["id"],
                "description": "Флагманский смартфон Samsung",
                "stock": 25,
            },
            headers=admin_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Samsung galaxy s24"
        assert body["price"] == 79990
        assert body["category_id"] == created_category["id"]
        assert body["stock"] == 25
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body

    async def test_create_with_defaults(self, client, admin_headers, created_category):
        """Создание с минимальными полями — defaults применяются."""
        response = await client.post(
            "/api/v1/products",
            json={
                "title": "Минимальный товар",
                "price": 100,
                "category_id": created_category["id"],
            },
            headers=admin_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["stock"] == 0
        assert body["images"] == []
        assert body["attributes"] == {}
        assert body["status"] == "active"

    async def test_create_category_not_found_404(self, client, admin_headers):
        """Создание с несуществующей категорией — 404."""
        response = await client.post(
            "/api/v1/products",
            json={
                "title": "Test product",
                "price": 100,
                "category_id": 99999,
            },
            headers=admin_headers,
        )

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"

    async def test_create_without_admin_403(self, client):
        """Создание без заголовка X-User-Role — 403."""
        response = await client.post(
            "/api/v1/products",
            json={"title": "Test", "price": 100, "category_id": 1},
        )

        assert response.status_code == 403

    async def test_create_wrong_role_403(self, client):
        """Создание с X-User-Role: user — 403."""
        response = await client.post(
            "/api/v1/products",
            json={"title": "Test", "price": 100, "category_id": 1},
            headers={"X-User-Role": "user"},
        )

        assert response.status_code == 403

    async def test_create_negative_price_422(self, client, admin_headers):
        """Отрицательная цена — 422."""
        response = await client.post(
            "/api/v1/products",
            json={"title": "Test", "price": -1, "category_id": 1},
            headers=admin_headers,
        )

        assert response.status_code == 422


# ── Получение товара ──────────────────────────────────────────────────────────


class TestGetProduct:
    """GET /api/v1/products/{product_id}."""

    async def test_get_200(self, client, created_product):
        """Успешное получение товара — 200 + данные с категорией."""
        product_id = created_product["id"]
        response = await client.get(f"/api/v1/products/{product_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == product_id
        assert body["title"] == created_product["title"]
        assert body["price"] == created_product["price"]
        assert "category" in body
        assert body["category"]["title"] == "Смартфоны"

    async def test_get_not_found_404(self, client):
        """Несуществующий ID — 404."""
        response = await client.get("/api/v1/products/99999")

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"


# ── Список товаров ────────────────────────────────────────────────────────────


class TestGetProducts:
    """GET /api/v1/products."""

    async def test_list_200(self, client, created_product):
        """Получение списка — 200 с пагинацией."""
        response = await client.get("/api/v1/products")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert "items" in body
        assert len(body["items"]) >= 1

    async def test_pagination(self, client, admin_headers, created_category):
        """Пагинация: page_size=2 разбивает результаты на страницы."""
        # Создаём 3 товара
        for i in range(3):
            await client.post(
                "/api/v1/products",
                json={
                    "title": f"Product {i}",
                    "price": 100 * (i + 1),
                    "category_id": created_category["id"],
                },
                headers=admin_headers,
            )

        # Первая страница
        resp1 = await client.get("/api/v1/products?page=1&page_size=2")
        body1 = resp1.json()
        assert resp1.status_code == 200
        assert len(body1["items"]) == 2
        assert body1["total"] == 3
        assert body1["total_pages"] == 2

        # Вторая страница
        resp2 = await client.get("/api/v1/products?page=2&page_size=2")
        body2 = resp2.json()
        assert len(body2["items"]) == 1

    async def test_search_filter(self, client, admin_headers, created_category):
        """Фильтрация по search (ILIKE по названию)."""
        # Создаём товары с разными названиями
        for title in ["Apple iPhone", "Samsung Galaxy", "Apple MacBook"]:
            await client.post(
                "/api/v1/products",
                json={
                    "title": title,
                    "price": 100,
                    "category_id": created_category["id"],
                },
                headers=admin_headers,
            )

        response = await client.get("/api/v1/products?search=apple")

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 2
        for item in items:
            assert "apple" in item["title"].lower()

    async def test_category_filter(self, client, admin_headers):
        """Фильтрация по category_id."""
        # Создаём 2 категории
        cat1 = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Категория A"},
                headers=admin_headers,
            )
        ).json()
        cat2 = (
            await client.post(
                "/api/v1/categories",
                json={"title": "Категория B"},
                headers=admin_headers,
            )
        ).json()

        # Товары в разных категориях
        await client.post(
            "/api/v1/products",
            json={"title": "Product A1", "price": 100, "category_id": cat1["id"]},
            headers=admin_headers,
        )
        await client.post(
            "/api/v1/products",
            json={"title": "Product A2", "price": 200, "category_id": cat1["id"]},
            headers=admin_headers,
        )
        await client.post(
            "/api/v1/products",
            json={"title": "Product B1", "price": 300, "category_id": cat2["id"]},
            headers=admin_headers,
        )

        response = await client.get(f"/api/v1/products?category_id={cat1['id']}")
        items = response.json()["items"]
        assert len(items) == 2
        for item in items:
            assert item["category_id"] == cat1["id"]

    async def test_price_filter(self, client, admin_headers, created_category):
        """Фильтрация по price_min / price_max."""
        for price in [50, 150, 250]:
            await client.post(
                "/api/v1/products",
                json={
                    "title": f"Price {price}",
                    "price": price,
                    "category_id": created_category["id"],
                },
                headers=admin_headers,
            )

        response = await client.get(
            "/api/v1/products?price_min=100&price_max=200",
        )
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["price"] == 150

    async def test_sorting_by_price_asc(self, client, admin_headers, created_category):
        """Сортировка по цене (asc)."""
        for price in [300, 100, 200]:
            await client.post(
                "/api/v1/products",
                json={
                    "title": f"Sort {price}",
                    "price": price,
                    "category_id": created_category["id"],
                },
                headers=admin_headers,
            )

        response = await client.get(
            "/api/v1/products?sort_by=price&sort_order=asc",
        )
        items = response.json()["items"]
        prices = [item["price"] for item in items]
        assert prices == sorted(prices)

    async def test_sorting_by_price_desc(self, client, admin_headers, created_category):
        """Сортировка по цене (desc)."""
        for price in [300, 100, 200]:
            await client.post(
                "/api/v1/products",
                json={
                    "title": f"SortDesc {price}",
                    "price": price,
                    "category_id": created_category["id"],
                },
                headers=admin_headers,
            )

        response = await client.get(
            "/api/v1/products?sort_by=price&sort_order=desc",
        )
        items = response.json()["items"]
        prices = [item["price"] for item in items]
        assert prices == sorted(prices, reverse=True)

    async def test_empty_result(self, client):
        """Пустая БД — total=0, items=[]."""
        response = await client.get("/api/v1/products")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["items"] == []
        assert body["total_pages"] == 1


# ── Обновление товара ─────────────────────────────────────────────────────────


class TestUpdateProduct:
    """PATCH /api/v1/products/{product_id}."""

    async def test_update_200(self, client, admin_headers, created_product):
        """Успешное обновление — 200 + обновлённые данные."""
        product_id = created_product["id"]
        response = await client.patch(
            f"/api/v1/products/{product_id}",
            json={"price": 89990, "description": "Обновлённое описание"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["price"] == 89990
        assert body["description"] == "Обновлённое описание"
        assert body["title"] == created_product["title"]
        assert body["stock"] == created_product["stock"]

    async def test_update_title_normalizes(
        self,
        client,
        admin_headers,
        created_product,
    ):
        """Обновление title — нормализация (strip + capitalize)."""
        response = await client.patch(
            f"/api/v1/products/{created_product['id']}",
            json={"title": "  samsung galaxy  "},
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Samsung galaxy"

    async def test_update_not_found_404(self, client, admin_headers):
        """Обновление несуществующего товара — 404."""
        response = await client.patch(
            "/api/v1/products/99999",
            json={"price": 100},
            headers=admin_headers,
        )

        assert response.status_code == 404

    async def test_update_without_admin_403(self, client, created_product):
        """Обновление без admin — 403."""
        response = await client.patch(
            f"/api/v1/products/{created_product['id']}",
            json={"price": 100},
        )

        assert response.status_code == 403


# ── Удаление товара ───────────────────────────────────────────────────────────


class TestDeleteProduct:
    """DELETE /api/v1/products/{product_id}."""

    async def test_delete_204(self, client, admin_headers, created_product):
        """Успешное удаление — 204 + повторный GET — 404."""
        product_id = created_product["id"]

        response = await client.delete(
            f"/api/v1/products/{product_id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # Проверяем что товар удалён
        get_response = await client.get(f"/api/v1/products/{product_id}")
        assert get_response.status_code == 404

    async def test_delete_not_found_404(self, client, admin_headers):
        """Удаление несуществующего товара — 404."""
        response = await client.delete(
            "/api/v1/products/99999",
            headers=admin_headers,
        )

        assert response.status_code == 404

    async def test_delete_without_admin_403(self, client, created_product):
        """Удаление без admin — 403."""
        response = await client.delete(
            f"/api/v1/products/{created_product['id']}",
        )

        assert response.status_code == 403


# ── Полный цикл CRUD ─────────────────────────────────────────────────────────


class TestProductCRUDCycle:
    """E2E тест: создание → чтение → обновление → удаление."""

    async def test_full_lifecycle(self, client, admin_headers, created_category):
        """Полный жизненный цикл товара через API."""
        # 1. Create
        create_resp = await client.post(
            "/api/v1/products",
            json={
                "title": "Lifecycle Product",
                "price": 50000,
                "category_id": created_category["id"],
                "stock": 5,
            },
            headers=admin_headers,
        )
        assert create_resp.status_code == 201
        product_id = create_resp.json()["id"]

        # 2. Read
        get_resp = await client.get(f"/api/v1/products/{product_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Lifecycle product"

        # 3. Update
        update_resp = await client.patch(
            f"/api/v1/products/{product_id}",
            json={"price": 45000, "stock": 3},
            headers=admin_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["price"] == 45000
        assert update_resp.json()["stock"] == 3

        # 4. Verify update
        verify_resp = await client.get(f"/api/v1/products/{product_id}")
        assert verify_resp.json()["price"] == 45000

        # 5. Delete
        delete_resp = await client.delete(
            f"/api/v1/products/{product_id}",
            headers=admin_headers,
        )
        assert delete_resp.status_code == 204

        # 6. Verify deletion
        gone_resp = await client.get(f"/api/v1/products/{product_id}")
        assert gone_resp.status_code == 404
