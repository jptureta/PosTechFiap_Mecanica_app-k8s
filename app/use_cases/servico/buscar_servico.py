from typing import List
from app.domain.entities.servico import Servico
from app.domain.repositories.servico_repository_interface import ServicoRepositoryInterface
from app.domain.exceptions.servico_exceptions import ServicoNaoEncontradoError


class BuscarServicoUseCase:
    def __init__(self, repository: ServicoRepositoryInterface):
        self.repository = repository

    def execute(self, servico_id: int) -> Servico:
        servico = self.repository.buscar_por_id(servico_id)
        if not servico:
            raise ServicoNaoEncontradoError()
        return servico


class ListarServicosUseCase:
    def __init__(self, repository: ServicoRepositoryInterface):
        self.repository = repository

    def execute(self, skip: int = 0, limit: int = 100) -> List[Servico]:
        return self.repository.listar_todos(skip=skip, limit=limit)
