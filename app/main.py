from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Oficina Mecânica - Sistema de Gestão",
    description=(
        "API RESTful para gestão de ordens de serviço, clientes, veículos, "
        "serviços e peças de uma oficina mecânica. "
        "Arquitetura Clean Architecture — Tech Challenge FIAP Fase 2."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


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
    return {"status": "ok", "service": "Oficina Mecânica API", "version": "1.0.0"}
