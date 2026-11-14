from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.auth import Actor, get_actor


def client_for_test(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "_memory_queue", [])
    monkeypatch.setattr(main, "redis_client", None)
    monkeypatch.setattr(main, "INTERNAL_TOKEN", "test-internal")

    def override_db():
        with factory() as session:
            yield session

    main.app.dependency_overrides[main.get_db] = override_db
    main.app.dependency_overrides[get_actor] = lambda: Actor(is_admin=True, customer_id=None)
    monkeypatch.setattr(main.httpx, "patch", lambda *args, **kwargs: type("Response", (), {"raise_for_status": lambda self: None})())
    return TestClient(main.app), engine


def test_queue_status_and_completion(monkeypatch):
    client, engine = client_for_test(monkeypatch)
    try:
        created = client.post("/executions", json={"order_id": "order-1", "priority": 5})
        assert created.status_code == 201
        execution = created.json()
        assert execution["status"] == "QUEUED"
        next_response = client.post("/executions/next")
        assert next_response.status_code == 200, next_response.text
        assert next_response.json()["execution"]["order_id"] == "order-1"
        assert client.patch(f"/executions/{execution['id']}/status", json={"status": "DIAGNOSING", "note": "Início"}).json()["status"] == "DIAGNOSING"
        assert client.patch(f"/executions/{execution['id']}/status", json={"status": "REPAIRING", "note": "Troca"}).json()["status"] == "REPAIRING"
        completed = client.post(f"/executions/{execution['id']}/complete", json={"note": "Finalizado"})
        assert completed.status_code == 200
        assert completed.json()["status"] == "COMPLETED"
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_execution_lookup_validation_and_notification_retry(monkeypatch):
    client, engine = client_for_test(monkeypatch)
    try:
        assert client.get("/health").status_code == 200
        assert client.get("/health/live").status_code == 200
        assert client.post("/executions", json={"order_id": "bad", "priority": 11}).status_code == 422

        created = client.post("/executions", json={"order_id": "order-retry", "priority": 3})
        assert created.status_code == 201
        execution = created.json()
        execution_id = execution["id"]
        assert client.post("/executions", json={"order_id": "order-retry"}).status_code == 409
        assert client.get("/executions").json()[0]["id"] == execution_id
        assert client.get(f"/executions/{execution_id}").status_code == 200
        assert client.get("/executions/missing").status_code == 404
        assert client.patch(
            f"/executions/{execution_id}/status",
            json={"status": "REPAIRING", "note": "Skip diagnosis"},
        ).status_code == 409
        assert client.post(f"/executions/{execution_id}/complete", json={"note": "Too early"}).status_code == 409

        notification_urls = []

        def fail_notification(url, **kwargs):
            notification_urls.append(url)
            request = main.httpx.Request("PATCH", url)
            response = main.httpx.Response(503)
            raise main.httpx.HTTPStatusError("OS unavailable", request=request, response=response)

        monkeypatch.setattr(main.httpx, "patch", fail_notification)
        failed = client.patch(
            f"/executions/{execution_id}/status",
            json={"status": "DIAGNOSING", "note": "First attempt"},
        )
        assert failed.status_code == 503
        assert notification_urls == [f"{main.OS_SERVICE_URL}/internal/orders/order-retry/status"]

        monkeypatch.setattr(
            main.httpx,
            "patch",
            lambda *args, **kwargs: type("Response", (), {"raise_for_status": lambda self: None})(),
        )
        retried = client.patch(
            f"/executions/{execution_id}/status",
            json={"status": "DIAGNOSING", "note": "Retry"},
        )
        assert retried.status_code == 200
        assert retried.json()["status"] == "DIAGNOSING"
        assert len(retried.json()["history"]) == 2
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
