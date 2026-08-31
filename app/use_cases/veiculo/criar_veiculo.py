from app.domain.entities.veiculo import Veiculo
from app.domain.repositories.veiculo_repository_interface import VeiculoRepositoryInterface
from app.domain.repositories.cliente_repository_interface import ClienteRepositoryInterface
from app.domain.exceptions.veiculo_exceptions import VeiculoPlacaDuplicadaError
from app.domain.exceptions.cliente_exceptions import ClienteNaoEncontradoError


class CriarVeiculoUseCase:
    def __init__(self, veiculo_repo: VeiculoRepositoryInterface, cliente_repo: ClienteRepositoryInterface):
        self.veiculo_repo = veiculo_repo
        self.cliente_repo = cliente_repo

    def execute(self, cliente_id: int, placa: str, marca: str, modelo: str, ano: int, cor: str = None, observacoes: str = None) -> Veiculo:
        if not self.cliente_repo.buscar_por_id(cliente_id):
            raise ClienteNaoEncontradoError()

        if self.veiculo_repo.buscar_por_placa(placa):
            raise VeiculoPlacaDuplicadaError()

        veiculo = Veiculo(
            cliente_id=cliente_id,
            placa=placa,
            marca=marca,
            modelo=modelo,
            ano=ano,
            cor=cor,
            observacoes=observacoes
        )
        return self.veiculo_repo.salvar(veiculo)
