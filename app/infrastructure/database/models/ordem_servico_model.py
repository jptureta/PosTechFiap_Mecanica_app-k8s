from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, Numeric, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.infrastructure.database import Base
from app.domain.enums import StatusOrdemServico


class OrdemServicoModel(Base):
    __tablename__ = "ordens_servico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    veiculo_id: Mapped[int] = mapped_column(Integer, ForeignKey("veiculos.id"), nullable=False, index=True)
    status: Mapped[StatusOrdemServico] = mapped_column(
        Enum(
            StatusOrdemServico,
            name="status_ordem_servico",
            values_callable=lambda enum: [m.value for m in enum],
        ),
        default=StatusOrdemServico.RECEBIDA,
        nullable=False,
        index=True,
    )
    observacoes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    orcamento_aprovado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    data_finalizacao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data_entrega: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    cliente: Mapped["ClienteModel"] = relationship("ClienteModel", back_populates="ordens_servico")
    veiculo: Mapped["VeiculoModel"] = relationship("VeiculoModel", back_populates="ordens_servico")
    itens_servico: Mapped[List["OrdemServicoServicoModel"]] = relationship("OrdemServicoServicoModel", back_populates="ordem_servico", lazy="selectin", cascade="all, delete-orphan")
    itens_peca: Mapped[List["OrdemServicoPecaModel"]] = relationship("OrdemServicoPecaModel", back_populates="ordem_servico", lazy="selectin", cascade="all, delete-orphan")
    historico: Mapped[List["OrdemServicoHistoricoModel"]] = relationship("OrdemServicoHistoricoModel", back_populates="ordem_servico", lazy="selectin", cascade="all, delete-orphan")


class OrdemServicoServicoModel(Base):
    __tablename__ = "ordens_servico_servicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ordem_servico_id: Mapped[int] = mapped_column(Integer, ForeignKey("ordens_servico.id"), nullable=False, index=True)
    servico_id: Mapped[int] = mapped_column(Integer, ForeignKey("servicos.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    ordem_servico: Mapped["OrdemServicoModel"] = relationship("OrdemServicoModel", back_populates="itens_servico")
    servico: Mapped["ServicoModel"] = relationship("ServicoModel", lazy="selectin")


class OrdemServicoPecaModel(Base):
    __tablename__ = "ordens_servico_pecas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ordem_servico_id: Mapped[int] = mapped_column(Integer, ForeignKey("ordens_servico.id"), nullable=False, index=True)
    peca_id: Mapped[int] = mapped_column(Integer, ForeignKey("pecas.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    ordem_servico: Mapped["OrdemServicoModel"] = relationship("OrdemServicoModel", back_populates="itens_peca")
    peca: Mapped["PecaModel"] = relationship("PecaModel", lazy="selectin")


class OrdemServicoHistoricoModel(Base):
    __tablename__ = "ordens_servico_historico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ordem_servico_id: Mapped[int] = mapped_column(Integer, ForeignKey("ordens_servico.id"), nullable=False, index=True)
    status_anterior: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status_novo: Mapped[str] = mapped_column(String(50), nullable=False)
    observacao: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    data_alteracao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ordem_servico: Mapped["OrdemServicoModel"] = relationship("OrdemServicoModel", back_populates="historico")
