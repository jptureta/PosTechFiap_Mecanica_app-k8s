import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.auth import Actor, get_actor

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./os-service.db")
BILLING_URL = os.getenv("BILLING_URL", "http://billing-service:8000").rstrip("/")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory-service:8000").rstrip("/")
INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(100), nullable=False)
    items: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="QUOTE_PENDING")
    saga_state: Mapped[str] = mapped_column(String(40), nullable=False, default="QUOTE_PENDING")
    quote_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    payment_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    history: Mapped[list["OrderHistory"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderHistory(Base):
    __tablename__ = "order_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(String(300), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    order: Mapped[Order] = relationship(back_populates="history")


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    aggregate_type: Mapped[str] = mapped_column(String(50), default="ORDER")
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrderItem(BaseModel):
    kind: Literal["PART", "SERVICE"] = "PART"
    sku: str
    quantity: int = Field(gt=0)


class CreateOrder(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100)
    vehicle_id: str = Field(min_length=1, max_length=100)
    items: list[OrderItem] = Field(min_length=1)


class StatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=40)
    note: str = Field(min_length=1, max_length=300)


class PaymentConfirmed(BaseModel):
    order_id: str
    payment_id: str


def get_db():
    with SessionLocal() as session:
        yield session


def require_internal_token(x_internal_token: Annotated[str | None, Header()] = None) -> None:
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal service token")


def record_status(db: Session, order: Order, new_status: str, note: str) -> None:
    if order.status == new_status:
        return
    order.history.append(
        OrderHistory(order_id=order.id, previous_status=order.status, new_status=new_status, note=note)
    )
    order.status = new_status


def record_outbox(
    db: Session,
    aggregate_id: str,
    event_type: str,
    payload: dict,
    status: str = "PENDING",
    error_message: str | None = None,
) -> OutboxMessage:
    msg = OutboxMessage(
        aggregate_type="ORDER",
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
        status=status,
        error_message=error_message,
        processed_at=datetime.now(timezone.utc) if status == "PROCESSED" else None,
    )
    db.add(msg)
    return msg


def ensure_order_access(order: Order, actor: Actor) -> None:
    if not actor.is_admin and actor.customer_id != order.customer_id:
        raise HTTPException(status_code=403, detail="order does not belong to the authenticated customer")


def order_document(order: Order) -> dict:
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "vehicle_id": order.vehicle_id,
        "items": order.items,
        "status": order.status,
        "saga_state": order.saga_state,
        "quote_id": order.quote_id,
        "created_at": order.created_at,
        "history": [
            {
                "previous_status": item.previous_status,
                "new_status": item.new_status,
                "note": item.note,
                "changed_at": item.changed_at,
            }
            for item in order.history
        ],
    }


app = FastAPI(title="Ordem de Serviço", version="1.0.0")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("database readiness check failed")
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "service": "os-service"}


@app.get("/health/live")
def liveness():
    return {"status": "ok", "service": "os-service"}


@app.post("/orders", status_code=status.HTTP_202_ACCEPTED)
def create_order(
    payload: CreateOrder,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    if not actor.is_admin and actor.customer_id != payload.customer_id:
        raise HTTPException(status_code=403, detail="customer cannot open an order for another customer")
    items = []
    for requested_item in payload.items:
        catalog_path = "parts" if requested_item.kind == "PART" else "services"
        try:
            catalog_response = httpx.get(
                f"{INVENTORY_URL}/internal/{catalog_path}/{requested_item.sku}",
                headers={"X-Internal-Token": INTERNAL_TOKEN},
                timeout=5,
            )
            if catalog_response.status_code == 404:
                raise HTTPException(status_code=422, detail=f"unknown catalog item: {requested_item.sku}")
            catalog_response.raise_for_status()
            catalog_item = catalog_response.json()
        except httpx.HTTPError as exc:
            logger.exception("catalog lookup failed for item %s", requested_item.sku)
            raise HTTPException(status_code=503, detail="catalog unavailable; no order was created") from exc
        if not catalog_item.get("active", True):
            raise HTTPException(status_code=422, detail=f"inactive catalog item: {requested_item.sku}")
        items.append(
            {
                "kind": requested_item.kind,
                "sku": requested_item.sku,
                "name": catalog_item["name"],
                "quantity": requested_item.quantity,
                "unit_price": str(catalog_item["unit_price"]),
            }
        )
    order = Order(
        customer_id=payload.customer_id,
        vehicle_id=payload.vehicle_id,
        items=items,
    )
    order.history.append(OrderHistory(new_status="QUOTE_PENDING", note="OS aberta"))
    db.add(order)
    db.commit()
    db.refresh(order)
    request = {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "items": order.items,
    }
    try:
        response = httpx.post(
            f"{BILLING_URL}/quotes",
            json=request,
            headers={"X-Internal-Token": INTERNAL_TOKEN},
            timeout=5,
        )
        response.raise_for_status()
        quote_id = response.json().get("id")
        if not isinstance(quote_id, str) or not quote_id:
            raise ValueError("billing response did not include a quote id")
        order.quote_id = quote_id
        order.saga_state = "QUOTE_CREATED"
        record_outbox(db, order.id, "QUOTE_REQUESTED", request, status="PROCESSED")
        db.commit()
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("billing quote creation failed for order %s", order.id)
        order.saga_state = "QUOTE_PENDING"
        record_outbox(db, order.id, "QUOTE_REQUESTED", request, status="FAILED", error_message=str(exc))
        db.commit()
    return order_document(order)


@app.post("/orders/{order_id}/retry-quote", status_code=status.HTTP_202_ACCEPTED)
def retry_quote(
    order_id: str,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="only an administrator can retry the saga")
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.saga_state == "QUOTE_CREATED":
        return order_document(order)
    try:
        response = httpx.post(
            f"{BILLING_URL}/quotes",
            json={"order_id": order.id, "customer_id": order.customer_id, "items": order.items},
            headers={"X-Internal-Token": INTERNAL_TOKEN},
            timeout=5,
        )
        response.raise_for_status()
        quote_id = response.json().get("id")
        if not isinstance(quote_id, str) or not quote_id:
            raise ValueError("billing response did not include a quote id")
    except httpx.HTTPError as exc:
        logger.exception("billing quote retry failed for order %s", order.id)
        raise HTTPException(status_code=503, detail="quote remains pending; retry later") from exc
    order.quote_id = quote_id
    order.saga_state = "QUOTE_CREATED"
    db.commit()
    return order_document(order)


@app.get("/orders/{order_id}")
def get_order(order_id: str, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    ensure_order_access(order, actor)
    return order_document(order)


@app.get("/orders/{order_id}/history")
def get_history(order_id: str, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    ensure_order_access(order, actor)
    return order_document(order)["history"]


@app.patch("/orders/{order_id}/status")
def change_status(
    order_id: str,
    payload: StatusChange,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="only an administrator can change order status")
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    transitions = {
        "READY_FOR_SERVICE": "IN_DIAGNOSIS",
        "IN_DIAGNOSIS": "IN_PROGRESS",
        "IN_PROGRESS": "COMPLETED",
        "COMPLETED": "DELIVERED",
    }
    if transitions.get(order.status) != payload.status:
        raise HTTPException(status_code=409, detail=f"invalid transition from {order.status} to {payload.status}")
    record_status(db, order, payload.status, payload.note)
    db.commit()
    return order_document(order)


@app.patch("/internal/orders/{order_id}/status")
def internal_change_status(
    order_id: str,
    payload: StatusChange,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    allowed = {"IN_DIAGNOSIS", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
    if payload.status not in allowed:
        raise HTTPException(status_code=409, detail=f"unsupported execution status: {payload.status}")
    record_status(db, order, payload.status, payload.note)
    db.commit()
    return order_document(order)


@app.post("/internal/orders/{order_id}/quote-approved")
def quote_approved(
    order_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    order.saga_state = "AWAITING_PAYMENT"
    record_status(db, order, "AWAITING_PAYMENT", "Orçamento aprovado")
    db.commit()
    return {"order_id": order.id, "saga_state": order.saga_state}


@app.post("/internal/payments/confirmed")
def payment_confirmed(
    payload: PaymentConfirmed,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    order = db.get(Order, payload.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.payment_id == payload.payment_id and order.status == "READY_FOR_SERVICE":
        return {"order_id": order.id, "status": order.status}
    if order.payment_id not in (None, payload.payment_id):
        raise HTTPException(status_code=409, detail="order already has a different payment")
    order.payment_id = payload.payment_id
    try:
        response = httpx.post(
            f"{INVENTORY_URL}/reservations",
            json={
                "order_id": order.id,
                "items": [
                    {"sku": item["sku"], "quantity": item["quantity"]}
                    for item in order.items
                    if item["kind"] == "PART"
                ],
            },
            headers={"X-Internal-Token": INTERNAL_TOKEN},
            timeout=5,
        )
        response.raise_for_status()
    except httpx.HTTPError as inventory_error:
        logger.exception("inventory reservation failed for order %s", order.id)
        order.saga_state = "COMPENSATION_PENDING"
        record_status(db, order, "COMPENSATION_PENDING", "Reserva de estoque falhou após pagamento")
        record_outbox(
            db,
            order.id,
            "INVENTORY_RESERVATION_FAILED",
            {"payment_id": payload.payment_id},
            status="FAILED",
            error_message=str(inventory_error),
        )
        db.commit()
        try:
            compensation = httpx.post(
                f"{BILLING_URL}/internal/payments/{payload.payment_id}/compensate",
                headers={"X-Internal-Token": INTERNAL_TOKEN},
                timeout=5,
            )
            compensation.raise_for_status()
        except httpx.HTTPError as compensation_error:
            logger.exception("payment compensation could not be recorded for order %s", order.id)
            record_outbox(
                db,
                order.id,
                "COMPENSATION_FAILED",
                {"payment_id": payload.payment_id},
                status="FAILED",
                error_message=str(compensation_error),
            )
            db.commit()
            raise HTTPException(
                status_code=503,
                detail="inventory failed; payment compensation remains pending",
            ) from compensation_error
        order.saga_state = "COMPENSATED"
        record_status(db, order, "CANCELLED", "Compensação solicitada ao Billing; confirmar reembolso no provedor")
        record_outbox(
            db,
            order.id,
            "COMPENSATION_COMPLETED",
            {"payment_id": payload.payment_id, "action": "REFUND_REQUIRED"},
            status="PROCESSED",
        )
        db.commit()
        return {
            "order_id": order.id,
            "status": order.status,
            "saga_state": order.saga_state,
            "compensation": "refund reconciliation required",
        }
    order.saga_state = "COMPLETED"
    record_status(db, order, "READY_FOR_SERVICE", "Pagamento confirmado e estoque reservado")
    record_outbox(
        db,
        order.id,
        "SAGA_COMPLETED",
        {"payment_id": payload.payment_id},
        status="PROCESSED",
    )
    db.commit()
    return {"order_id": order.id, "status": order.status, "saga_state": order.saga_state}


@app.post("/orders/{order_id}/retry-compensation", status_code=status.HTTP_202_ACCEPTED)
def retry_compensation(
    order_id: str,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="only an administrator can retry compensation")
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.saga_state == "COMPENSATED":
        return order_document(order)
    if order.saga_state != "COMPENSATION_PENDING":
        raise HTTPException(status_code=409, detail=f"order is not awaiting compensation (saga_state={order.saga_state})")
    if not order.payment_id:
        raise HTTPException(status_code=422, detail="order has no payment to compensate")
    try:
        compensation = httpx.post(
            f"{BILLING_URL}/internal/payments/{order.payment_id}/compensate",
            headers={"X-Internal-Token": INTERNAL_TOKEN},
            timeout=5,
        )
        compensation.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("retry compensation failed for order %s", order.id)
        record_outbox(
            db,
            order.id,
            "COMPENSATION_RETRY_FAILED",
            {"payment_id": order.payment_id},
            status="FAILED",
            error_message=str(exc),
        )
        db.commit()
        raise HTTPException(status_code=503, detail="compensation remains pending; retry later") from exc
    order.saga_state = "COMPENSATED"
    record_status(db, order, "CANCELLED", "Compensação solicitada ao Billing; confirmar reembolso no provedor")
    record_outbox(
        db,
        order.id,
        "COMPENSATION_COMPLETED",
        {"payment_id": order.payment_id, "action": "REFUND_REQUIRED"},
        status="PROCESSED",
    )
    db.commit()
    return order_document(order)


@app.get("/orders/{order_id}/outbox")
def get_order_outbox(
    order_id: str,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    ensure_order_access(order, actor)
    messages = db.scalars(
        select(OutboxMessage).where(OutboxMessage.aggregate_id == order_id).order_by(OutboxMessage.created_at.asc())
    ).all()
    return [
        {
            "id": m.id,
            "event_type": m.event_type,
            "payload": m.payload,
            "status": m.status,
            "error_message": m.error_message,
            "created_at": m.created_at,
            "processed_at": m.processed_at,
        }
        for m in messages
    ]
