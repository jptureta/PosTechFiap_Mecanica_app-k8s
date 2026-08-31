from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.schemas.peca import PecaCreate, PecaUpdate, PecaResponse, AjusteEstoqueRequest
from app.api.deps import get_current_user
from app.adapters.gateways.peca_repository import PecaRepository
from app.use_cases.peca.criar_peca import CriarPecaUseCase
from app.use_cases.peca.buscar_peca import BuscarPecaUseCase, ListarPecasUseCase
from app.use_cases.peca.atualizar_peca import AtualizarPecaUseCase, DeletarPecaUseCase
from app.domain.exceptions.peca_exceptions import PecaError, PecaNaoEncontradaError, PecaPrecoInvalidoError
from app.services import peca_service

router = APIRouter(prefix="/pecas", tags=["Peças"])


def handle_peca_error(e: PecaError):
    if isinstance(e, PecaNaoEncontradaError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, PecaPrecoInvalidoError):
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=500, detail="Erro interno no domínio de peças")


@router.post("/", response_model=PecaResponse, status_code=201, dependencies=[Depends(get_current_user)])
def criar_peca(dados: PecaCreate, db: Session = Depends(get_db)):
    """Cria uma nova peça."""
    repo = PecaRepository(db)
    use_case = CriarPecaUseCase(repo)
    try:
        peca = use_case.execute(
            nome=dados.nome,
            preco=dados.preco,
            descricao=dados.descricao,
            quantidade_estoque=dados.quantidade_estoque,
            codigo=dados.codigo,
            unidade_medida=dados.unidade_medida,
            estoque_minimo=dados.estoque_minimo
        )
        # Manter compatibilidade com testes que verificam publicação de eventos
        peca_service.publicar_notificacao("PecaCadastrada", {"id": peca.id, "nome": peca.nome})
        if peca.quantidade_estoque > 0:
             peca_service.publicar_notificacao("EstoqueReposto", {"id": peca.id, "quantidade": peca.quantidade_estoque})
        
        return peca
    except PecaError as e:
        handle_peca_error(e)


@router.get("/", response_model=list[PecaResponse], dependencies=[Depends(get_current_user)])
def listar_pecas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Lista todas as peças com paginação."""
    repo = PecaRepository(db)
    use_case = ListarPecasUseCase(repo)
    pecas = use_case.execute(skip=skip, limit=limit)
    if apenas_ativos:
        pecas = [p for p in pecas if p.ativo]
    return pecas


@router.get("/{peca_id}", response_model=PecaResponse, dependencies=[Depends(get_current_user)])
def buscar_peca(peca_id: int, db: Session = Depends(get_db)):
    """Busca uma peça pelo ID."""
    repo = PecaRepository(db)
    use_case = BuscarPecaUseCase(repo)
    try:
        return use_case.execute(peca_id)
    except PecaError as e:
        handle_peca_error(e)


@router.put("/{peca_id}", response_model=PecaResponse, dependencies=[Depends(get_current_user)])
def atualizar_peca(peca_id: int, dados: PecaUpdate, db: Session = Depends(get_db)):
    """Atualiza dados de uma peça."""
    repo = PecaRepository(db)
    use_case = AtualizarPecaUseCase(repo)
    try:
        return use_case.execute(peca_id, dados.model_dump(exclude_unset=True))
    except PecaError as e:
        handle_peca_error(e)


@router.patch("/{peca_id}/quantidade", response_model=PecaResponse, dependencies=[Depends(get_current_user)])
def ajustar_estoque(peca_id: int, dados: AjusteEstoqueRequest, db: Session = Depends(get_db)):
    """Ajusta o estoque de uma peça (entrada)."""
    repo = PecaRepository(db)
    use_case = AtualizarPecaUseCase(repo)
    try:
        peca = repo.buscar_por_id(peca_id)
        if not peca:
            raise PecaNaoEncontradaError()
        peca.adicionar_estoque(dados.quantidade_entrada)
        
        # Publicar evento de reposição
        peca_service.publicar_notificacao("EstoqueReposto", {"id": peca.id, "quantidade": dados.quantidade_entrada})
        
        # Check for stock alert (as expected by tests)
        if peca.quantidade_estoque <= peca.estoque_minimo:
             peca_service.publicar_notificacao("AlertaDeEstoqueEmitido", {"id": peca.id, "estoque": peca.quantidade_estoque})
             
        return repo.atualizar(peca)
    except (PecaError, ValueError) as e:
        if isinstance(e, ValueError):
             raise HTTPException(status_code=400, detail=str(e))
        handle_peca_error(e)


@router.patch("/{peca_id}/desativar", response_model=PecaResponse, dependencies=[Depends(get_current_user)])
def desativar_peca(peca_id: int, db: Session = Depends(get_db)):
    """Desativa uma peça."""
    repo = PecaRepository(db)
    use_case = AtualizarPecaUseCase(repo)
    try:
        return use_case.execute(peca_id, {"ativo": False})
    except PecaError as e:
        handle_peca_error(e)


@router.patch("/{peca_id}/ativar", response_model=PecaResponse, dependencies=[Depends(get_current_user)])
def ativar_peca(peca_id: int, db: Session = Depends(get_db)):
    """Ativa uma peça."""
    repo = PecaRepository(db)
    use_case = AtualizarPecaUseCase(repo)
    try:
        return use_case.execute(peca_id, {"ativo": True})
    except PecaError as e:
        handle_peca_error(e)


@router.delete("/{peca_id}", status_code=204, dependencies=[Depends(get_current_user)])
def deletar_peca(peca_id: int, db: Session = Depends(get_db)):
    """Remove uma peça do sistema."""
    repo = PecaRepository(db)
    use_case = DeletarPecaUseCase(repo)
    try:
        use_case.execute(peca_id)
    except PecaError as e:
        handle_peca_error(e)
