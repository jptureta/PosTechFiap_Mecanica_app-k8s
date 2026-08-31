from abc import ABC, abstractmethod
from typing import Optional


class NotificacaoServiceInterface(ABC):
    """Porta de notificação do domínio.

    Define o contrato para notificar partes interessadas sobre mudanças
    na ordem de serviço. A implementação concreta (e-mail, SMS, webhook)
    fica na camada de adaptadores.
    """

    @abstractmethod
    def notificar_mudanca_status(
        self,
        ordem_id: int,
        status_anterior: str,
        status_novo: str,
        cliente_email: Optional[str] = None,
    ) -> None:
        """Notifica o cliente sobre mudança de status da OS."""
        pass

    @abstractmethod
    def notificar_orcamento_aprovado(
        self,
        ordem_id: int,
        valor_total: float,
        cliente_email: Optional[str] = None,
    ) -> None:
        """Notifica que o orçamento foi aprovado e a execução será iniciada."""
        pass

    @abstractmethod
    def notificar_orcamento_recusado(
        self,
        ordem_id: int,
        cliente_email: Optional[str] = None,
    ) -> None:
        """Notifica que o orçamento foi recusado e a OS será cancelada."""
        pass
