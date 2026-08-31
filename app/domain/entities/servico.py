from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Servico:
    nome: str
    preco: Decimal
    descricao: Optional[str] = None
    tempo_estimado_minutos: Optional[int] = None
    ativo: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def desativar(self):
        self.ativo = False

    def ativar(self):
        self.ativo = True
