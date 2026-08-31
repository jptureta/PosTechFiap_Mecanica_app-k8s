from sqlalchemy.orm import Session
from app.infrastructure.database.models.peca_model import PecaModel as Peca
from app.repositories.base import BaseRepository


class PecaRepository(BaseRepository[Peca]):
    def __init__(self, db: Session):
        super().__init__(Peca, db)
