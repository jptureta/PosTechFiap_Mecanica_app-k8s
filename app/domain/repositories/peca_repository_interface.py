from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.peca import Peca


class PecaRepositoryInterface(ABC):
    @abstractmethod
    def salvar(self, peca: Peca) -> Peca:
        pass

    @abstractmethod
    def buscar_por_id(self, peca_id: int) -> Optional[Peca]:
        pass

    @abstractmethod
    def listar_todas(self, skip: int = 0, limit: int = 100) -> List[Peca]:
        pass

    @abstractmethod
    def atualizar(self, peca: Peca) -> Peca:
        pass

    @abstractmethod
    def deletar(self, peca_id: int) -> None:
        pass
