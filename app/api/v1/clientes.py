from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.api.deps import get_current_user
from app.adapters.gateways.cliente_repository import ClienteRepository
from app.adapters.gateways.cliente_pendencia_gateway import ClientePendenciaGateway
from app.use_cases.cliente.criar_cliente import CriarClienteUseCase
from app.use_cases.cliente.buscar_cliente import BuscarClienteUseCase, ListarClientesUseCase
from app.use_cases.cliente.atualizar_cliente import AtualizarClienteUseCase, DesativarClienteUseCase, AtivarClienteUseCase
from app.domain.exceptions.cliente_exceptions import ClienteError, ClienteNaoEncontradoError, ClienteJaCadastradoError, ClientePossuiPendenciasError

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def handle_domain_error(e: ClienteError):
    if isinstance(e, ClienteNaoEncontradoError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, ClienteJaCadastradoError):
        raise HTTPException(status_code=400, detail=str(e))
    if isinstance(e, ClientePossuiPendenciasError):
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=500, detail="Erro interno de domínio")


@router.post("/", response_model=ClienteResponse, status_code=201, dependencies=[Depends(get_current_user)])
def criar_cliente(dados: ClienteCreate, db: Session = Depends(get_db)):
    """Cria um novo cliente."""
    repo = ClienteRepository(db)
    use_case = CriarClienteUseCase(repo)
    try:
        return use_case.execute(
            nome=dados.nome,
            cpf_cnpj=dados.cpf_cnpj,
            email=dados.email,
            telefone=dados.telefone,
            endereco=dados.endereco
        )
    except ClienteError as e:
        handle_domain_error(e)


@router.get("/", response_model=list[ClienteResponse], dependencies=[Depends(get_current_user)])
def listar_clientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lista todos os clientes com paginação."""
    repo = ClienteRepository(db)
    use_case = ListarClientesUseCase(repo)
    return use_case.execute(skip=skip, limit=limit)


@router.get("/{cliente_id}", response_model=ClienteResponse, dependencies=[Depends(get_current_user)])
def buscar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Busca um cliente pelo ID."""
    repo = ClienteRepository(db)
    use_case = BuscarClienteUseCase(repo)
    try:
        return use_case.por_id(cliente_id)
    except ClienteError as e:
        handle_domain_error(e)


@router.get("/cpf-cnpj/{cpf_cnpj}", response_model=ClienteResponse, dependencies=[Depends(get_current_user)])
def buscar_por_cpf_cnpj(cpf_cnpj: str, db: Session = Depends(get_db)):
    """Busca um cliente pelo CPF ou CNPJ."""
    repo = ClienteRepository(db)
    use_case = BuscarClienteUseCase(repo)
    try:
        return use_case.por_cpf_cnpj(cpf_cnpj)
    except ClienteError as e:
        handle_domain_error(e)


@router.put("/{cliente_id}", response_model=ClienteResponse, dependencies=[Depends(get_current_user)])
def atualizar_cliente(cliente_id: int, dados: ClienteUpdate, db: Session = Depends(get_db)):
    """Atualiza dados de um cliente."""
    repo = ClienteRepository(db)
    use_case = AtualizarClienteUseCase(repo)
    try:
        return use_case.execute(cliente_id, dados.model_dump(exclude_unset=True))
    except ClienteError as e:
        handle_domain_error(e)


@router.delete("/{cliente_id}/desativar", status_code=204, dependencies=[Depends(get_current_user)])
def desativar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Desativa um cliente."""
    repo = ClienteRepository(db)
    pendencia_gateway = ClientePendenciaGateway(db)
    use_case = DesativarClienteUseCase(repo, pendencia_gateway)
    try:
        use_case.execute(cliente_id)
    except ClienteError as e:
        handle_domain_error(e)


@router.put("/{cliente_id}/ativar", response_model=ClienteResponse, dependencies=[Depends(get_current_user)])
def ativar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Ativa um cliente."""
    repo = ClienteRepository(db)
    use_case = AtivarClienteUseCase(repo)
    try:
        return use_case.execute(cliente_id)
    except ClienteError as e:
        handle_domain_error(e)
