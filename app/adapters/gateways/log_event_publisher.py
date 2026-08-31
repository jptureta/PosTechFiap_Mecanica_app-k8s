import logging
from app.domain.services.event_publisher_interface import EventPublisherInterface

logger = logging.getLogger(__name__)


class LogEventPublisher(EventPublisherInterface):
    """Adaptador de publicação de eventos via log.

    Implementa a porta EventPublisherInterface logando os eventos.
    Em produção, pode ser substituído por uma implementação via
    Redis, RabbitMQ, Kafka, etc.
    """

    def publicar(self, evento: str, dados: dict) -> None:
        logger.info("EVENTO: %s - %s", evento, dados)
