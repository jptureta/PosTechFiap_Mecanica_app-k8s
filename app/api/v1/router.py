from fastapi import APIRouter
from app.api.v1 import auth, clientes, veiculos, servicos, pecas, ordens_servico, webhooks

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(clientes.router)
router.include_router(veiculos.router)
router.include_router(servicos.router)
router.include_router(pecas.router)
router.include_router(ordens_servico.router)
router.include_router(webhooks.router)
