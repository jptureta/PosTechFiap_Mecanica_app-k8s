"""Módulo de compatibilidade para testes legados.

As funções que existiam aqui foram migradas para os use cases e adapters.
Este módulo mantém apenas a função publicar_notificacao para compatibilidade
com testes que fazem mock deste path.
"""


def publicar_notificacao(evento: str, dados: dict):
    """Ponte de compatibilidade para testes que fazem mock deste módulo."""
    print(f"NOTIFICAÇÃO: {evento} - {dados}")
