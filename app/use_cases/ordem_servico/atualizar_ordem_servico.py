from datetime import datetime, timezone
from typing import Optional
from app.domain.entities.ordem_servico import OrdemServico, OrdemServicoHistorico
from app.domain.repositories.ordem_servico_repository_interface import OrdemServicoRepositoryInterface
from app.domain.repositories.peca_repository_interface import PecaRepositoryInterface
from app.domain.exceptions.ordem_servico_exceptions import (
    OrdemServicoError,
    OrdemServicoNaoEncontradaError,
    TransicaoStatusInvalidaError,
)
from app.domain.exceptions.peca_exceptions import PecaError
from app.domain.services.notificacao_service_interface import NotificacaoServiceInterface
from app.domain.services.event_publisher_interface import EventPublisherInterface
from app.domain.enums import StatusOrdemServico


class AtualizarStatusOrdemServicoUseCase:
    def __init__(
        self,
        repository: OrdemServicoRepositoryInterface,
        peca_repo: PecaRepositoryInterface,
        notificacao_service: Optional[NotificacaoServiceInterface] = None,
        event_publisher: Optional[EventPublisherInterface] = None,
    ):
        self.repository = repository
        self.peca_repo = peca_repo
        self.notificacao_service = notificacao_service
        self.event_publisher = event_publisher

    def execute(self, ordem_id: int, novo_status: StatusOrdemServico, observacao: str = None) -> OrdemServico:
        ordem = self.repository.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()

        if ordem.status == novo_status:
            return ordem

        if novo_status == StatusOrdemServico.EM_EXECUCAO and not ordem.orcamento_aprovado:
            raise OrdemServicoError("Necessário ter o orçamento aprovado para iniciar a execução")

        if not ordem.pode_alterar_status(novo_status):
            raise TransicaoStatusInvalidaError(ordem.status, novo_status)

        status_anterior = ordem.status
        
        # Lógica de Estoque Baseada em Transição de Status
        # A reserva já é feita em AprovarOrcamentoUseCase; evita dupla reserva
        
        if novo_status == StatusOrdemServico.FINALIZADA:
            ordem.data_finalizacao = datetime.now(timezone.utc)
            # Efetivar saída do estoque (remover de estoque e de reserva)
            for item in ordem.itens_peca:
                 peca = self.peca_repo.buscar_por_id(item.peca_id)
                 if peca:
                     peca.quantidade_estoque -= item.quantidade
                     peca.quantidade_reservada -= item.quantidade
                     self.peca_repo.atualizar(peca)
                     
                     # Alerta de estoque baixo
                     if peca.quantidade_estoque <= peca.estoque_minimo:
                          if self.event_publisher:
                              self.event_publisher.publicar(
                                  "AlertaDeEstoqueEmitido",
                                  {"id": peca.id, "estoque": peca.quantidade_estoque},
                              )
                              """
                              20/6/2026 - Code Smell? 
                              contém um import de compatibilidade legada (from app.services import ordem_servico_service) 
                               viola o princípio de dependência e deveria ser removido

                          # Compatibilidade com testes que fazem mock do service legado
                          from app.services import ordem_servico_service
                          ordem_servico_service.publicar_notificacao(
                              "AlertaDeEstoqueEmitido",
                              {"id": peca.id, "estoque": peca.quantidade_estoque},
                          )
                          """

        if novo_status == StatusOrdemServico.CANCELADA:
             # Liberar reserva se estava em execução
             # 20/6/2026 - Corrigido bug onde ao cancelar uma ordem que estava aguardando aprovação, o estoque reservado não era liberado
             if status_anterior in [StatusOrdemServico.EM_EXECUCAO] or ordem.orcamento_aprovado:
                  for item in ordem.itens_peca:
                      peca = self.peca_repo.buscar_por_id(item.peca_id)
                      if peca:
                          peca.quantidade_reservada -= item.quantidade
                          self.peca_repo.atualizar(peca)

        if novo_status == StatusOrdemServico.ENTREGUE:
            ordem.data_entrega = datetime.now(timezone.utc)

        ordem.status = novo_status
        ordem.historico.append(OrdemServicoHistorico(
            status_anterior=status_anterior,
            status_novo=novo_status,
            data_alteracao=datetime.now(timezone.utc),
            observacao=observacao
        ))

        resultado = self.repository.atualizar(ordem)

        # Notificar mudança de status via e-mail
        if self.notificacao_service:
            self.notificacao_service.notificar_mudanca_status(
                ordem_id=ordem_id,
                status_anterior=str(status_anterior),
                status_novo=str(novo_status),
            )

        return resultado


class AprovarOrcamentoUseCase:
    def __init__(
        self,
        repository: OrdemServicoRepositoryInterface,
        peca_repo: PecaRepositoryInterface,
        notificacao_service: Optional[NotificacaoServiceInterface] = None,
    ):
        self.repository = repository
        self.peca_repo = peca_repo
        self.notificacao_service = notificacao_service

    def execute(self, ordem_id: int) -> OrdemServico:
        ordem = self.repository.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()
        
        if ordem.orcamento_aprovado:
             raise OrdemServicoError("Orçamento já foi aprovado")

        if ordem.status != StatusOrdemServico.AGUARDANDO_APROVACAO:
             raise TransicaoStatusInvalidaError(ordem.status, "EM_EXECUCAO (Aprovação)")

        # Validar estoque disponível para todas as peças antes de reservar
        for item in ordem.itens_peca:
             peca = self.peca_repo.buscar_por_id(item.peca_id)
             if peca:
                 disponivel = peca.quantidade_estoque - peca.quantidade_reservada
                 if disponivel < item.quantidade:
                      raise PecaError(f"Estoque insuficiente para a peça {peca.nome}")

        status_anterior = ordem.status
        ordem.aprovar_orcamento()  # Define orcamento_aprovado=True
        
        # Reservar estoque ao aprovar
        for item in ordem.itens_peca:
             peca = self.peca_repo.buscar_por_id(item.peca_id)
             if peca:
                 peca.quantidade_reservada += item.quantidade
                 self.peca_repo.atualizar(peca)

        ordem.historico.append(OrdemServicoHistorico(
            status_anterior=status_anterior,
            status_novo=ordem.status,
            data_alteracao=datetime.now(timezone.utc),
            observacao="Orçamento aprovado pelo cliente"
        ))

        resultado = self.repository.atualizar(ordem)

        # Notificar aprovação de orçamento via e-mail
        if self.notificacao_service:
            self.notificacao_service.notificar_orcamento_aprovado(
                ordem_id=ordem_id,
                valor_total=float(ordem.valor_total),
            )

        return resultado


class RecusarOrcamentoUseCase:
    def __init__(
        self,
        repository: OrdemServicoRepositoryInterface,
        notificacao_service: Optional[NotificacaoServiceInterface] = None,
    ):
        self.repository = repository
        self.notificacao_service = notificacao_service

    def execute(self, ordem_id: int) -> OrdemServico:
        ordem = self.repository.buscar_por_id(ordem_id)
        if not ordem:
            raise OrdemServicoNaoEncontradaError()

        if ordem.status != StatusOrdemServico.AGUARDANDO_APROVACAO:
            raise TransicaoStatusInvalidaError(ordem.status, StatusOrdemServico.CANCELADA)

        status_anterior = ordem.status
        ordem.status = StatusOrdemServico.CANCELADA

        ordem.historico.append(OrdemServicoHistorico(
            status_anterior=status_anterior,
            status_novo=ordem.status,
            data_alteracao=datetime.now(timezone.utc),
            observacao="Orçamento recusado pelo cliente"
        ))

        resultado = self.repository.atualizar(ordem)

        # Notificar recusa de orçamento via e-mail
        if self.notificacao_service:
            self.notificacao_service.notificar_orcamento_recusado(
                ordem_id=ordem_id,
            )

        return resultado
