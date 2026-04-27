"""Интеграционные тесты для Internal API /internal/products.

Тесты проверяют межсервисные эндпоинты: получение товара,
резервирование, подтверждение и отмену резерва.
"""

import uuid


# ── Получение товара (internal) ──────────────────────────────────────────────


class TestGetProductInternal:
    """GET /internal/products/{product_id}."""

    async def test_get_200(self, client, created_product):
        """Успешное получение товара через internal API — 200."""
        product_id = created_product["id"]

        response = await client.get(f"/internal/products/{product_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == product_id
        assert body["title"] == created_product["title"]
        assert body["price"] == created_product["price"]

    async def test_get_not_found_404(self, client):
        """Несуществующий ID — 404."""
        response = await client.get("/internal/products/99999")

        assert response.status_code == 404
        assert response.json()["error_type"] == "not_found"

    async def test_no_auth_required(self, client, created_product):
        """Internal API не требует авторизации (X-User-Role)."""
        response = await client.get(
            f"/internal/products/{created_product['id']}",
        )

        assert response.status_code == 200


# ── Резервирование товаров ───────────────────────────────────────────────────


class TestReserveProducts:
    """POST /internal/products/reserve."""

    async def test_reserve_single_product(
        self, client, admin_headers, created_category
    ):
        """Резервирование одного товара — stock уменьшается."""
        # Создаём товар со stock=10
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "Reserve test",
                    "price": 5000,
                    "category_id": created_category["id"],
                    "stock": 10,
                },
                headers=admin_headers,
            )
        ).json()

        order_id = str(uuid.uuid4())
        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": order_id,
                "items": [
                    {"product_id": product["id"], "quantity": 3},
                ],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["product_id"] == product["id"]
        assert body[0]["name"] == "Reserve test"
        assert body[0]["price"] == 5000
        assert body[0]["quantity"] == 3

        # Проверяем stock через API
        get_resp = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp.json()["stock"] == 7  # 10 - 3

    async def test_reserve_multiple_products(
        self, client, admin_headers, created_category
    ):
        """Резервирование нескольких товаров в одном запросе."""
        products = []
        for i in range(3):
            resp = await client.post(
                "/api/v1/products",
                json={
                    "title": f"Multi reserve {i}",
                    "price": 1000 * (i + 1),
                    "category_id": created_category["id"],
                    "stock": 20,
                },
                headers=admin_headers,
            )
            products.append(resp.json())

        order_id = str(uuid.uuid4())
        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": order_id,
                "items": [
                    {"product_id": products[0]["id"], "quantity": 5},
                    {"product_id": products[1]["id"], "quantity": 2},
                    {"product_id": products[2]["id"], "quantity": 10},
                ],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 3

        # Проверяем остатки
        for p, expected_stock in zip(products, [15, 18, 10]):
            get_resp = await client.get(f"/api/v1/products/{p['id']}")
            assert get_resp.json()["stock"] == expected_stock

    async def test_reserve_insufficient_stock_400(
        self,
        client,
        admin_headers,
        created_category,
    ):
        """Недостаточно stock — 400 bad_request."""
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "Low stock",
                    "price": 1000,
                    "category_id": created_category["id"],
                    "stock": 2,
                },
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": product["id"], "quantity": 5},
                ],
            },
        )

        assert response.status_code == 400
        assert response.json()["error_type"] == "bad_request"

        # Stock не изменился
        get_resp = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp.json()["stock"] == 2

    async def test_reserve_product_not_found_400(self, client):
        """Резервирование несуществующего товара — 400."""
        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": 99999, "quantity": 1},
                ],
            },
        )

        assert response.status_code == 400
        assert response.json()["error_type"] == "bad_request"

    async def test_reserve_depletes_stock(
        self, client, admin_headers, created_category
    ):
        """Резервирование всего stock — stock становится 0."""
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "Deplete stock",
                    "price": 1000,
                    "category_id": created_category["id"],
                    "stock": 5,
                },
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": product["id"], "quantity": 5},
                ],
            },
        )

        assert response.status_code == 200

        get_resp = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp.json()["stock"] == 0

    async def test_reserve_empty_items_422(self, client):
        """Пустой список items — 422."""
        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [],
            },
        )

        assert response.status_code == 422

    async def test_reserve_invalid_quantity_422(self, client):
        """quantity <= 0 — 422."""
        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": 1, "quantity": 0},
                ],
            },
        )

        assert response.status_code == 422

    async def test_reserve_with_images(self, client, admin_headers, created_category):
        """Резервирование возвращает image_url из первого изображения."""
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "With image",
                    "price": 3000,
                    "category_id": created_category["id"],
                    "stock": 10,
                    "images": [
                        "https://example.com/photo1.jpg",
                        "https://example.com/photo2.jpg",
                    ],
                },
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": product["id"], "quantity": 1},
                ],
            },
        )

        assert response.status_code == 200
        assert response.json()[0]["image_url"] == "https://example.com/photo1.jpg"

    async def test_reserve_without_images(
        self, client, admin_headers, created_category
    ):
        """Резервирование товара без изображений — image_url пустая строка."""
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "No image",
                    "price": 2000,
                    "category_id": created_category["id"],
                    "stock": 5,
                },
                headers=admin_headers,
            )
        ).json()

        response = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [
                    {"product_id": product["id"], "quantity": 1},
                ],
            },
        )

        assert response.status_code == 200
        assert response.json()[0]["image_url"] == ""


# ── Отмена резерва ───────────────────────────────────────────────────────────


class TestCancelReserve:
    """POST /internal/products/cancel-reserve."""

    async def test_cancel_restores_stock(self, client, admin_headers, created_category):
        """Отмена резерва восстанавливает stock."""
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "Cancel test",
                    "price": 1000,
                    "category_id": created_category["id"],
                    "stock": 10,
                },
                headers=admin_headers,
            )
        ).json()

        order_id = str(uuid.uuid4())

        # Резервируем 4 штуки
        await client.post(
            "/internal/products/reserve",
            json={
                "order_id": order_id,
                "items": [
                    {"product_id": product["id"], "quantity": 4},
                ],
            },
        )

        # Stock = 6
        get_resp = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp.json()["stock"] == 6

        # Отменяем резерв
        cancel_resp = await client.post(
            "/internal/products/cancel-reserve",
            json={
                "order_id": order_id,
                "items": [
                    {"product_id": product["id"], "quantity": 4},
                ],
            },
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "ok"

        # Stock вернулся к 10
        get_resp2 = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp2.json()["stock"] == 10

    async def test_cancel_idempotent(self, client, admin_headers, created_category):
        """Повторная отмена того же order_id — идемпотентная (не ошибка)."""
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "Idempotent cancel",
                    "price": 1000,
                    "category_id": created_category["id"],
                    "stock": 10,
                },
                headers=admin_headers,
            )
        ).json()

        order_id = str(uuid.uuid4())

        # Резервируем
        await client.post(
            "/internal/products/reserve",
            json={
                "order_id": order_id,
                "items": [{"product_id": product["id"], "quantity": 2}],
            },
        )

        cancel_body = {
            "order_id": order_id,
            "items": [{"product_id": product["id"], "quantity": 2}],
        }

        # Первая отмена
        resp1 = await client.post("/internal/products/cancel-reserve", json=cancel_body)
        assert resp1.status_code == 200

        # Вторая отмена того же order — ОК (идемпотентность)
        resp2 = await client.post("/internal/products/cancel-reserve", json=cancel_body)
        assert resp2.status_code == 200

        # Stock вернулся к 10
        get_resp = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp.json()["stock"] == 10

    async def test_cancel_nonexistent_order(self, client):
        """Отмена несуществующего заказа — идемпотентный ответ 200."""
        response = await client.post(
            "/internal/products/cancel-reserve",
            json={
                "order_id": str(uuid.uuid4()),
                "items": [{"product_id": 1, "quantity": 1}],
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ── Полный цикл резервирования ───────────────────────────────────────────────


class TestReservationLifecycle:
    """E2E тест: создание товара → резерв → проверка stock → отмена → проверка."""

    async def test_reserve_and_cancel_lifecycle(
        self,
        client,
        admin_headers,
        created_category,
    ):
        """Полный цикл: create → reserve → verify → cancel → verify."""
        # 1. Создаём товар
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "Lifecycle reserve",
                    "price": 9999,
                    "category_id": created_category["id"],
                    "stock": 20,
                    "images": ["https://img.example.com/1.jpg"],
                },
                headers=admin_headers,
            )
        ).json()

        order_id = str(uuid.uuid4())

        # 2. Резервируем 8 штук
        reserve_resp = await client.post(
            "/internal/products/reserve",
            json={
                "order_id": order_id,
                "items": [
                    {"product_id": product["id"], "quantity": 8},
                ],
            },
        )
        assert reserve_resp.status_code == 200
        reserved = reserve_resp.json()
        assert reserved[0]["product_id"] == product["id"]
        assert reserved[0]["name"] == "Lifecycle reserve"
        assert reserved[0]["price"] == 9999
        assert reserved[0]["quantity"] == 8
        assert reserved[0]["image_url"] == "https://img.example.com/1.jpg"

        # 3. Проверяем stock через public API
        get1 = await client.get(f"/api/v1/products/{product['id']}")
        assert get1.json()["stock"] == 12  # 20 - 8

        # 4. Проверяем stock через internal API
        get_internal = await client.get(f"/internal/products/{product['id']}")
        assert get_internal.json()["stock"] == 12

        # 5. Отменяем резерв
        cancel_resp = await client.post(
            "/internal/products/cancel-reserve",
            json={
                "order_id": order_id,
                "items": [
                    {"product_id": product["id"], "quantity": 8},
                ],
            },
        )
        assert cancel_resp.status_code == 200

        # 6. Проверяем что stock восстановился
        get2 = await client.get(f"/api/v1/products/{product['id']}")
        assert get2.json()["stock"] == 20

    async def test_multiple_reserves_same_product(
        self,
        client,
        admin_headers,
        created_category,
    ):
        """Несколько резервов на один товар — stock уменьшается последовательно."""
        product = (
            await client.post(
                "/api/v1/products",
                json={
                    "title": "Multi reservations",
                    "price": 500,
                    "category_id": created_category["id"],
                    "stock": 30,
                },
                headers=admin_headers,
            )
        ).json()

        order_ids = [str(uuid.uuid4()) for _ in range(3)]

        # Резервируем 3 заказа: 5, 10, 8
        for order_id, qty in zip(order_ids, [5, 10, 8]):
            resp = await client.post(
                "/internal/products/reserve",
                json={
                    "order_id": order_id,
                    "items": [
                        {"product_id": product["id"], "quantity": qty},
                    ],
                },
            )
            assert resp.status_code == 200

        # Stock = 7
        get_resp = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp.json()["stock"] == 7

        # Отменяем второй заказ (10 штук)
        await client.post(
            "/internal/products/cancel-reserve",
            json={
                "order_id": order_ids[1],
                "items": [
                    {"product_id": product["id"], "quantity": 10},
                ],
            },
        )

        # Stock = 17
        get_resp2 = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp2.json()["stock"] == 17
