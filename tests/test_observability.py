import json

from app.observability import build_json_log_record, generate_request_id


def test_generate_request_id_returns_unique_value():
    request_id = generate_request_id()

    assert isinstance(request_id, str)
    assert len(request_id) > 10


def test_build_json_log_record_includes_context_fields():
    record = build_json_log_record(
        message="request processed",
        level="INFO",
        request_id="req-123",
        route="/api/v1/ordens-servico",
        status_code=200,
        latency_ms=42.5,
    )

    payload = json.loads(record)
    assert payload["message"] == "request processed"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-123"
    assert payload["route"] == "/api/v1/ordens-servico"
    assert payload["status_code"] == 200
    assert payload["latency_ms"] == 42.5
