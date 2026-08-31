from typing import Optional, List
from app.domain.entities.cliente import Cliente
from app.domain.repositories.cliente_repository_interface import ClienteRepositoryInterface
from app.domain.exceptions.cliente_exceptions import ClienteNaoEncontradoError


class BuscarClienteUseCase:
    def __init__(self, repository: ClienteRepositoryInterface):
        self.repository = repository

    def por_id(self, cliente_id: int) -> Cliente:
        cliente = self.repository.buscar_por_id(cliente_id)
        if not cliente:
            raise ClienteNaoEncontradoError()
        return cliente

    def por_cpf_cnpj(self, cpf_cnpj: str) -> Cliente:
        cliente = self.repository.buscar_por_cpf_cnpj(cpf_cnpj)
        if not cliente:
            raise ClienteNaoEncontradoError()
        return cliente


class ListarClientesUseCase:
    def __init__(self, repository: ClienteRepositoryInterface):
        self.repository = repository

    def execute(self, skip: int = 0, limit: int = 100) -> List[Cliente]:
        return self.repository.listar_todos(skip=skip, limit=limit)
