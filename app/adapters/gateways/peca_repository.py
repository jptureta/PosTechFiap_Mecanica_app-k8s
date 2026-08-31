from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.domain.entities.peca import Peca
from app.domain.repositories.peca_repository_interface import PecaRepositoryInterface
from app.infrastructure.database.models.peca_model import PecaModel


class PecaRepository(PecaRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, model: PecaModel) -> Peca:
        return Peca(
            id=model.id,
            codigo=model.codigo,
            nome=model.nome,
            descricao=model.descricao,
            unidade_medida=model.unidade_medida,
            preco=model.preco,
            quantidade_estoque=model.quantidade_estoque,
            quantidade_reservada=model.quantidade_reservada,
            estoque_minimo=model.estoque_minimo,
            ativo=model.ativo,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Peca) -> PecaModel:
        return PecaModel(
            id=entity.id,
            codigo=entity.codigo,
            nome=entity.nome,
            descricao=entity.descricao,
            unidade_medida=entity.unidade_medida,
            preco=entity.preco,
            quantidade_estoque=entity.quantidade_estoque,
            quantidade_reservada=entity.quantidade_reservada,
            estoque_minimo=entity.estoque_minimo,
            ativo=entity.ativo,
        )

    def salvar(self, peca: Peca) -> Peca:
        model = self._to_model(peca)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def buscar_por_id(self, peca_id: int) -> Optional[Peca]:
        model = self.db.get(PecaModel, peca_id)
        return self._to_domain(model) if model else None

    def listar_todas(self, skip: int = 0, limit: int = 100) -> List[Peca]:
        stmt = select(PecaModel).offset(skip).limit(limit)
        models = self.db.scalars(stmt).all()
        return [self._to_domain(m) for m in models]

    def atualizar(self, peca: Peca) -> Peca:
        model = self.db.get(PecaModel, peca.id)
        if model:
            model.codigo = peca.codigo
            model.nome = peca.nome
            model.descricao = peca.descricao
            model.unidade_medida = peca.unidade_medida
            model.preco = peca.preco
            model.quantidade_estoque = peca.quantidade_estoque
            model.quantidade_reservada = peca.quantidade_reservada
            model.estoque_minimo = peca.estoque_minimo
            model.ativo = peca.ativo
            self.db.commit()
            self.db.refresh(model)
            return self._to_domain(model)
        return peca

    def deletar(self, peca_id: int) -> None:
        model = self.db.get(PecaModel, peca_id)
        if model:
            self.db.delete(model)
            self.db.commit()
