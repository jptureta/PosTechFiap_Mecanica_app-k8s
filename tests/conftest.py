"""
Setup mínimo de ambiente para a suíte de testes.

1. Define as variáveis de ambiente obrigatórias (mesma coisa que a esteira
   faz copiando .env antes do pytest). Fica antes de qualquer `import app.*`
   para que `Settings()` carregue sem estourar.
2. Importa TODOS os modelos SQLAlchemy. Isso garante que, quando o primeiro
   teste instanciar uma classe mapeada (ex.: `Usuario()`), a configuração
   automática dos mappers consegue resolver as `relationship("...")` que
   apontam para outros models por nome.

Valores fixos e óbvios de teste. NUNCA use estes valores em ambiente
compartilhado.
"""

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-1234567890")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")

os.environ.setdefault("DB_USER", "oficina")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "oficina_test")

os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

os.environ.setdefault("WEBHOOK_API_KEY", "test-webhook-key")
os.environ.setdefault("APP_ENV", "test")


# Registra todos os models no metadata do SQLAlchemy antes que qualquer
# teste instancie uma classe mapeada. Sem isto, `Usuario()` num teste
# unitário dispara a configuração dos mappers e falha ao resolver a
# `relationship("VeiculoModel")` do ClienteModel, porque o módulo do
# VeiculoModel ainda não teria sido importado.
from app.infrastructure.database.models import (  # noqa: E402, F401
    cliente_model,
    ordem_servico_model,
    peca_model,
    servico_model,
    veiculo_model,
)
