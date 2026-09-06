"""
Worker de processamento de notificações via Redis.
Consome mensagens da fila e processa (log, email, etc.).
"""

import json
import logging
import signal
import sys

from app.infrastructure.redis_client import consumir_notificacao
from app.observability import logger, record_integration_failure, record_order_status_transition

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logger

running = True


def handle_signal(signum, frame):
    global running
    logger.info("Recebido sinal de encerramento. Finalizando worker...")
    running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def processar_notificacao(notificacao: dict) -> None:
    """Processa uma notificação recebida da fila."""
    tipo = notificacao.get("tipo")
    dados = notificacao.get("dados", {})

    if tipo == "os_criada":
        logger.info(
            "Nova OS criada - ID: %s, Cliente: %s, Valor: R$ %s",
            dados.get("ordem_servico_id"),
            dados.get("cliente_id"),
            dados.get("valor_total"),
            extra={"order_id": dados.get("ordem_servico_id"), "status": "recebida"},
        )
        record_order_status_transition("recebida", dados.get("ordem_servico_id"))
    elif tipo == "status_alterado":
        logger.info(
            "Status alterado - OS: %s, De: %s -> Para: %s",
            dados.get("ordem_servico_id"),
            dados.get("status_anterior"),
            dados.get("status_novo"),
            extra={"order_id": dados.get("ordem_servico_id"), "status": dados.get("status_novo")},
        )
        record_order_status_transition(str(dados.get("status_novo")), dados.get("ordem_servico_id"))
    else:
        logger.warning("Tipo de notificação desconhecido: %s", tipo, extra={"event_type": tipo})
        record_integration_failure("redis_consumer", "unknown_notification_type")


def main():
    logger.info("Worker de notificações iniciado. Aguardando mensagens...")

    while running:
        try:
            notificacao = consumir_notificacao()
            if notificacao:
                processar_notificacao(notificacao)
        except Exception as e:
            logger.error("Erro ao processar notificação: %s", str(e))

    logger.info("Worker encerrado.")


if __name__ == "__main__":
    main()
