import re
from typing import List, Optional
from app.domain.entities.ordem_servico import OrdemServico
from app.domain.repositories.ordem_servico_repository_interface import OrdemServicoRepositoryInterface
from app.domain.repositories.cliente_repository_interface import ClienteRepositoryInterface
from app.domain.exceptions.cliente_exceptions import ClienteNaoEncontradoError
from app.domain.exceptions.ordem_servico_exceptions import OrdemServicoNaoEncontradaError


def _normalizar_documento(valor: str) -> str:
    """Remove caracteres não numéricos de um documento (CPF/CNPJ)."""
    return re.sub(r"\D", "", valor) if valor else ""


class AcompanharOrdemServicoUseCase:
    def __init__(
        self,
        ordem_repo: OrdemServicoRepositoryInterface,
        cliente_repo: ClienteRepositoryInterface
    ):
        self.ordem_repo = ordem_repo
        self.cliente_repo = cliente_repo

    def execute(self, cpf_cnpj: str) -> List[OrdemServico]:
        """Lista todas as ordens de serviço de um cliente pelo CPF/CNPJ."""
        cliente = self.cliente_repo.buscar_por_cpf_cnpj(cpf_cnpj)
        if not cliente:
            raise ClienteNaoEncontradoError()
        
        return self.ordem_repo.listar_todas(cliente_id=cliente.id)

    def por_id_e_cpf_cnpj(self, ordem_id: int, cpf_cnpj: str) -> OrdemServico:
        """Busca uma OS por ID e valida pertencimento ao CPF/CNPJ informado.

        Endpoint público de acompanhamento — não exige autenticação.
        Levanta OrdemServicoNaoEncontradaError se a OS não existir.
        Levanta ClienteNaoEncontradoError se o CPF/CNPJ não bater.
        """
        ordem = self.ordem_repo.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()

        cliente = self.cliente_repo.buscar_por_id(ordem.cliente_id)

        if not cliente or _normalizar_documento(cliente.cpf_cnpj) != _normalizar_documento(cpf_cnpj):
            raise ClienteNaoEncontradoError("Acesso negado: CPF/CNPJ inválido para esta ordem de serviço")

        return ordem
