from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Veiculo:
    cliente_id: int
    placa: str
    marca: str
    modelo: str
    ano: int
    cor: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def desativar(self):
        self.ativo = False

    def ativar(self):
        self.ativo = True
