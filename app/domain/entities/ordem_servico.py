from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from app.domain.enums import StatusOrdemServico


@dataclass
class OrdemServicoServico:
    servico_id: int
    quantidade: int
    valor_unitario: Decimal
    valor_total: Decimal
    id: Optional[int] = None
    nome_servico: Optional[str] = None


@dataclass
class OrdemServicoPeca:
    peca_id: int
    quantidade: int
    valor_unitario: Decimal
    valor_total: Decimal
    id: Optional[int] = None
    nome_peca: Optional[str] = None


@dataclass
class OrdemServicoHistorico:
    status_anterior: Optional[str]
    status_novo: str
    data_alteracao: datetime
    observacao: Optional[str] = None
    id: Optional[int] = None


@dataclass
class OrdemServico:
    cliente_id: int
    veiculo_id: int
    status: StatusOrdemServico = StatusOrdemServico.RECEBIDA
    observacoes: Optional[str] = None
    valor_total: Decimal = Decimal("0.00")
    orcamento_aprovado: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    data_finalizacao: Optional[datetime] = None
    data_entrega: Optional[datetime] = None

    itens_servico: List[OrdemServicoServico] = field(default_factory=list)
    itens_peca: List[OrdemServicoPeca] = field(default_factory=list)
    historico: List[OrdemServicoHistorico] = field(default_factory=list)

    def calcular_total(self):
        total_servicos = sum(item.valor_total for item in self.itens_servico)
        total_pecas = sum(item.valor_total for item in self.itens_peca)
        self.valor_total = total_servicos + total_pecas

    def pode_alterar_status(self, novo_status: StatusOrdemServico) -> bool:
        from app.domain.enums import TRANSICOES_VALIDAS
        return novo_status in TRANSICOES_VALIDAS.get(self.status, [])

    def aprovar_orcamento(self):
        self.orcamento_aprovado = True
