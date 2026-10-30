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
    main._memory_queue.clear()
    main.redis_client = None
    main.INTERNAL_TOKEN = "test-internal"
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
