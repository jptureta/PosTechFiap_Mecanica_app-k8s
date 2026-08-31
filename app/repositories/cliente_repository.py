from sqlalchemy.orm import Session
from sqlalchemy import select
from app.infrastructure.database.models.cliente_model import ClienteModel as Cliente
from app.repositories.base import BaseRepository


class ClienteRepository(BaseRepository[Cliente]):
    def __init__(self, db: Session):
        super().__init__(Cliente, db)

    def get_by_cpf_cnpj(self, cpf_cnpj: str) -> Cliente | None:
        stmt = select(Cliente).where(Cliente.cpf_cnpj == cpf_cnpj)
        return self.db.scalars(stmt).first()
