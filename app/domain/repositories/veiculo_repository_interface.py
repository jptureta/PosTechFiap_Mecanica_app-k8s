from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.veiculo import Veiculo


class VeiculoRepositoryInterface(ABC):
    @abstractmethod
    def salvar(self, veiculo: Veiculo) -> Veiculo:
        pass

    @abstractmethod
    def buscar_por_id(self, veiculo_id: int) -> Optional[Veiculo]:
        pass

    @abstractmethod
    def buscar_por_placa(self, placa: str) -> Optional[Veiculo]:
        pass

    @abstractmethod
    def buscar_por_cliente(self, cliente_id: int) -> List[Veiculo]:
        pass

    @abstractmethod
    def listar_todos(self, skip: int = 0, limit: int = 100) -> List[Veiculo]:
        pass

    @abstractmethod
    def atualizar(self, veiculo: Veiculo) -> Veiculo:
        pass

    @abstractmethod
    def deletar(self, veiculo_id: int) -> None:
        pass
