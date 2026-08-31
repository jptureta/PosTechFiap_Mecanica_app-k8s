from sqlalchemy.orm import Session
from app.infrastructure.database.models.servico_model import ServicoModel as Servico
from app.repositories.base import BaseRepository


class ServicoRepository(BaseRepository[Servico]):
    def __init__(self, db: Session):
        super().__init__(Servico, db)
