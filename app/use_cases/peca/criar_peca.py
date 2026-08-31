from decimal import Decimal
from app.domain.entities.peca import Peca
from app.domain.repositories.peca_repository_interface import PecaRepositoryInterface
from app.domain.exceptions.peca_exceptions import PecaPrecoInvalidoError


class CriarPecaUseCase:
    def __init__(self, repository: PecaRepositoryInterface):
        self.repository = repository

    def execute(self, nome: str, preco: Decimal, descricao: str = None, quantidade_estoque: int = 0, codigo: str = None, unidade_medida: str = None, estoque_minimo: int = 0) -> Peca:
        if preco <= 0:
            raise PecaPrecoInvalidoError()

        peca = Peca(
            nome=nome,
            preco=preco,
            descricao=descricao,
            quantidade_estoque=quantidade_estoque,
            codigo=codigo,
            unidade_medida=unidade_medida,
            estoque_minimo=estoque_minimo
        )
        return self.repository.salvar(peca)
