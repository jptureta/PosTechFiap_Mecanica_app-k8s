from typing import List, Optional
from app.domain.entities.ordem_servico import OrdemServico
from app.domain.repositories.ordem_servico_repository_interface import OrdemServicoRepositoryInterface
from app.domain.exceptions.ordem_servico_exceptions import OrdemServicoNaoEncontradaError


class BuscarOrdemServicoUseCase:
    def __init__(self, repository: OrdemServicoRepositoryInterface):
        self.repository = repository

    def execute(self, ordem_id: int) -> OrdemServico:
        ordem = self.repository.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()
        return ordem


class ListarOrdensServicoUseCase:
    def __init__(self, repository: OrdemServicoRepositoryInterface):
        self.repository = repository

    def execute(self, skip: int = 0, limit: int = 100, status=None, cliente_id=None) -> List[OrdemServico]:
        return self.repository.listar_todas(skip=skip, limit=limit, status=status, cliente_id=cliente_id)


class ListarOrdensServicoAtivasUseCase:
    def __init__(self, repository: OrdemServicoRepositoryInterface):
        self.repository = repository
    
    def execute(self, skip: int = 0, limit: int = 100) -> List[OrdemServico]:
        return self.repository.listar_ativas_ordenadas(skip=skip, limit=limit)