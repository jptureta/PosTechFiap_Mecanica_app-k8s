from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.domain.entities.ordem_servico import OrdemServico, OrdemServicoServico, OrdemServicoPeca, OrdemServicoHistorico
from app.domain.repositories.ordem_servico_repository_interface import OrdemServicoRepositoryInterface
from app.infrastructure.database.models.ordem_servico_model import OrdemServicoModel, OrdemServicoServicoModel, OrdemServicoPecaModel, OrdemServicoHistoricoModel
from app.domain.enums import StatusOrdemServico


class OrdemServicoRepository(OrdemServicoRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, model: OrdemServicoModel) -> OrdemServico:
        itens_servico = []
        for item in model.itens_servico:
             itens_servico.append(OrdemServicoServico(
                id=item.id,
                servico_id=item.servico_id,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                valor_total=item.valor_total,
                nome_servico=getattr(item.servico, 'nome', None) if hasattr(item, 'servico') else None
             ))

        itens_peca = []
        for item in model.itens_peca:
             itens_peca.append(OrdemServicoPeca(
                id=item.id,
                peca_id=item.peca_id,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                valor_total=item.valor_total,
                nome_peca=getattr(item.peca, 'nome', None) if hasattr(item, 'peca') else None
             ))

        return OrdemServico(
            id=model.id,
            cliente_id=model.cliente_id,
            veiculo_id=model.veiculo_id,
            status=model.status,
            observacoes=model.observacoes,
            valor_total=model.valor_total,
            orcamento_aprovado=model.orcamento_aprovado,
            created_at=model.created_at,
            updated_at=model.updated_at,
            data_finalizacao=model.data_finalizacao,
            data_entrega=model.data_entrega,
            itens_servico=itens_servico,
            itens_peca=itens_peca,
            historico=[
                OrdemServicoHistorico(
                    id=item.id,
                    status_anterior=item.status_anterior,
                    status_novo=item.status_novo,
                    data_alteracao=item.data_alteracao,
                    observacao=item.observacao
                ) for item in model.historico
            ]
        )

    def _to_model(self, entity: OrdemServico) -> OrdemServicoModel:
        model = OrdemServicoModel(
            id=entity.id,
            cliente_id=entity.cliente_id,
            veiculo_id=entity.veiculo_id,
            status=entity.status,
            observacoes=entity.observacoes,
            valor_total=entity.valor_total,
            orcamento_aprovado=entity.orcamento_aprovado,
            data_finalizacao=entity.data_finalizacao,
            data_entrega=entity.data_entrega
        )
        # Notas: Não populamos coleções no _to_model para evitar loops se chamado recursivamente
        # O atualizar/salvar cuida das coleções
        return model

    def salvar(self, ordem: OrdemServico) -> OrdemServico:
        model = self._to_model(ordem)
        
        # Adicionar itens explicitamente
        for item in ordem.itens_servico:
             model.itens_servico.append(OrdemServicoServicoModel(
                servico_id=item.servico_id,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                valor_total=item.valor_total
             ))
        
        for item in ordem.itens_peca:
             model.itens_peca.append(OrdemServicoPecaModel(
                peca_id=item.peca_id,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                valor_total=item.valor_total
             ))

        for item in ordem.historico:
             model.historico.append(OrdemServicoHistoricoModel(
                status_anterior=item.status_anterior,
                status_novo=item.status_novo,
                data_alteracao=item.data_alteracao,
                observacao=item.observacao
             ))

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def buscar_por_id(self, ordem_id: int) -> Optional[OrdemServico]:
        # Tentar buscar do cache da sessão primeiro para garantir que vemos mudanças não commitadas se necessário
        model = self.db.get(OrdemServicoModel, ordem_id)
        if not model:
             # Forçar flush e tentar novamente se houver algo pendente
             self.db.flush()
             model = self.db.get(OrdemServicoModel, ordem_id)
        return self._to_domain(model) if model else None

    def listar_todas(self, skip: int = 0, limit: int = 100, status=None, cliente_id=None) -> List[OrdemServico]:
        stmt = select(OrdemServicoModel).offset(skip).limit(limit)
        if status:
            stmt = stmt.where(OrdemServicoModel.status == status)
        if cliente_id:
            stmt = stmt.where(OrdemServicoModel.cliente_id == cliente_id)
        
        models = self.db.scalars(stmt).unique().all()
        return [self._to_domain(m) for m in models]

    def listar_ativas_ordenadas(self, skip: int = 0, limit: int = 100) -> List[OrdemServico]:
        from sqlalchemy import case

        # Status ativos (exclui Finalizada, Entregue, Cancelada)
        status_ativos = [
            StatusOrdemServico.EM_EXECUCAO,
            StatusOrdemServico.AGUARDANDO_APROVACAO,
            StatusOrdemServico.EM_DIAGNOSTICO,
            StatusOrdemServico.RECEBIDA,
        ]

        # Ordenação de prioridade: Em Execução > Aguardando Aprovação > Diagnóstico > Recebida
        prioridade_status = case(
            (OrdemServicoModel.status == StatusOrdemServico.EM_EXECUCAO, 1),
            (OrdemServicoModel.status == StatusOrdemServico.AGUARDANDO_APROVACAO, 2),
            (OrdemServicoModel.status == StatusOrdemServico.EM_DIAGNOSTICO, 3),
            (OrdemServicoModel.status == StatusOrdemServico.RECEBIDA, 4),
            else_=5,
        )

        stmt = (
            select(OrdemServicoModel)
            .where(OrdemServicoModel.status.in_(status_ativos))
            .order_by(prioridade_status, OrdemServicoModel.created_at.asc())
            .offset(skip)
            .limit(limit)
        )

        models = self.db.scalars(stmt).unique().all()
        return [self._to_domain(m) for m in models]


    def atualizar(self, ordem: OrdemServico) -> OrdemServico:
        existing_model = self.db.get(OrdemServicoModel, ordem.id)
        if not existing_model:
            # Tentar flush se for novo mas com ID (raro mas possível em testes)
            self.db.flush()
            existing_model = self.db.get(OrdemServicoModel, ordem.id)
            if not existing_model: return ordem

        # Atualiza campos básicos
        existing_model.status = ordem.status
        existing_model.observacoes = ordem.observacoes
        existing_model.valor_total = ordem.valor_total
        existing_model.orcamento_aprovado = ordem.orcamento_aprovado
        existing_model.data_finalizacao = ordem.data_finalizacao
        existing_model.data_entrega = ordem.data_entrega

        # Sincronizar Coleções - Remover e Recriar para Sincronizar
        # Limpar existentes via query para garantir cascade/delete
        self.db.query(OrdemServicoServicoModel).filter_by(ordem_servico_id=ordem.id).delete()
        self.db.query(OrdemServicoPecaModel).filter_by(ordem_servico_id=ordem.id).delete()
        self.db.query(OrdemServicoHistoricoModel).filter_by(ordem_servico_id=ordem.id).delete()
        self.db.flush()

        # Re-inserir do domínio
        for item in ordem.itens_servico:
             existing_model.itens_servico.append(OrdemServicoServicoModel(
                servico_id=item.servico_id,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                valor_total=item.valor_total
             ))
        
        for item in ordem.itens_peca:
             existing_model.itens_peca.append(OrdemServicoPecaModel(
                peca_id=item.peca_id,
                quantidade=item.quantidade,
                valor_unitario=item.valor_unitario,
                valor_total=item.valor_total
             ))

        for item in ordem.historico:
             existing_model.historico.append(OrdemServicoHistoricoModel(
                status_anterior=item.status_anterior,
                status_novo=item.status_novo,
                data_alteracao=item.data_alteracao,
                observacao=item.observacao
             ))

        self.db.commit()
        self.db.refresh(existing_model)
        return self._to_domain(existing_model)

    def buscar_pendentes_por_cliente(self, cliente_id: int) -> List[OrdemServico]:
        status_abertos = [
            StatusOrdemServico.RECEBIDA,
            StatusOrdemServico.EM_DIAGNOSTICO,
            StatusOrdemServico.AGUARDANDO_APROVACAO,
            StatusOrdemServico.EM_EXECUCAO,
        ]
        stmt = select(OrdemServicoModel).where(
            OrdemServicoModel.cliente_id == cliente_id,
            OrdemServicoModel.status.in_(status_abertos)
        )
        models = self.db.scalars(stmt).unique().all()
        return [self._to_domain(m) for m in models]
