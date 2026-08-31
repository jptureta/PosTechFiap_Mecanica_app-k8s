from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Peca:
    nome: str
    preco: Decimal
    descricao: Optional[str] = None
    quantidade_estoque: int = 0
    quantidade_reservada: int = 0
    codigo: Optional[str] = None
    unidade_medida: Optional[str] = None
    estoque_minimo: int = 0
    ativo: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def desativar(self):
        self.ativo = False

    def ativar(self):
        self.ativo = True

    def adicionar_estoque(self, quantidade: int):
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser positiva")
        self.quantidade_estoque += quantidade

    def remover_estoque(self, quantidade: int):
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser positiva")
        if self.quantidade_estoque < quantidade:
            raise ValueError("Estoque insuficiente")
        self.quantidade_estoque -= quantidade
