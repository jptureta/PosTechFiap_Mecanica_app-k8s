import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from starlette.responses import Response

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["Microservices"])
settings = get_settings()


def forward_request(
    request: Request,
    service_url: str,
    path: str,
    method: str,
    payload: dict[str, Any] | None = None,
) -> Response:
    headers = {}
    for header_name in ("authorization", "x-provider-token"):
        value = request.headers.get(header_name)
        if value:
            headers[header_name] = value
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers["x-request-id"] = request_id
    try:
        upstream = httpx.request(
            method,
            f"{service_url.rstrip('/')}{path}",
            headers=headers,
            json=payload,
            timeout=10,
        )
    except httpx.HTTPError as exc:
        logger.exception("microservice request failed: %s %s", method, path)
        raise HTTPException(status_code=503, detail="downstream service unavailable") from exc
    response_headers = {}
    for header_name in ("content-type", "x-request-id"):
        value = upstream.headers.get(header_name)
        if value:
            response_headers[header_name] = value
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@router.post("/orders")
def create_order(request: Request, payload: dict[str, Any]):
    return forward_request(request, settings.OS_SERVICE_URL, "/orders", "POST", payload)


@router.post("/executions")
def create_execution(request: Request, payload: dict[str, Any]):
    return forward_request(request, settings.EXECUTION_SERVICE_URL, "/executions", "POST", payload)


@router.get("/executions")
def list_executions(request: Request):
    return forward_request(request, settings.EXECUTION_SERVICE_URL, "/executions", "GET")


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, request: Request):
    return forward_request(request, settings.EXECUTION_SERVICE_URL, f"/executions/{execution_id}", "GET")


@router.post("/executions/next")
def claim_next_execution(request: Request):
    return forward_request(request, settings.EXECUTION_SERVICE_URL, "/executions/next", "POST")


@router.patch("/executions/{execution_id}/status")
def update_execution_status(execution_id: str, request: Request, payload: dict[str, Any]):
    return forward_request(request, settings.EXECUTION_SERVICE_URL, f"/executions/{execution_id}/status", "PATCH", payload)


@router.post("/executions/{execution_id}/complete")
def complete_execution(execution_id: str, request: Request, payload: dict[str, Any]):
    return forward_request(request, settings.EXECUTION_SERVICE_URL, f"/executions/{execution_id}/complete", "POST", payload)


@router.post("/orders/{order_id}/retry-quote")
def retry_order_quote(order_id: str, request: Request):
    return forward_request(
        request,
        settings.OS_SERVICE_URL,
        f"/orders/{order_id}/retry-quote",
        "POST",
    )


@router.post("/orders/{order_id}/retry-compensation")
def retry_order_compensation(order_id: str, request: Request):
    return forward_request(
        request,
        settings.OS_SERVICE_URL,
        f"/orders/{order_id}/retry-compensation",
        "POST",
    )


@router.get("/orders/{order_id}/outbox")
def get_order_outbox(order_id: str, request: Request):
    return forward_request(
        request,
        settings.OS_SERVICE_URL,
        f"/orders/{order_id}/outbox",
        "GET",
    )


@router.get("/orders/{order_id}")
def get_order(order_id: str, request: Request):
    return forward_request(request, settings.OS_SERVICE_URL, f"/orders/{order_id}", "GET")


@router.get("/orders/{order_id}/history")
def get_order_history(order_id: str, request: Request):
    return forward_request(request, settings.OS_SERVICE_URL, f"/orders/{order_id}/history", "GET")


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: str, request: Request, payload: dict[str, Any]):
    return forward_request(
        request,
        settings.OS_SERVICE_URL,
        f"/orders/{order_id}/status",
        "PATCH",
        payload,
    )


@router.get("/quotes/{quote_id}")
def get_quote(quote_id: str, request: Request):
    return forward_request(request, settings.BILLING_SERVICE_URL, f"/quotes/{quote_id}", "GET")


@router.post("/quotes/{quote_id}/send")
def send_quote(quote_id: str, request: Request):
    return forward_request(request, settings.BILLING_SERVICE_URL, f"/quotes/{quote_id}/send", "POST")


@router.post("/quotes/{quote_id}/approval")
def approve_quote(quote_id: str, request: Request):
    return forward_request(
        request,
        settings.BILLING_SERVICE_URL,
        f"/quotes/{quote_id}/approval",
        "POST",
    )


@router.post("/quotes/{quote_id}/payments")
def register_payment(quote_id: str, request: Request):
    return forward_request(
        request,
        settings.BILLING_SERVICE_URL,
        f"/quotes/{quote_id}/payments",
        "POST",
    )


@router.post("/payments/mercado-pago/webhook")
def mercado_pago_webhook(request: Request, payload: dict[str, Any]):
    return forward_request(
        request,
        settings.BILLING_SERVICE_URL,
        "/payments/mercado-pago/webhook",
        "POST",
        payload,
    )


@router.post("/payments/{payment_id}/verify")
def verify_payment(payment_id: str, request: Request, payload: dict[str, Any]):
    return forward_request(
        request,
        settings.BILLING_SERVICE_URL,
        f"/payments/{payment_id}/verify",
        "POST",
        payload,
    )


@router.get("/parts/{sku}")
def get_part(sku: str, request: Request):
    return forward_request(request, settings.INVENTORY_SERVICE_URL, f"/parts/{sku}", "GET")


@router.put("/parts/{sku}")
def update_part(sku: str, request: Request, payload: dict[str, Any]):
    return forward_request(request, settings.INVENTORY_SERVICE_URL, f"/parts/{sku}", "PUT", payload)


@router.put("/services/{sku}")
def update_service(sku: str, request: Request, payload: dict[str, Any]):
    return forward_request(request, settings.INVENTORY_SERVICE_URL, f"/services/{sku}", "PUT", payload)
