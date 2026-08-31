from app.domain.entities.servico import Servico
from app.domain.repositories.servico_repository_interface import ServicoRepositoryInterface
from app.domain.exceptions.servico_exceptions import ServicoNaoEncontradoError, ServicoPrecoInvalidoError


class AtualizarServicoUseCase:
    def __init__(self, repository: ServicoRepositoryInterface):
        self.repository = repository

    def execute(self, servico_id: int, dados_atualizacao: dict) -> Servico:
        servico = self.repository.buscar_por_id(servico_id)
        if not servico:
            raise ServicoNaoEncontradoError()

        if "preco" in dados_atualizacao and dados_atualizacao["preco"] <= 0:
            raise ServicoPrecoInvalidoError()

        for field, value in dados_atualizacao.items():
            if hasattr(servico, field):
                setattr(servico, field, value)

        return self.repository.atualizar(servico)


class DeletarServicoUseCase:
    def __init__(self, repository: ServicoRepositoryInterface):
        self.repository = repository

    def execute(self, servico_id: int) -> None:
        servico = self.repository.buscar_por_id(servico_id)
        if not servico:
            raise ServicoNaoEncontradoError()
        self.repository.deletar(servico_id)
