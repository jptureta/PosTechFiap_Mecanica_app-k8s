import json
import redis
from app.config import get_settings

settings = get_settings()

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

QUEUE_NOTIFICACOES = "fila:notificacoes"


def publicar_notificacao(tipo: str, dados: dict) -> None:
    """Publica uma notificação na fila Redis."""
    mensagem = json.dumps({"tipo": tipo, "dados": dados})
    redis_client.rpush(QUEUE_NOTIFICACOES, mensagem)


def consumir_notificacao() -> dict | None:
    """Consome uma notificação da fila Redis (blocking pop com timeout)."""
    resultado = redis_client.blpop(QUEUE_NOTIFICACOES, timeout=5)
    if resultado:
        _, mensagem = resultado
        return json.loads(mensagem)
    return None
