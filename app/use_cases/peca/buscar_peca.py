from typing import List
from app.domain.entities.peca import Peca
from app.domain.repositories.peca_repository_interface import PecaRepositoryInterface
from app.domain.exceptions.peca_exceptions import PecaNaoEncontradaError


class BuscarPecaUseCase:
    def __init__(self, repository: PecaRepositoryInterface):
        self.repository = repository

    def execute(self, peca_id: int) -> Peca:
        peca = self.repository.buscar_por_id(peca_id)
        if not peca:
            raise PecaNaoEncontradaError()
        return peca


class ListarPecasUseCase:
    def __init__(self, repository: PecaRepositoryInterface):
        self.repository = repository

    def execute(self, skip: int = 0, limit: int = 100) -> List[Peca]:
        return self.repository.listar_todas(skip=skip, limit=limit)
