from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.schemas.veiculo import VeiculoCreate, VeiculoUpdate, VeiculoResponse
from app.api.deps import get_current_user
from app.adapters.gateways.veiculo_repository import VeiculoRepository
from app.adapters.gateways.cliente_repository import ClienteRepository
from app.use_cases.veiculo.criar_veiculo import CriarVeiculoUseCase
from app.use_cases.veiculo.buscar_veiculo import BuscarVeiculoUseCase, ListarVeiculosUseCase
from app.use_cases.veiculo.atualizar_veiculo import AtualizarVeiculoUseCase, DeletarVeiculoUseCase
from app.domain.exceptions.veiculo_exceptions import VeiculoError, VeiculoNaoEncontradoError, VeiculoPlacaDuplicadaError
from app.domain.exceptions.cliente_exceptions import ClienteNaoEncontradoError

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


def handle_veiculo_error(e: Exception):
    if isinstance(e, VeiculoNaoEncontradoError) or isinstance(e, ClienteNaoEncontradoError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, VeiculoPlacaDuplicadaError):
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=500, detail="Erro interno no domínio de veículos")


@router.post("/", response_model=VeiculoResponse, status_code=201, dependencies=[Depends(get_current_user)])
def criar_veiculo(dados: VeiculoCreate, db: Session = Depends(get_db)):
    """Cria um novo veículo."""
    veiculo_repo = VeiculoRepository(db)
    cliente_repo = ClienteRepository(db)
    use_case = CriarVeiculoUseCase(veiculo_repo, cliente_repo)
    try:
        return use_case.execute(
            cliente_id=dados.cliente_id,
            placa=dados.placa,
            marca=dados.marca,
            modelo=dados.modelo,
            ano=dados.ano,
            cor=dados.cor,
            observacoes=dados.observacoes
        )
    except (VeiculoError, ClienteNaoEncontradoError) as e:
        handle_veiculo_error(e)


@router.get("/", response_model=list[VeiculoResponse], dependencies=[Depends(get_current_user)])
def listar_veiculos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lista todos os veículos com paginação."""
    repo = VeiculoRepository(db)
    use_case = ListarVeiculosUseCase(repo)
    return use_case.execute(skip=skip, limit=limit)


@router.get("/{veiculo_id}", response_model=VeiculoResponse, dependencies=[Depends(get_current_user)])
def buscar_veiculo(veiculo_id: int, db: Session = Depends(get_db)):
    """Busca um veículo pelo ID."""
    repo = VeiculoRepository(db)
    use_case = BuscarVeiculoUseCase(repo)
    try:
        return use_case.por_id(veiculo_id)
    except VeiculoError as e:
        handle_veiculo_error(e)


@router.get("/cliente/{cliente_id}", response_model=list[VeiculoResponse], dependencies=[Depends(get_current_user)])
def buscar_por_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Busca veículos associados a um cliente."""
    repo = VeiculoRepository(db)
    use_case = BuscarVeiculoUseCase(repo)
    return use_case.por_cliente(cliente_id)


@router.put("/{veiculo_id}", response_model=VeiculoResponse, dependencies=[Depends(get_current_user)])
def atualizar_veiculo(veiculo_id: int, dados: VeiculoUpdate, db: Session = Depends(get_db)):
    """Atualiza dados de um veículo."""
    repo = VeiculoRepository(db)
    use_case = AtualizarVeiculoUseCase(repo)
    try:
        return use_case.execute(veiculo_id, dados.model_dump(exclude_unset=True))
    except VeiculoError as e:
        handle_veiculo_error(e)


@router.delete("/{veiculo_id}", status_code=204, dependencies=[Depends(get_current_user)])
def deletar_veiculo(veiculo_id: int, db: Session = Depends(get_db)):
    """Remove um veículo do sistema."""
    repo = VeiculoRepository(db)
    use_case = DeletarVeiculoUseCase(repo)
    try:
        use_case.execute(veiculo_id)
    except VeiculoError as e:
        handle_veiculo_error(e)
