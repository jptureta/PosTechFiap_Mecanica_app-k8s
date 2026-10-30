import os
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from redis import Redis
from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.auth import Actor, get_actor

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./execution-service.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("EXECUTION_QUEUE_KEY", "execution:queue")
OS_SERVICE_URL = os.getenv("OS_SERVICE_URL", "http://os-service:8000").rstrip("/")
INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

redis_client: Redis | None
try:
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None
_memory_queue: list[str] = []


class Base(DeclarativeBase):
    pass


class Execution(Base):
    __tablename__ = "executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="QUEUED")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    history: Mapped[list["ExecutionHistory"]] = relationship(back_populates="execution", cascade="all, delete-orphan")


class ExecutionHistory(Base):
    __tablename__ = "execution_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    execution: Mapped[Execution] = relationship(back_populates="history")


class EnqueueExecution(BaseModel):
    order_id: str = Field(min_length=1, max_length=36)
    priority: int = Field(ge=0, le=10, default=0)


class StatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=40)
    note: str = Field(min_length=1, max_length=500)


class Completion(BaseModel):
    note: str = Field(min_length=1, max_length=500, default="Serviço concluído")


def get_db():
    with SessionLocal() as session:
        yield session


def require_internal_token(x_internal_token: Annotated[str | None, Header()] = None) -> None:
    if not INTERNAL_TOKEN or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal service token")


def require_admin(actor: Actor = Depends(get_actor)) -> Actor:
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="only an administrator can execute an order")
    return actor


def record_status(db: Session, execution: Execution, new_status: str, note: str) -> None:
    if execution.status == new_status:
        return
    execution.history.append(ExecutionHistory(previous_status=execution.status, new_status=new_status, note=note))
    execution.status = new_status
    execution.updated_at = datetime.now(timezone.utc)


def enqueue(order_id: str) -> None:
    if redis_client is not None:
        try:
            redis_client.rpush(QUEUE_KEY, order_id)
            return
        except Exception:
            logger.warning("Redis queue unavailable; using process queue", exc_info=True)
    if order_id not in _memory_queue:
        _memory_queue.append(order_id)


def next_queued() -> str | None:
    if redis_client is not None:
        try:
            value = redis_client.lpop(QUEUE_KEY)
            if value is not None:
                return str(value)
        except Exception:
            logger.warning("Redis queue unavailable; using process queue", exc_info=True)
    return _memory_queue.pop(0) if _memory_queue else None


def execution_document(execution: Execution) -> dict:
    return {
        "id": execution.id,
        "order_id": execution.order_id,
        "status": execution.status,
        "priority": execution.priority,
        "notes": execution.notes,
        "created_at": execution.created_at,
        "updated_at": execution.updated_at,
        "history": [
            {"previous_status": h.previous_status, "new_status": h.new_status, "note": h.note, "changed_at": h.changed_at}
            for h in execution.history
        ],
    }


app = FastAPI(title="Execução e Produção", version="1.0.0")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        redis_ok = True
        if redis_client is not None:
            redis_client.ping()
    except (SQLAlchemyError, Exception) as exc:
        logger.exception("service dependency check failed")
        raise HTTPException(status_code=503, detail="database or queue unavailable") from exc
    return {"status": "ok", "service": "execution-service", "queue": "redis" if redis_ok else "memory"}


@app.get("/health/live")
def liveness():
    return {"status": "ok", "service": "execution-service"}


@app.post("/executions", status_code=status.HTTP_201_CREATED)
def create_execution(payload: EnqueueExecution, db: Session = Depends(get_db), _: Actor = Depends(require_admin)):
    execution = db.execute(select(Execution).where(Execution.order_id == payload.order_id)).scalar_one_or_none()
    if execution is not None:
        raise HTTPException(status_code=409, detail="execution already exists for this order")
    execution = Execution(order_id=payload.order_id, priority=payload.priority)
    execution.history.append(ExecutionHistory(previous_status=None, new_status="QUEUED", note="OS adicionada à fila"))
    db.add(execution)
    db.commit()
    db.refresh(execution)
    enqueue(execution.order_id)
    return execution_document(execution)


@app.get("/executions")
def list_executions(db: Session = Depends(get_db), _: Actor = Depends(get_actor)):
    executions = db.query(Execution).order_by(Execution.priority.desc(), Execution.created_at.asc()).all()
    return [execution_document(item) for item in executions]


@app.get("/executions/{execution_id}")
def get_execution(execution_id: str, db: Session = Depends(get_db), _: Actor = Depends(get_actor)):
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    return execution_document(execution)


@app.post("/executions/next")
def claim_next(db: Session = Depends(get_db), _: Actor = Depends(require_admin)):
    order_id = next_queued()
    if order_id is None:
        return {"execution": None}
    execution = db.query(Execution).filter(Execution.order_id == order_id).one_or_none()
    if execution is None:
        return {"execution": None}
    return {"execution": execution_document(execution)}


@app.patch("/executions/{execution_id}/status")
def update_status(execution_id: str, payload: StatusUpdate, db: Session = Depends(get_db), _: Actor = Depends(require_admin)):
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    allowed = {"QUEUED": {"DIAGNOSING", "CANCELLED"}, "DIAGNOSING": {"REPAIRING", "CANCELLED"}, "REPAIRING": {"COMPLETED", "CANCELLED"}}
    if payload.status not in allowed.get(execution.status, set()) and payload.status != execution.status:
        raise HTTPException(status_code=409, detail=f"invalid transition from {execution.status} to {payload.status}")
    record_status(db, execution, payload.status, payload.note)
    db.commit()
    db.refresh(execution)
    notify_os(execution, payload.status, payload.note)
    return execution_document(execution)


@app.post("/executions/{execution_id}/complete")
def complete(execution_id: str, payload: Completion, db: Session = Depends(get_db), _: Actor = Depends(require_admin)):
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    if execution.status not in {"DIAGNOSING", "REPAIRING"}:
        raise HTTPException(status_code=409, detail=f"cannot complete execution in {execution.status}")
    record_status(db, execution, "COMPLETED", payload.note)
    db.commit()
    db.refresh(execution)
    notify_os(execution, "COMPLETED", payload.note)
    return execution_document(execution)


def notify_os(execution: Execution, status_value: str, note: str) -> None:
    os_status = {"DIAGNOSING": "IN_DIAGNOSIS", "REPAIRING": "IN_PROGRESS", "COMPLETED": "COMPLETED", "CANCELLED": "CANCELLED"}.get(status_value)
    if os_status is None:
        return
    try:
        response = httpx.patch(f"{OS_SERVICE_URL}/internal/orders/{execution.order_id}/status", json={"status": os_status, "note": note}, headers={"X-Internal-Token": INTERNAL_TOKEN}, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("failed to notify OS service about order %s", execution.order_id)
        raise HTTPException(status_code=503, detail="OS service notification failed") from exc
