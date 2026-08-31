from app.domain.entities.peca import Peca
from app.domain.repositories.peca_repository_interface import PecaRepositoryInterface
from app.domain.exceptions.peca_exceptions import PecaNaoEncontradaError, PecaPrecoInvalidoError


class AtualizarPecaUseCase:
    def __init__(self, repository: PecaRepositoryInterface):
        self.repository = repository

    def execute(self, peca_id: int, dados_atualizacao: dict) -> Peca:
        peca = self.repository.buscar_por_id(peca_id)
        if not peca:
            raise PecaNaoEncontradaError()

        if "preco" in dados_atualizacao and dados_atualizacao["preco"] <= 0:
            raise PecaPrecoInvalidoError()

        for field, value in dados_atualizacao.items():
            if hasattr(peca, field):
                setattr(peca, field, value)

        return self.repository.atualizar(peca)


class DeletarPecaUseCase:
    def __init__(self, repository: PecaRepositoryInterface):
        self.repository = repository

    def execute(self, peca_id: int) -> None:
        peca = self.repository.buscar_por_id(peca_id)
        if not peca:
            raise PecaNaoEncontradaError()
        self.repository.deletar(peca_id)
