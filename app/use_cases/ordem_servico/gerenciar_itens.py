from decimal import Decimal
from datetime import datetime
from app.domain.entities.ordem_servico import OrdemServico, OrdemServicoServico, OrdemServicoPeca, OrdemServicoHistorico
from app.domain.repositories.ordem_servico_repository_interface import OrdemServicoRepositoryInterface
from app.domain.repositories.servico_repository_interface import ServicoRepositoryInterface
from app.domain.repositories.peca_repository_interface import PecaRepositoryInterface
from app.domain.exceptions.ordem_servico_exceptions import OrdemServicoNaoEncontradaError, TransicaoStatusInvalidaError
from app.domain.exceptions.servico_exceptions import ServicoNaoEncontradoError
from app.domain.exceptions.peca_exceptions import PecaNaoEncontradaError, PecaError
from app.domain.enums import StatusOrdemServico


class AdicionarItemOrdemServicoUseCase:
    def __init__(
        self,
        ordem_repo: OrdemServicoRepositoryInterface,
        servico_repo: ServicoRepositoryInterface,
        peca_repo: PecaRepositoryInterface
    ):
        self.ordem_repo = ordem_repo
        self.servico_repo = servico_repo
        self.peca_repo = peca_repo

    def adicionar_servico(self, ordem_id: int, servico_id: int, quantidade: int) -> OrdemServico:
        ordem = self.ordem_repo.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()

        if ordem.status not in [StatusOrdemServico.RECEBIDA, StatusOrdemServico.EM_DIAGNOSTICO]:
             raise TransicaoStatusInvalidaError(ordem.status, "Adição de item")

        servico = self.servico_repo.buscar_por_id(servico_id)
        if not servico:
            raise ServicoNaoEncontradoError()

        ordem.itens_servico.append(OrdemServicoServico(
            servico_id=servico.id,
            quantidade=quantidade,
            valor_unitario=servico.preco,
            valor_total=servico.preco * quantidade,
            nome_servico=servico.nome
        ))
        ordem.calcular_total()
        return self.ordem_repo.atualizar(ordem)

    def adicionar_peca(self, ordem_id: int, peca_id: int, quantidade: int) -> OrdemServico:
        ordem = self.ordem_repo.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()

        if ordem.status not in [StatusOrdemServico.RECEBIDA, StatusOrdemServico.EM_DIAGNOSTICO]:
             raise TransicaoStatusInvalidaError(ordem.status, "Adição de item")

        peca = self.peca_repo.buscar_por_id(peca_id)
        if not peca:
            raise PecaNaoEncontradaError()

        if peca.quantidade_estoque < quantidade:
             raise PecaError("Estoque insuficiente")

        # Lógica de reserva se a OS já estiver aprovada ou em andamento
        if ordem.status in [StatusOrdemServico.EM_EXECUCAO]:
             peca.quantidade_reservada += quantidade
             self.peca_repo.atualizar(peca)

        ordem.itens_peca.append(OrdemServicoPeca(
            peca_id=peca.id,
            quantidade=quantidade,
            valor_unitario=peca.preco,
            valor_total=peca.preco * quantidade,
            nome_peca=peca.nome
        ))
        ordem.calcular_total()
        return self.ordem_repo.atualizar(ordem)


class RemoverItemOrdemServicoUseCase:
    def __init__(self, repository: OrdemServicoRepositoryInterface, peca_repo: PecaRepositoryInterface = None):
        self.repository = repository
        self.peca_repo = peca_repo

    def remover_servico(self, ordem_id: int, servico_id: int) -> OrdemServico:
        ordem = self.repository.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()
        
        if ordem.status not in [StatusOrdemServico.RECEBIDA, StatusOrdemServico.EM_DIAGNOSTICO]:
             raise TransicaoStatusInvalidaError(ordem.status, "Remoção de item")

        ordem.itens_servico = [item for item in ordem.itens_servico if item.servico_id != servico_id]
        ordem.calcular_total()
        return self.repository.atualizar(ordem)

    def remover_peca(self, ordem_id: int, peca_id: int) -> OrdemServico:
        ordem = self.repository.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()

        if ordem.status not in [StatusOrdemServico.RECEBIDA, StatusOrdemServico.EM_DIAGNOSTICO, StatusOrdemServico.AGUARDANDO_APROVACAO, StatusOrdemServico.EM_EXECUCAO]:
             raise TransicaoStatusInvalidaError(ordem.status, "Remoção de item")

        # Se houver repositório de peças e a OS tiver reserva, liberar reserva
        if self.peca_repo and ordem.orcamento_aprovado:
             for item in ordem.itens_peca:
                  if item.peca_id == peca_id:
                       peca = self.peca_repo.buscar_por_id(peca_id)
                       if peca:
                            peca.quantidade_reservada -= item.quantidade
                            self.peca_repo.atualizar(peca)

        ordem.itens_peca = [item for item in ordem.itens_peca if item.peca_id != peca_id]
        ordem.calcular_total()
        return self.repository.atualizar(ordem)
