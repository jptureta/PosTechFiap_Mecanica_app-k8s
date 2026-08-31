from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.cliente import Cliente


class ClienteRepositoryInterface(ABC):
    @abstractmethod
    def salvar(self, cliente: Cliente) -> Cliente:
        pass

    @abstractmethod
    def buscar_por_id(self, cliente_id: int) -> Optional[Cliente]:
        pass

    @abstractmethod
    def buscar_por_cpf_cnpj(self, cpf_cnpj: str) -> Optional[Cliente]:
        pass

    @abstractmethod
    def listar_todos(self, skip: int = 0, limit: int = 100) -> List[Cliente]:
        pass

    @abstractmethod
    def atualizar(self, cliente: Cliente) -> Cliente:
        pass
