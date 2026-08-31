from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.domain.entities.veiculo import Veiculo
from app.domain.repositories.veiculo_repository_interface import VeiculoRepositoryInterface
from app.infrastructure.database.models.veiculo_model import VeiculoModel


class VeiculoRepository(VeiculoRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, model: VeiculoModel) -> Veiculo:
        return Veiculo(
            id=model.id,
            cliente_id=model.cliente_id,
            placa=model.placa,
            marca=model.marca,
            modelo=model.modelo,
            ano=model.ano,
            cor=model.cor,
            observacoes=model.observacoes,
            ativo=model.ativo,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Veiculo) -> VeiculoModel:
        return VeiculoModel(
            id=entity.id,
            cliente_id=entity.cliente_id,
            placa=entity.placa,
            marca=entity.marca,
            modelo=entity.modelo,
            ano=entity.ano,
            cor=entity.cor,
            observacoes=entity.observacoes,
            ativo=entity.ativo,
        )

    def salvar(self, veiculo: Veiculo) -> Veiculo:
        model = self._to_model(veiculo)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def buscar_por_id(self, veiculo_id: int) -> Optional[Veiculo]:
        model = self.db.get(VeiculoModel, veiculo_id)
        return self._to_domain(model) if model else None

    def buscar_por_placa(self, placa: str) -> Optional[Veiculo]:
        stmt = select(VeiculoModel).where(VeiculoModel.placa == placa)
        model = self.db.scalars(stmt).first()
        return self._to_domain(model) if model else None

    def buscar_por_cliente(self, cliente_id: int) -> List[Veiculo]:
        stmt = select(VeiculoModel).where(VeiculoModel.cliente_id == cliente_id)
        models = self.db.scalars(stmt).all()
        return [self._to_domain(m) for m in models]

    def listar_todos(self, skip: int = 0, limit: int = 100) -> List[Veiculo]:
        stmt = select(VeiculoModel).offset(skip).limit(limit)
        models = self.db.scalars(stmt).all()
        return [self._to_domain(m) for m in models]

    def atualizar(self, veiculo: Veiculo) -> Veiculo:
        model = self.db.get(VeiculoModel, veiculo.id)
        if model:
            model.cliente_id = veiculo.cliente_id
            model.placa = veiculo.placa
            model.marca = veiculo.marca
            model.modelo = veiculo.modelo
            model.ano = veiculo.ano
            model.cor = veiculo.cor
            model.observacoes = veiculo.observacoes
            model.ativo = veiculo.ativo
            self.db.commit()
            self.db.refresh(model)
            return self._to_domain(model)
        return veiculo

    def deletar(self, veiculo_id: int) -> None:
        model = self.db.get(VeiculoModel, veiculo_id)
        if model:
            self.db.delete(model)
            self.db.commit()
