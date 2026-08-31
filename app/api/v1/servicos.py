from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.schemas.servico import ServicoCreate, ServicoUpdate, ServicoResponse
from app.api.deps import get_current_user
from app.adapters.gateways.servico_repository import ServicoRepository
from app.use_cases.servico.criar_servico import CriarServicoUseCase
from app.use_cases.servico.buscar_servico import BuscarServicoUseCase, ListarServicosUseCase
from app.use_cases.servico.atualizar_servico import AtualizarServicoUseCase, DeletarServicoUseCase
from app.domain.exceptions.servico_exceptions import ServicoError, ServicoNaoEncontradoError, ServicoPrecoInvalidoError

router = APIRouter(prefix="/servicos", tags=["Serviços"])


def handle_servico_error(e: ServicoError):
    if isinstance(e, ServicoNaoEncontradoError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, ServicoPrecoInvalidoError):
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=500, detail="Erro interno no domínio de serviços")


@router.post("/", response_model=ServicoResponse, status_code=201, dependencies=[Depends(get_current_user)])
def criar_servico(dados: ServicoCreate, db: Session = Depends(get_db)):
    """Cria um novo serviço."""
    repo = ServicoRepository(db)
    use_case = CriarServicoUseCase(repo)
    try:
        return use_case.execute(
            nome=dados.nome,
            preco=dados.preco,
            descricao=dados.descricao,
            tempo_estimado_minutos=dados.tempo_estimado_minutos
        )
    except ServicoError as e:
        handle_servico_error(e)


@router.get("/", response_model=list[ServicoResponse], dependencies=[Depends(get_current_user)])
def listar_servicos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Lista todos os serviços com paginação."""
    repo = ServicoRepository(db)
    use_case = ListarServicosUseCase(repo)
    servicos = use_case.execute(skip=skip, limit=limit)
    if apenas_ativos:
        servicos = [s for s in servicos if s.ativo]
    return servicos


@router.get("/{servico_id}", response_model=ServicoResponse, dependencies=[Depends(get_current_user)])
def buscar_servico(servico_id: int, db: Session = Depends(get_db)):
    """Busca um serviço pelo ID."""
    repo = ServicoRepository(db)
    use_case = BuscarServicoUseCase(repo)
    try:
        return use_case.execute(servico_id)
    except ServicoError as e:
        handle_servico_error(e)


@router.put("/{servico_id}", response_model=ServicoResponse, dependencies=[Depends(get_current_user)])
def atualizar_servico(servico_id: int, dados: ServicoUpdate, db: Session = Depends(get_db)):
    """Atualiza dados de um serviço."""
    repo = ServicoRepository(db)
    use_case = AtualizarServicoUseCase(repo)
    try:
        return use_case.execute(servico_id, dados.model_dump(exclude_unset=True))
    except ServicoError as e:
        handle_servico_error(e)


@router.patch("/{servico_id}/desativar", response_model=ServicoResponse, dependencies=[Depends(get_current_user)])
def desativar_servico(servico_id: int, db: Session = Depends(get_db)):
    """Desativa um serviço."""
    repo = ServicoRepository(db)
    use_case = AtualizarServicoUseCase(repo)
    try:
        return use_case.execute(servico_id, {"ativo": False})
    except ServicoError as e:
        handle_servico_error(e)


@router.patch("/{servico_id}/ativar", response_model=ServicoResponse, dependencies=[Depends(get_current_user)])
def ativar_servico(servico_id: int, db: Session = Depends(get_db)):
    """Ativa um serviço."""
    repo = ServicoRepository(db)
    use_case = AtualizarServicoUseCase(repo)
    try:
        return use_case.execute(servico_id, {"ativo": True})
    except ServicoError as e:
        handle_servico_error(e)


@router.delete("/{servico_id}", status_code=204, dependencies=[Depends(get_current_user)])
def deletar_servico(servico_id: int, db: Session = Depends(get_db)):
    """Remove um serviço do sistema."""
    repo = ServicoRepository(db)
    use_case = DeletarServicoUseCase(repo)
    try:
        use_case.execute(servico_id)
    except ServicoError as e:
        handle_servico_error(e)
