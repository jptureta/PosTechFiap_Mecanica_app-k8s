import httpx
from fastapi.testclient import TestClient

from app.api.v2 import router as gateway
from app.main import app


def test_order_request_is_forwarded_with_bearer_token(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(202, json={"id": "order-1"})

    monkeypatch.setattr(gateway.httpx, "request", fake_request)
    response = TestClient(app).post(
        "/api/v2/orders",
        headers={"Authorization": "Bearer signed-token"},
        json={"customer_id": "1", "vehicle_id": "2", "items": []},
    )

    assert response.status_code == 202
    assert captured["url"].endswith("/orders")
    assert captured["headers"]["authorization"] == "Bearer signed-token"


def test_downstream_failure_returns_service_unavailable(monkeypatch):
    def fail_request(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(gateway.httpx, "request", fail_request)
    response = TestClient(app).get(
        "/api/v2/orders/order-1",
        headers={"Authorization": "Bearer signed-token"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "downstream service unavailable"
