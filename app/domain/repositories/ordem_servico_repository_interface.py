from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.ordem_servico import OrdemServico


class OrdemServicoRepositoryInterface(ABC):
    @abstractmethod
    def salvar(self, ordem: OrdemServico) -> OrdemServico:
        pass

    @abstractmethod
    def buscar_por_id(self, ordem_id: int) -> Optional[OrdemServico]:
        pass

    @abstractmethod
    def listar_todas(self, skip: int = 0, limit: int = 100, status=None, cliente_id=None) -> List[OrdemServico]:
        pass

    @abstractmethod
    def atualizar(self, ordem: OrdemServico) -> OrdemServico:
        pass

    @abstractmethod
    def buscar_pendentes_por_cliente(self, cliente_id: int) -> List[OrdemServico]:
        pass

    @abstractmethod
    def listar_ativas_ordenadas(self, skip: int = 0, limit: int = 100) -> List[OrdemServico]:
        pass