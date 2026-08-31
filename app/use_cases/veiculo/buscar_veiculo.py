from typing import List
from app.domain.entities.veiculo import Veiculo
from app.domain.repositories.veiculo_repository_interface import VeiculoRepositoryInterface
from app.domain.exceptions.veiculo_exceptions import VeiculoNaoEncontradoError


class BuscarVeiculoUseCase:
    def __init__(self, repository: VeiculoRepositoryInterface):
        self.repository = repository

    def por_id(self, veiculo_id: int) -> Veiculo:
        veiculo = self.repository.buscar_por_id(veiculo_id)
        if not veiculo:
            raise VeiculoNaoEncontradoError()
        return veiculo

    def por_cliente(self, cliente_id: int) -> List[Veiculo]:
        return self.repository.buscar_por_cliente(cliente_id)


class ListarVeiculosUseCase:
    def __init__(self, repository: VeiculoRepositoryInterface):
        self.repository = repository

    def execute(self, skip: int = 0, limit: int = 100) -> List[Veiculo]:
        return self.repository.listar_todos(skip=skip, limit=limit)
