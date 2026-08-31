from app.domain.repositories.cliente_repository_interface import ClienteRepositoryInterface
from app.domain.exceptions.cliente_exceptions import ClienteNaoEncontradoError, ClientePossuiPendenciasError


class AtualizarClienteUseCase:
    def __init__(self, repository: ClienteRepositoryInterface):
        self.repository = repository

    def execute(self, cliente_id: int, dados_atualizacao: dict) -> "Cliente":
        cliente = self.repository.buscar_por_id(cliente_id)
        if not cliente:
            raise ClienteNaoEncontradoError()

        for field, value in dados_atualizacao.items():
            if hasattr(cliente, field):
                setattr(cliente, field, value)

        return self.repository.atualizar(cliente)


class DesativarClienteUseCase:
    def __init__(self, repository: ClienteRepositoryInterface, pendencia_checker=None):
        self.repository = repository
        self.pendencia_checker = pendencia_checker

    def execute(self, cliente_id: int) -> None:
        cliente = self.repository.buscar_por_id(cliente_id)
        if not cliente:
            raise ClienteNaoEncontradoError()

        if self.pendencia_checker and self.pendencia_checker.possui_pendencias(cliente_id):
            raise ClientePossuiPendenciasError()

        cliente.desativar()
        self.repository.atualizar(cliente)


class AtivarClienteUseCase:
    def __init__(self, repository: ClienteRepositoryInterface):
        self.repository = repository

    def execute(self, cliente_id: int) -> "Cliente":
        cliente = self.repository.buscar_por_id(cliente_id)
        if not cliente:
            raise ClienteNaoEncontradoError()

        cliente.ativar()
        return self.repository.atualizar(cliente)
