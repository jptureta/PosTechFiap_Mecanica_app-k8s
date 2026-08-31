from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Cliente:
    nome: str
    cpf_cnpj: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    ativo: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def desativar(self):
        self.ativo = False

    def ativar(self):
        self.ativo = True
