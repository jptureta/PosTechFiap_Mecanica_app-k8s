from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import Actor, get_actor
from app import main


def client_for_test(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    main.INTERNAL_TOKEN = "test-internal"

    def override_db():
        with factory() as session:
            yield session

    main.app.dependency_overrides[main.get_db] = override_db
    main.app.dependency_overrides[get_actor] = lambda: Actor(is_admin=True, customer_id=None)
    monkeypatch.setattr(
        main.httpx,
        "post",
        lambda *args, **kwargs: type(
            "Response",
            (),
            {
                "raise_for_status": lambda self: None,
                "json": lambda self: {"id": "quote-test"},
            },
        )(),
    )
    monkeypatch.setattr(
        main.httpx,
        "get",
        lambda url, **kwargs: type(
            "Response",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "name": "Inspection" if url.endswith("inspection") else "Oil",
                    "unit_price": "5.00" if url.endswith("inspection") else "10.00",
                    "active": True,
                },
                "raise_for_status": lambda self: None,
            },
        )(),
    )
    return TestClient(main.app), engine


def test_create_order_and_read_history(monkeypatch):
    client, engine = client_for_test(monkeypatch)
    try:
        response = client.post(
            "/orders",
            json={
                "customer_id": "customer-1",
                "vehicle_id": "vehicle-1",
                "items": [{"sku": "oil-1", "quantity": 1}],
            },
        )
        assert response.status_code == 202
        order_id = response.json()["id"]
        assert response.json()["saga_state"] == "QUOTE_CREATED"
        assert response.json()["quote_id"] == "quote-test"
        history = client.get(f"/orders/{order_id}/history")
        assert history.status_code == 200
        assert history.json()[0]["new_status"] == "QUOTE_PENDING"
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_missing_order_returns_404(monkeypatch):
    client, engine = client_for_test(monkeypatch)
    try:
        assert client.get("/orders/not-found").status_code == 404
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_payment_confirmation_reserves_parts_and_advances_status(monkeypatch):
    client, engine = client_for_test(monkeypatch)
    main.INTERNAL_TOKEN = "test-internal"
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return type(
            "Response",
            (),
            {
                "raise_for_status": lambda self: None,
                "json": lambda self: {"id": "quote-test"},
            },
        )()

    monkeypatch.setattr(main.httpx, "post", post)
    try:
        order = client.post(
            "/orders",
            json={
                "customer_id": "customer-1",
                "vehicle_id": "vehicle-1",
                "items": [
                    {"kind": "PART", "sku": "oil-1", "quantity": 1},
                    {"kind": "SERVICE", "sku": "inspection", "quantity": 1},
                ],
            },
        ).json()
        response = client.post(
            "/internal/payments/confirmed",
            json={"order_id": order["id"], "payment_id": "payment-1"},
            headers={"X-Internal-Token": "test-internal"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "READY_FOR_SERVICE"
        inventory_call = next(call for call in calls if call[0].endswith("/reservations"))
        assert inventory_call[1]["headers"]["X-Internal-Token"] == "test-internal"
        assert inventory_call[1]["json"]["items"] == [{"sku": "oil-1", "quantity": 1}]
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_inventory_failure_requests_payment_compensation(monkeypatch):
    client, engine = client_for_test(monkeypatch)
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/reservations"):
            request = main.httpx.Request("POST", url)
            response = main.httpx.Response(409)
            raise main.httpx.HTTPStatusError("stock unavailable", request=request, response=response)
        return type(
            "Response",
            (),
            {
                "raise_for_status": lambda self: None,
                "json": lambda self: {"id": "quote-test"},
            },
        )()

    monkeypatch.setattr(main.httpx, "post", post)
    try:
        order = client.post(
            "/orders",
            json={
                "customer_id": "customer-1",
                "vehicle_id": "vehicle-1",
                "items": [{"sku": "oil-1", "quantity": 1}],
            },
        ).json()
        response = client.post(
            "/internal/payments/confirmed",
            json={"order_id": order["id"], "payment_id": "payment-2"},
            headers={"X-Internal-Token": "test-internal"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"
        compensation_call = next(call for call in calls if "/compensate" in call[0])
        assert compensation_call[1]["headers"]["X-Internal-Token"] == "test-internal"

        outbox = client.get(f"/orders/{order['id']}/outbox")
        assert outbox.status_code == 200
        event_types = [m["event_type"] for m in outbox.json()]
        assert "INVENTORY_RESERVATION_FAILED" in event_types
        assert "COMPENSATION_COMPLETED" in event_types
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_retry_compensation_when_first_compensation_fails(monkeypatch):
    client, engine = client_for_test(monkeypatch)
    calls = []
    fail_compensation = True

    def post(url, **kwargs):
        nonlocal fail_compensation
        calls.append((url, kwargs))
        if url.endswith("/reservations"):
            request = main.httpx.Request("POST", url)
            response = main.httpx.Response(409)
            raise main.httpx.HTTPStatusError("stock unavailable", request=request, response=response)
        if "/compensate" in url and fail_compensation:
            request = main.httpx.Request("POST", url)
            response = main.httpx.Response(503)
            raise main.httpx.HTTPStatusError("billing temporarily down", request=request, response=response)
        return type(
            "Response",
            (),
            {
                "raise_for_status": lambda self: None,
                "json": lambda self: {"id": "quote-test"},
            },
        )()

    monkeypatch.setattr(main.httpx, "post", post)
    try:
        order = client.post(
            "/orders",
            json={
                "customer_id": "customer-1",
                "vehicle_id": "vehicle-1",
                "items": [{"sku": "oil-1", "quantity": 1}],
            },
        ).json()
        # Primeiro confirmação falha no compensar -> 503
        response = client.post(
            "/internal/payments/confirmed",
            json={"order_id": order["id"], "payment_id": "payment-retry"},
            headers={"X-Internal-Token": "test-internal"},
        )
        assert response.status_code == 503
        check_order = client.get(f"/orders/{order['id']}").json()
        assert check_order["saga_state"] == "COMPENSATION_PENDING"

        # Agora o Billing voltou; executamos retry-compensation
        fail_compensation = False
        retry_res = client.post(f"/orders/{order['id']}/retry-compensation")
        assert retry_res.status_code == 202
        assert retry_res.json()["saga_state"] == "COMPENSATED"
        assert retry_res.json()["status"] == "CANCELLED"
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
