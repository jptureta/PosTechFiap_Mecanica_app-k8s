import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.v1.router import router
from app.config import get_settings
from app.observability import get_metrics_snapshot, logger, record_http_request, generate_request_id

settings = get_settings()

app = FastAPI(
    title="Oficina Mecânica - Sistema de Gestão",
    description=(
        "API RESTful para gestão de ordens de serviço, clientes, veículos, "
        "serviços e peças de uma oficina mecânica. "
        "Arquitetura Clean Architecture — Tech Challenge FIAP Fase 2."
    ),
    version=settings.DD_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next: Callable):
    start = time.perf_counter()
    request_id = generate_request_id()
    request.state.request_id = request_id

    try:
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        record_http_request(
            method=request.method,
            route=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            request_id=request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:  # pragma: no cover - propagates error after metric emit
        latency_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": request.url.path,
                "latency_ms": round(latency_ms, 2),
            },
        )
        record_http_request(
            method=request.method,
            route=request.url.path,
            status_code=500,
            latency_ms=latency_ms,
            request_id=request_id,
        )
        return JSONResponse(status_code=500, content={"detail": "internal_server_error"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"])
def health_check():
    """Verifica se a API está no ar."""
    return {"status": "ok", "service": "Oficina Mecânica API", "version": settings.DD_VERSION}


@app.get("/health", tags=["Health"])
def health_status():
    return {
        "status": "ok",
        "service": "Oficina Mecânica API",
        "uptime_seconds": get_metrics_snapshot()["uptime_seconds"],
        "version": settings.DD_VERSION,
    }


@app.get("/metrics", tags=["Monitoring"])
def metrics():
    return get_metrics_snapshot()
