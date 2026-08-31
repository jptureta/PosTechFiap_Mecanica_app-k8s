from sqlalchemy import select
from sqlalchemy.orm import Session
from app.infrastructure.database.models.ordem_servico_model import OrdemServicoModel
from app.domain.enums import StatusOrdemServico


class ClientePendenciaGateway:
    def __init__(self, db: Session):
        self.db = db

    def possui_pendencias(self, cliente_id: int) -> bool:
        status_abertos = [
            StatusOrdemServico.RECEBIDA,
            StatusOrdemServico.EM_DIAGNOSTICO,
            StatusOrdemServico.AGUARDANDO_APROVACAO,
            StatusOrdemServico.EM_EXECUCAO,
        ]
        stmt = (
            select(OrdemServicoModel)
            .where(OrdemServicoModel.cliente_id == cliente_id, OrdemServicoModel.status.in_(status_abertos))
            .limit(1)
        )
        os_aberta = self.db.scalars(stmt).first()
        return os_aberta is not None
