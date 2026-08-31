from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.domain.entities.servico import Servico
from app.domain.repositories.servico_repository_interface import ServicoRepositoryInterface
from app.infrastructure.database.models.servico_model import ServicoModel


class ServicoRepository(ServicoRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, model: ServicoModel) -> Servico:
        return Servico(
            id=model.id,
            nome=model.nome,
            descricao=model.descricao,
            preco=model.preco,
            tempo_estimado_minutos=model.tempo_estimado_minutos,
            ativo=model.ativo,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Servico) -> ServicoModel:
        return ServicoModel(
            id=entity.id,
            nome=entity.nome,
            descricao=entity.descricao,
            preco=entity.preco,
            tempo_estimado_minutos=entity.tempo_estimado_minutos,
            ativo=entity.ativo,
        )

    def salvar(self, servico: Servico) -> Servico:
        model = self._to_model(servico)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def buscar_por_id(self, servico_id: int) -> Optional[Servico]:
        model = self.db.get(ServicoModel, servico_id)
        return self._to_domain(model) if model else None

    def listar_todos(self, skip: int = 0, limit: int = 100) -> List[Servico]:
        stmt = select(ServicoModel).offset(skip).limit(limit)
        models = self.db.scalars(stmt).all()
        return [self._to_domain(m) for m in models]

    def atualizar(self, servico: Servico) -> Servico:
        model = self.db.get(ServicoModel, servico.id)
        if model:
            model.nome = servico.nome
            model.descricao = servico.descricao
            model.preco = servico.preco
            model.tempo_estimado_minutos = servico.tempo_estimado_minutos
            model.ativo = servico.ativo
            self.db.commit()
            self.db.refresh(model)
            return self._to_domain(model)
        return servico

    def deletar(self, servico_id: int) -> None:
        model = self.db.get(ServicoModel, servico_id)
        if model:
            self.db.delete(model)
            self.db.commit()
