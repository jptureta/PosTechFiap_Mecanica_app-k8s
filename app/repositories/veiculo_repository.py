from sqlalchemy.orm import Session
from app.infrastructure.database.models.veiculo_model import VeiculoModel as Veiculo
from app.repositories.base import BaseRepository


class VeiculoRepository(BaseRepository[Veiculo]):
    def __init__(self, db: Session):
        super().__init__(Veiculo, db)

    def get_by_placa(self, placa: str) -> Veiculo | None:
        from sqlalchemy import select
        stmt = select(Veiculo).where(Veiculo.placa == placa)
        return self.db.scalars(stmt).first()

    def get_by_cliente(self, cliente_id: int) -> list[Veiculo]:
        from sqlalchemy import select
        stmt = select(Veiculo).where(Veiculo.cliente_id == cliente_id)
        return list(self.db.scalars(stmt).all())
