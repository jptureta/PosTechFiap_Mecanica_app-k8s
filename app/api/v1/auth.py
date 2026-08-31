from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.schemas.token import Token
from app.schemas.usuario import UsuarioCreate, UsuarioResponse
from app.services import auth_service
from app.api.deps import get_current_user
from app.domain.entities.usuario import Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UsuarioResponse, status_code=201)
def registrar(dados: UsuarioCreate, db: Session = Depends(get_db)):
    """Registra um novo usuário administrativo."""
    return auth_service.registrar_usuario(db, dados)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Autentica o usuário e retorna um token JWT."""
    return auth_service.autenticar_usuario(db, form_data.username, form_data.password)


@router.get("/me", response_model=UsuarioResponse)
def perfil(current_user: Usuario = Depends(get_current_user)):
    """Retorna informações do usuário autenticado."""
    return current_user
