from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from app.domain.enums import StatusOrdemServico


class ItemServicoCreate(BaseModel):
    servico_id: int
    quantidade: int = 1


class ItemServicoResponse(BaseModel):
    id: int
    servico_id: int
    quantidade: int
    valor_unitario: Decimal
    valor_total: Decimal

    model_config = {"from_attributes": True}


class ItemPecaCreate(BaseModel):
    peca_id: int
    quantidade: int = 1


class ItemPecaResponse(BaseModel):
    id: int
    peca_id: int
    quantidade: int
    valor_unitario: Decimal
    valor_total: Decimal

    model_config = {"from_attributes": True}



class HistoricoResponse(BaseModel):
    id: int
    status_anterior: str | None
    status_novo: str
    observacao: str | None
    data_alteracao: datetime

    model_config = {"from_attributes": True}



class OrdemServicoCreate(BaseModel):
    cliente_id: int
    veiculo_id: int
    observacoes: str | None = None
    itens_servico: list[ItemServicoCreate] | None = None
    itens_peca: list[ItemPecaCreate] | None = None


class OrdemServicoUpdate(BaseModel):
    observacoes: str | None = None


class AlterarStatusRequest(BaseModel):
    novo_status: StatusOrdemServico
    observacao: str | None = None


class AdicionarItemServicoRequest(BaseModel):
    servico_id: int
    quantidade: int = 1


class AdicionarItemPecaRequest(BaseModel):
    peca_id: int
    quantidade: int = 1


class OrdemServicoResponse(BaseModel):
    id: int
    cliente_id: int
    veiculo_id: int
    status: StatusOrdemServico
    observacoes: str | None
    valor_total: Decimal
    orcamento_aprovado: bool
    created_at: datetime
    updated_at: datetime
    data_finalizacao: datetime | None
    data_entrega: datetime | None
    itens_servico: list[ItemServicoResponse]
    itens_peca: list[ItemPecaResponse]
    historico: list[HistoricoResponse]

    model_config = {"from_attributes": True}


class OrdemServicoResumo(BaseModel):
    id: int
    cliente_id: int
    veiculo_id: int
    status: StatusOrdemServico
    valor_total: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class TempoMedioResponse(BaseModel):
    tempo_medio_minutos: float
    total_ordens_finalizadas: int
