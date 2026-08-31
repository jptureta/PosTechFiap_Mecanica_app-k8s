import logging
from typing import Optional
from app.domain.services.notificacao_service_interface import NotificacaoServiceInterface

logger = logging.getLogger(__name__)


class EmailNotificacaoService(NotificacaoServiceInterface):
    """Adaptador de notificação via e-mail simulado.

    Implementa a porta NotificacaoServiceInterface logando as notificações
    no formato de e-mail. Em produção, pode ser substituído por uma
    implementação real via SMTP, SendGrid, SES, etc.
    """

    def notificar_mudanca_status(
        self,
        ordem_id: int,
        status_anterior: str,
        status_novo: str,
        cliente_email: Optional[str] = None,
    ) -> None:
        destinatario = cliente_email or "cliente@oficina.local"
        logger.info(
            "[EMAIL] Para: %s | Assunto: Atualização OS #%d | "
            "Status: %s → %s",
            destinatario,
            ordem_id,
            status_anterior,
            status_novo,
        )

    def notificar_orcamento_aprovado(
        self,
        ordem_id: int,
        valor_total: float,
        cliente_email: Optional[str] = None,
    ) -> None:
        destinatario = cliente_email or "cliente@oficina.local"
        logger.info(
            "[EMAIL] Para: %s | Assunto: Orçamento Aprovado OS #%d | "
            "Valor: R$ %.2f | A execução dos serviços será iniciada.",
            destinatario,
            ordem_id,
            valor_total,
        )

    def notificar_orcamento_recusado(
        self,
        ordem_id: int,
        cliente_email: Optional[str] = None,
    ) -> None:
        destinatario = cliente_email or "cliente@oficina.local"
        logger.info(
            "[EMAIL] Para: %s | Assunto: Orçamento Recusado OS #%d | "
            "A ordem de serviço foi cancelada.",
            destinatario,
            ordem_id,
        )
