from decimal import Decimal
from app.domain.entities.servico import Servico
from app.domain.repositories.servico_repository_interface import ServicoRepositoryInterface
from app.domain.exceptions.servico_exceptions import ServicoPrecoInvalidoError


class CriarServicoUseCase:
    def __init__(self, repository: ServicoRepositoryInterface):
        self.repository = repository

    def execute(self, nome: str, preco: Decimal, descricao: str = None, tempo_estimado_minutos: int = None) -> Servico:
        if preco <= 0:
            raise ServicoPrecoInvalidoError()

        servico = Servico(
            nome=nome,
            preco=preco,
            descricao=descricao,
            tempo_estimado_minutos=tempo_estimado_minutos
        )
        return self.repository.salvar(servico)
