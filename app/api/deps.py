from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.services.auth_service import decode_access_token
from app.adapters.gateways.usuario_repository import UsuarioRepository
from app.domain.entities.usuario import Usuario
from app.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependency que valida o token JWT e retorna o usuário autenticado."""
    token_data = decode_access_token(token)
    repo = UsuarioRepository(db)
    user = repo.buscar_por_username(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return user


def get_webhook_api_key(x_webhook_key: str = Header(..., description="API key para webhooks externos")) -> str:
    """Valida a API key usada por sistemas externos (portais, gateways, provedores de e-mail)."""
    settings = get_settings()
    if x_webhook_key != settings.WEBHOOK_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key inválida")
    return x_webhook_key


def get_admin_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Dependency que exige permissão de administrador."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão de administrador necessária",
        )
    return current_user
