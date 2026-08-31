from pydantic import BaseModel, field_validator
from datetime import datetime
from decimal import Decimal


class PecaBase(BaseModel):
    codigo: str | None = None
    nome: str
    descricao: str | None = None
    unidade_medida: str | None = None
    preco: Decimal
    quantidade_estoque: int
    estoque_minimo: int = 0

    @field_validator("preco")
    @classmethod
    def preco_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Preço deve ser positivo")
        return v

    @field_validator("quantidade_estoque")
    @classmethod
    def estoque_nao_negativo(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantidade em estoque não pode ser negativa")
        return v

    @field_validator("estoque_minimo")
    @classmethod
    def estoque_minimo_nao_negativo(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Estoque mínimo não pode ser negativo")
        return v


class PecaCreate(PecaBase):
    pass


class PecaUpdate(BaseModel):
    codigo: str | None = None
    nome: str | None = None
    descricao: str | None = None
    unidade_medida: str | None = None
    preco: Decimal | None = None
    quantidade_estoque: int | None = None
    estoque_minimo: int | None = None
    ativo: bool | None = None

    @field_validator("preco")
    @classmethod
    def preco_positivo(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Preço deve ser positivo")
        return v

    @field_validator("quantidade_estoque")
    @classmethod
    def estoque_nao_negativo(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Quantidade em estoque não pode ser negativa")
        return v

    @field_validator("estoque_minimo")
    @classmethod
    def estoque_minimo_nao_negativo(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Estoque mínimo não pode ser negativo")
        return v


class AjusteEstoqueRequest(BaseModel):
    quantidade_entrada: int

    @field_validator("quantidade_entrada")
    @classmethod
    def quantidade_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantidade de entrada deve ser positiva")
        return v


class PecaResponse(PecaBase):
    id: int
    quantidade_reservada: int
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
