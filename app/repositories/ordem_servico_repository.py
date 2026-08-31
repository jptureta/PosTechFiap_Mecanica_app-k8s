from sqlalchemy.orm import Session
from app.infrastructure.database.models.ordem_servico_model import OrdemServicoModel as OrdemServico
from app.repositories.base import BaseRepository


class OrdemServicoRepository(BaseRepository[OrdemServico]):
    def __init__(self, db: Session):
        super().__init__(OrdemServico, db)
