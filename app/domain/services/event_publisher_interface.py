from abc import ABC, abstractmethod


class EventPublisherInterface(ABC):
    """Porta de publicação de eventos do domínio.

    Define o contrato para publicar eventos de domínio (alertas de estoque,
    notificações internas, etc.) sem acoplar os use cases à infraestrutura
    de mensageria (Redis, RabbitMQ, etc.).
    """

    @abstractmethod
    def publicar(self, evento: str, dados: dict) -> None:
        """Publica um evento de domínio."""
        pass
