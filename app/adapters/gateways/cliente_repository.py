from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.domain.entities.cliente import Cliente
from app.domain.repositories.cliente_repository_interface import ClienteRepositoryInterface
from app.infrastructure.database.models.cliente_model import ClienteModel


class ClienteRepository(ClienteRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, model: ClienteModel) -> Cliente:
        return Cliente(
            id=model.id,
            nome=model.nome,
            cpf_cnpj=model.cpf_cnpj,
            email=model.email,
            telefone=model.telefone,
            endereco=model.endereco,
            ativo=model.ativo,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Cliente) -> ClienteModel:
        return ClienteModel(
            id=entity.id,
            nome=entity.nome,
            cpf_cnpj=entity.cpf_cnpj,
            email=entity.email,
            telefone=entity.telefone,
            endereco=entity.endereco,
            ativo=entity.ativo,
        )

    def salvar(self, cliente: Cliente) -> Cliente:
        model = self._to_model(cliente)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def buscar_por_id(self, cliente_id: int) -> Optional[Cliente]:
        model = self.db.get(ClienteModel, cliente_id)
        return self._to_domain(model) if model else None

    def buscar_por_cpf_cnpj(self, cpf_cnpj: str) -> Optional[Cliente]:
        stmt = select(ClienteModel).where(ClienteModel.cpf_cnpj == cpf_cnpj)
        model = self.db.scalars(stmt).first()
        return self._to_domain(model) if model else None

    def listar_todos(self, skip: int = 0, limit: int = 100) -> List[Cliente]:
        stmt = select(ClienteModel).offset(skip).limit(limit)
        models = self.db.scalars(stmt).all()
        return [self._to_domain(m) for m in models]

    def atualizar(self, cliente: Cliente) -> Cliente:
        model = self.db.get(ClienteModel, cliente.id)
        if model:
            model.nome = cliente.nome
            model.email = cliente.email
            model.telefone = cliente.telefone
            model.endereco = cliente.endereco
            model.ativo = cliente.ativo
            self.db.commit()
            self.db.refresh(model)
            return self._to_domain(model)
        return cliente
