from decimal import Decimal
from datetime import datetime, timezone
from typing import List
from app.domain.entities.ordem_servico import OrdemServico, OrdemServicoServico, OrdemServicoPeca, OrdemServicoHistorico
from app.domain.repositories.ordem_servico_repository_interface import OrdemServicoRepositoryInterface
from app.domain.repositories.cliente_repository_interface import ClienteRepositoryInterface
from app.domain.repositories.veiculo_repository_interface import VeiculoRepositoryInterface
from app.domain.repositories.servico_repository_interface import ServicoRepositoryInterface
from app.domain.repositories.peca_repository_interface import PecaRepositoryInterface
from app.domain.exceptions.cliente_exceptions import ClienteNaoEncontradoError
from app.domain.exceptions.veiculo_exceptions import VeiculoNaoEncontradoError
from app.domain.exceptions.servico_exceptions import ServicoNaoEncontradoError, ServicoError
from app.domain.exceptions.peca_exceptions import PecaNaoEncontradaError, PecaError
from app.domain.exceptions.ordem_servico_exceptions import OrdemServicoError, OrdemServicoSemItensError
from app.domain.enums import StatusOrdemServico


class CriarOrdemServicoUseCase:
    def __init__(
        self,
        ordem_repo: OrdemServicoRepositoryInterface,
        cliente_repo: ClienteRepositoryInterface,
        veiculo_repo: VeiculoRepositoryInterface,
        servico_repo: ServicoRepositoryInterface,
        peca_repo: PecaRepositoryInterface
    ):
        self.ordem_repo = ordem_repo
        self.cliente_repo = cliente_repo
        self.veiculo_repo = veiculo_repo
        self.servico_repo = servico_repo
        self.peca_repo = peca_repo

    def execute(
        self,
        cliente_id: int,
        veiculo_id: int,
        itens_servico_req: List[dict],
        itens_peca_req: List[dict],
        observacoes: str = None
    ) -> OrdemServico:
        # Validar Cliente
        cliente = self.cliente_repo.buscar_por_id(cliente_id)
        if not cliente:
            raise ClienteNaoEncontradoError()
        if not cliente.ativo:
            raise OrdemServicoError("Cliente inativo")
        
        # Validar Veículo
        veiculo = self.veiculo_repo.buscar_por_id(veiculo_id)
        if not veiculo:
            raise VeiculoNaoEncontradoError("Veículo não encontrado")
        
        if veiculo.cliente_id != cliente_id:
            raise OrdemServicoError("Veículo não pertence ao cliente")
            
        if not veiculo.ativo:
            raise VeiculoNaoEncontradoError("Veículo inativo")

        ordem = OrdemServico(
            cliente_id=cliente_id,
            veiculo_id=veiculo_id,
            observacoes=observacoes,
            status=StatusOrdemServico.RECEBIDA
        )

        # Processar Serviços
        for item in itens_servico_req:
            servico = self.servico_repo.buscar_por_id(item["servico_id"])
            if not servico:
                raise ServicoNaoEncontradoError(f"Serviço {item['servico_id']} não encontrado")
            if not servico.ativo:
                raise ServicoError("Serviço inativo")
            
            valor_unitario = Decimal(str(item.get("valor_unitario") or servico.preco))
            quantidade = item["quantidade"]
            ordem.itens_servico.append(OrdemServicoServico(
                servico_id=servico.id,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total=valor_unitario * quantidade,
                nome_servico=servico.nome
            ))

        # Processar Peças
        for item in itens_peca_req:
            peca = self.peca_repo.buscar_por_id(item["peca_id"])
            if not peca:
                raise PecaNaoEncontradaError(f"Peça {item['peca_id']} não encontrada")
            if not peca.ativo:
                raise PecaError("Peça inativa")
            
            valor_unitario = Decimal(str(item.get("valor_unitario") or peca.preco))
            quantidade = item["quantidade"]
            
            ordem.itens_peca.append(OrdemServicoPeca(
                peca_id=peca.id,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total=valor_unitario * quantidade,
                nome_peca=peca.nome
            ))

        ordem.calcular_total()
        
        # Registrar Histórico Inicial
        ordem.historico.append(OrdemServicoHistorico(
            status_anterior=None,
            status_novo=StatusOrdemServico.RECEBIDA,
            data_alteracao=datetime.now(timezone.utc),
            observacao="Ordem de serviço aberta"
        ))

        return self.ordem_repo.salvar(ordem)
