from app.domain.entities.veiculo import Veiculo
from app.domain.repositories.veiculo_repository_interface import VeiculoRepositoryInterface
from app.domain.exceptions.veiculo_exceptions import VeiculoNaoEncontradoError


class AtualizarVeiculoUseCase:
    def __init__(self, repository: VeiculoRepositoryInterface):
        self.repository = repository

    def execute(self, veiculo_id: int, dados_atualizacao: dict) -> Veiculo:
        veiculo = self.repository.buscar_por_id(veiculo_id)
        if not veiculo:
            raise VeiculoNaoEncontradoError()

        for field, value in dados_atualizacao.items():
            if hasattr(veiculo, field):
                setattr(veiculo, field, value)

        return self.repository.atualizar(veiculo)


class DeletarVeiculoUseCase:
    def __init__(self, repository: VeiculoRepositoryInterface):
        self.repository = repository

    def execute(self, veiculo_id: int) -> None:
        veiculo = self.repository.buscar_por_id(veiculo_id)
        if not veiculo:
            raise VeiculoNaoEncontradoError()
        self.repository.deletar(veiculo_id)
