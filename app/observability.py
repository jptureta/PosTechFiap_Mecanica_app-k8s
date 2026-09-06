import json
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

try:
    from datadog import statsd as datadog_statsd
except Exception:  # pragma: no cover - opcional em ambientes sem Datadog
    datadog_statsd = None


START_TIME = time.time()
REQUEST_METRICS = {
    "requests_total": 0,
    "requests_by_route": defaultdict(int),
    "requests_by_status": defaultdict(int),
    "orders_by_status": defaultdict(int),
    "orders_total": 0,
    "latency_ms": [],
    "status_duration_ms": defaultdict(list),
    "integration_failures": defaultdict(int),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def build_json_log_record(message: str, level: str = "INFO", **fields: Any) -> str:
    payload = {
        "timestamp": now_iso(),
        "level": str(level).upper(),
        "message": message,
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    return json.dumps(payload, separators=(",", ":"), default=str)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": now_iso(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "route",
            "status_code",
            "latency_ms",
            "client_ip",
            "order_id",
            "status",
            "integration",
            "error_type",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_json_logging() -> logging.Logger:
    logger = logging.getLogger("oficina")
    logger.setLevel(logging.INFO)
    if not any(isinstance(handler.formatter, JsonFormatter) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


logger = configure_json_logging()


def emit_datadog_metric(name: str, value: float = 1, tags: list[str] | None = None) -> None:
    if datadog_statsd is None:
        return
    try:
        datadog_statsd.increment(name, value=value, tags=tags or [])
    except Exception:
        pass


def record_http_request(method: str, route: str, status_code: int, latency_ms: float, request_id: str) -> None:
    REQUEST_METRICS["requests_total"] += 1
    REQUEST_METRICS["requests_by_route"][route] += 1
    REQUEST_METRICS["requests_by_status"][str(status_code)] += 1
    REQUEST_METRICS["latency_ms"].append(float(latency_ms))

    logger.info(
        "http_request",
        extra={
            "request_id": request_id,
            "method": method,
            "route": route,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 2),
        },
    )

    emit_datadog_metric(
        "oficina.api.requests_total",
        value=1,
        tags=[f"method:{method}", f"route:{route}", f"status:{status_code}"],
    )
    emit_datadog_metric(
        "oficina.api.request_latency_ms",
        value=latency_ms,
        tags=[f"method:{method}", f"route:{route}"],
    )


def record_order_status_transition(status: str, order_id: int | None = None, duration_ms: float | None = None) -> None:
    REQUEST_METRICS["orders_total"] += 1
    REQUEST_METRICS["orders_by_status"][status] += 1
    if duration_ms is not None:
        REQUEST_METRICS["status_duration_ms"][status].append(float(duration_ms))

    logger.info(
        "order_status_transition",
        extra={
            "order_id": order_id,
            "status": status,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
        },
    )

    emit_datadog_metric("oficina.api.orders_total", value=1, tags=[f"status:{status}"])
    if duration_ms is not None:
        emit_datadog_metric("oficina.api.order_duration_ms", value=duration_ms, tags=[f"status:{status}"])


def record_integration_failure(integration: str, error: str) -> None:
    REQUEST_METRICS["integration_failures"][integration] += 1
    logger.error(
        "integration_failure",
        extra={"integration": integration, "error_type": error},
    )
    emit_datadog_metric("oficina.api.integration_failures", value=1, tags=[f"integration:{integration}"])


def get_metrics_snapshot() -> dict[str, Any]:
    latency_values = REQUEST_METRICS["latency_ms"]
    status_durations = {}
    for status, values in REQUEST_METRICS["status_duration_ms"].items():
        if values:
            status_durations[status] = round(sum(values) / len(values), 2)

    return {
        "service": "oficina-mecanica-api",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "requests_total": REQUEST_METRICS["requests_total"],
        "requests_by_route": dict(REQUEST_METRICS["requests_by_route"]),
        "requests_by_status": dict(REQUEST_METRICS["requests_by_status"]),
        "orders_total": REQUEST_METRICS["orders_total"],
        "orders_by_status": dict(REQUEST_METRICS["orders_by_status"]),
        "latency_ms": {
            "avg": round(sum(latency_values) / len(latency_values), 2) if latency_values else 0,
            "p95": round(sorted(latency_values)[max(0, min(len(latency_values) - 1, int(len(latency_values) * 0.95)))], 2) if latency_values else 0,
        },
        "status_duration_ms": status_durations,
        "integration_failures": dict(REQUEST_METRICS["integration_failures"]),
    }
