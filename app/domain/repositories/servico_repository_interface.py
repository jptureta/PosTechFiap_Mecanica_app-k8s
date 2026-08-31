from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.servico import Servico


class ServicoRepositoryInterface(ABC):
    @abstractmethod
    def salvar(self, servico: Servico) -> Servico:
        pass

    @abstractmethod
    def buscar_por_id(self, servico_id: int) -> Optional[Servico]:
        pass

    @abstractmethod
    def listar_todos(self, skip: int = 0, limit: int = 100) -> List[Servico]:
        pass

    @abstractmethod
    def atualizar(self, servico: Servico) -> Servico:
        pass

    @abstractmethod
    def deletar(self, servico_id: int) -> None:
        pass
