from typing import List, Optional
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.infrastructure.database import Base


class VeiculoModel(Base):
    __tablename__ = "veiculos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    placa: Mapped[str] = mapped_column(String(7), unique=True, nullable=False, index=True)
    marca: Mapped[str] = mapped_column(String(100), nullable=False)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    cliente: Mapped["ClienteModel"] = relationship("ClienteModel", back_populates="veiculos")
    ordens_servico: Mapped[List["OrdemServicoModel"]] = relationship("OrdemServicoModel", back_populates="veiculo", lazy="selectin")
