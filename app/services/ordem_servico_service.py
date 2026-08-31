"""Módulo de compatibilidade para testes legados.

As funções de orquestração que existiam aqui foram migradas para os use cases
em app/use_cases/ordem_servico/. Este módulo mantém apenas a função
publicar_notificacao para compatibilidade com testes que fazem mock deste path.
"""


def publicar_notificacao(evento: str, dados: dict):
    """Ponte de compatibilidade para testes que fazem mock deste módulo.

    Em produção, a publicação de eventos é feita via EventPublisherInterface
    injetado nos use cases.
    """
    print(f"NOTIFICAÇÃO OS: {evento} - {dados}")
