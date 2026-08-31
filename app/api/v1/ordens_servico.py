from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.infrastructure.database import get_db
from app.schemas.ordem_servico import (
    OrdemServicoCreate, OrdemServicoUpdate, OrdemServicoResponse, 
    AlterarStatusRequest, AdicionarItemServicoRequest, AdicionarItemPecaRequest,
    OrdemServicoResumo, TempoMedioResponse
)
from app.api.deps import get_current_user
from app.domain.enums import StatusOrdemServico

# Repositories (Adapters)
from app.adapters.gateways.ordem_servico_repository import OrdemServicoRepository
from app.adapters.gateways.cliente_repository import ClienteRepository
from app.adapters.gateways.veiculo_repository import VeiculoRepository
from app.adapters.gateways.servico_repository import ServicoRepository
from app.adapters.gateways.peca_repository import PecaRepository

# Notification Adapter
from app.adapters.gateways.email_notificacao_service import EmailNotificacaoService

# Use Cases
from app.use_cases.ordem_servico.criar_ordem_servico import CriarOrdemServicoUseCase
from app.use_cases.ordem_servico.buscar_ordem_servico import BuscarOrdemServicoUseCase, ListarOrdensServicoUseCase, ListarOrdensServicoAtivasUseCase
from app.use_cases.ordem_servico.atualizar_ordem_servico import AtualizarStatusOrdemServicoUseCase, AprovarOrcamentoUseCase, RecusarOrcamentoUseCase
from app.use_cases.ordem_servico.gerenciar_itens import AdicionarItemOrdemServicoUseCase, RemoverItemOrdemServicoUseCase
from app.use_cases.ordem_servico.acompanhar_ordem_servico import AcompanharOrdemServicoUseCase
from app.use_cases.ordem_servico.relatorios_ordem_servico import RelatoriosOrdemServicoUseCase

# Exceptions
from app.domain.exceptions.ordem_servico_exceptions import OrdemServicoError, OrdemServicoNaoEncontradaError, TransicaoStatusInvalidaError, OrdemServicoSemItensError
from app.domain.exceptions.cliente_exceptions import ClienteNaoEncontradoError
from app.domain.exceptions.veiculo_exceptions import VeiculoNaoEncontradoError
from app.domain.exceptions.servico_exceptions import ServicoNaoEncontradoError, ServicoError
from app.domain.exceptions.peca_exceptions import PecaNaoEncontradaError, PecaError

router = APIRouter(prefix="/ordens-servico", tags=["Ordens de Serviço"])


def handle_os_error(e: Exception):
    if isinstance(e, (OrdemServicoNaoEncontradaError, ClienteNaoEncontradoError, VeiculoNaoEncontradoError, ServicoNaoEncontradoError, PecaNaoEncontradaError)):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, (TransicaoStatusInvalidaError, OrdemServicoSemItensError, PecaError, OrdemServicoError, ServicoError)):
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=500, detail=f"Erro interno no domínio de ordens de serviço: {str(e)}")


@router.post("/", response_model=OrdemServicoResponse, status_code=201, dependencies=[Depends(get_current_user)])
def criar_ordem_servico(dados: OrdemServicoCreate, db: Session = Depends(get_db)):
    """Abre uma nova ordem de serviço."""
    repo = OrdemServicoRepository(db)
    use_case = CriarOrdemServicoUseCase(
        repo,
        ClienteRepository(db),
        VeiculoRepository(db),
        ServicoRepository(db),
        PecaRepository(db)
    )
    try:
        return use_case.execute(
            cliente_id=dados.cliente_id,
            veiculo_id=dados.veiculo_id,
            itens_servico_req=[item.model_dump() for item in (dados.itens_servico or [])],
            itens_peca_req=[item.model_dump() for item in (dados.itens_peca or [])],
            observacoes=dados.observacoes
        )
    except Exception as e:
        handle_os_error(e)


@router.get("/", response_model=List[OrdemServicoResponse], dependencies=[Depends(get_current_user)])
def listar_ordens_servico(
    status: Optional[StatusOrdemServico] = None,
    cliente_id: Optional[int] = None,
    incluir_finalizadas: bool = Query(False, description="Se True, inclui OS finalizadas/entregues/canceladas e desativa a ordenação por prioridade."),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lista ordens de serviço ativas com ordenação por prioridade de status.
    
    Ordenação padrão: Em Execução > Aguardando Aprovação > Diagnóstico > Recebida.
    Dentro de cada status, as mais antigas aparecem primeiro.
    OS com status Finalizada, Entregue e Cancelada são excluídas por padrão.
    
    Utilizar incluir_finalizadas=true para listar todas as OS sem filtro de status ativo.
    """
    repo = OrdemServicoRepository(db)

    # Se há filtro explícito de status ou cliente, ou se incluir_finalizadas=True,
    # usa a listagem legada sem ordenação de prioridade
    if incluir_finalizadas or status or cliente_id:
        use_case = ListarOrdensServicoUseCase(repo)
        return use_case.execute(skip=skip, limit=limit, status=status, cliente_id=cliente_id)

    # Comportamento padrão: listagem ativa com ordenação por prioridade
    use_case = ListarOrdensServicoAtivasUseCase(repo)
    return use_case.execute(skip=skip, limit=limit)


#@router.get("/relatorios/tempo-medio", response_model=TempoMedioResponse, dependencies=[Depends(get_current_user)])
@router.get("/tempo-medio", response_model=TempoMedioResponse, dependencies=[Depends(get_current_user)])
def calcular_tempo_medio(db: Session = Depends(get_db)):
    """Calcula o tempo médio de execução das ordens finalizadas."""
    repo = OrdemServicoRepository(db)
    use_case = RelatoriosOrdemServicoUseCase(repo)
    return use_case.calcular_tempo_medio_execucao()


@router.get("/cliente/{cliente_id}", response_model=List[OrdemServicoResponse], dependencies=[Depends(get_current_user)])
def buscar_ordens_por_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Busca todas as ordens de serviço de um cliente."""
    repo = OrdemServicoRepository(db)
    use_case = ListarOrdensServicoUseCase(repo)
    return use_case.execute(cliente_id=cliente_id)


@router.get("/acompanhar/{ordem_id}", response_model=OrdemServicoResponse)
def acompanhar_ordem_servico(ordem_id: int, cpf_cnpj: str = Query(...), db: Session = Depends(get_db)):
    """Acompanhamento público de uma ordem de serviço por ID e validação de CPF/CNPJ."""
    ordem_repo = OrdemServicoRepository(db)
    cliente_repo = ClienteRepository(db)
    use_case = AcompanharOrdemServicoUseCase(ordem_repo, cliente_repo)
    try:
        return use_case.por_id_e_cpf_cnpj(ordem_id, cpf_cnpj)
    except OrdemServicoNaoEncontradaError:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    except ClienteNaoEncontradoError:
        raise HTTPException(status_code=403, detail="Acesso negado: CPF/CNPJ inválido para esta ordem de serviço")
    except Exception as e:
        handle_os_error(e)


@router.get("/{ordem_id}", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def buscar_ordem_servico(ordem_id: int, db: Session = Depends(get_db)):
    """Busca os detalhes de uma ordem de serviço."""
    repo = OrdemServicoRepository(db)
    use_case = BuscarOrdemServicoUseCase(repo)
    try:
        return use_case.execute(ordem_id)
    except Exception as e:
        handle_os_error(e)


@router.patch("/{ordem_id}/status", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def atualizar_status(ordem_id: int, dados: AlterarStatusRequest, db: Session = Depends(get_db)):
    """Atualiza o status de uma ordem de serviço com notificação via e-mail."""
    repo = OrdemServicoRepository(db)
    notificacao = EmailNotificacaoService()
    use_case = AtualizarStatusOrdemServicoUseCase(repo, PecaRepository(db), notificacao_service=notificacao)
    try:
        return use_case.execute(ordem_id, dados.novo_status, dados.observacao)
    except Exception as e:
        handle_os_error(e)


@router.post("/{ordem_id}/aprovar", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
@router.post("/{ordem_id}/aprovar-orcamento", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def aprovar_orcamento(ordem_id: int, db: Session = Depends(get_db)):
    """Aprova o orçamento de uma ordem de serviço."""
    repo = OrdemServicoRepository(db)
    notificacao = EmailNotificacaoService()
    use_case = AprovarOrcamentoUseCase(repo, PecaRepository(db), notificacao_service=notificacao)
    try:
        return use_case.execute(ordem_id)
    except Exception as e:
        handle_os_error(e)


@router.post("/{ordem_id}/recusar", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def recusar_orcamento(ordem_id: int, db: Session = Depends(get_db)):
    """Recusa o orçamento de uma ordem de serviço."""
    repo = OrdemServicoRepository(db)
    notificacao = EmailNotificacaoService()
    use_case = RecusarOrcamentoUseCase(repo, notificacao_service=notificacao)
    try:
        return use_case.execute(ordem_id)
    except Exception as e:
        handle_os_error(e)


@router.post("/{ordem_id}/servicos", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def adicionar_servico(ordem_id: int, dados: AdicionarItemServicoRequest, db: Session = Depends(get_db)):
    """Adiciona um serviço à ordem de serviço."""
    repo = OrdemServicoRepository(db)
    use_case = AdicionarItemOrdemServicoUseCase(repo, ServicoRepository(db), PecaRepository(db))
    try:
        return use_case.adicionar_servico(ordem_id, dados.servico_id, dados.quantidade)
    except Exception as e:
        handle_os_error(e)


@router.post("/{ordem_id}/pecas", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def adicionar_peca(ordem_id: int, dados: AdicionarItemPecaRequest, db: Session = Depends(get_db)):
    """Adiciona uma peça à ordem de serviço."""
    repo = OrdemServicoRepository(db)
    use_case = AdicionarItemOrdemServicoUseCase(repo, ServicoRepository(db), PecaRepository(db))
    try:
        return use_case.adicionar_peca(ordem_id, dados.peca_id, dados.quantidade)
    except Exception as e:
        handle_os_error(e)


@router.delete("/{ordem_id}/servicos/{servico_id}", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def remover_servico(ordem_id: int, servico_id: int, db: Session = Depends(get_db)):
    """Remove um serviço da ordem de serviço."""
    repo = OrdemServicoRepository(db)
    use_case = RemoverItemOrdemServicoUseCase(repo)
    try:
        return use_case.remover_servico(ordem_id, servico_id)
    except Exception as e:
        handle_os_error(e)


@router.delete("/{ordem_id}/pecas/{peca_id}", response_model=OrdemServicoResponse, dependencies=[Depends(get_current_user)])
def remover_peca(ordem_id: int, peca_id: int, db: Session = Depends(get_db)):
    """Remove uma peça da ordem de serviço."""
    repo = OrdemServicoRepository(db)
    use_case = RemoverItemOrdemServicoUseCase(repo, PecaRepository(db))
    try:
        return use_case.remover_peca(ordem_id, peca_id)
    except Exception as e:
        handle_os_error(e)
