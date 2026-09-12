from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.services.auth_service import decode_access_token
from app.adapters.gateways.usuario_repository import UsuarioRepository
from app.adapters.gateways.cliente_repository import ClienteRepository
from app.domain.entities.usuario import Usuario
from app.domain.entities.cliente import Cliente
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


def get_current_cliente(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Cliente:
    """
    Dependency que aceita tokens JWT emitidos pela Lambda de autenticação por CPF.

    Use esta dependência em rotas que devem ser acessíveis por clientes
    autenticados com seu CPF (em vez de usuários admin com username/senha).
    """
    token_data = decode_access_token(token)

    if token_data.tipo != "cliente" or not token_data.cpf:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta rota requer autenticação de cliente via CPF",
        )

    repo = ClienteRepository(db)
    cliente = repo.buscar_por_cpf_cnpj(token_data.cpf)

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cliente não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not cliente.ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cliente inativo",
        )

    return cliente


# ─────────────────────────────────────────────────────────────
# Ator híbrido: admin OU cliente CPF
#
# Rotas que devem servir os dois tipos de token (ex.: consultar
# uma ordem de serviço) usam `get_current_actor` e chamam
# `_assert_pode_ver_ordem` para autorizar por regra de negócio.
# ─────────────────────────────────────────────────────────────


@dataclass
class Actor:
    """
    Representa quem está fazendo a requisição.

    Um `Actor` sai da dependency `get_current_actor` já resolvido — seja um
    funcionário admin (token de username/senha emitido pelo /api/v1/auth/login),
    seja um cliente autenticado por CPF (token emitido pela Lambda /auth/cpf).

    As propriedades `is_admin` / `is_cliente` e `cliente_id` são atalhos usados
    pelas checagens de ownership dos endpoints (ver `_assert_pode_ver_ordem`).
    """

    tipo: str  # "admin" ou "cliente"
    admin: Optional[Usuario] = None
    cliente: Optional[Cliente] = None

    @property
    def is_admin(self) -> bool:
        return self.tipo == "admin"

    @property
    def is_cliente(self) -> bool:
        return self.tipo == "cliente"

    @property
    def cliente_id(self) -> Optional[int]:
        return self.cliente.id if self.cliente else None


def get_current_actor(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Actor:
    """
    Aceita qualquer token JWT válido (admin OU cliente) e devolve um `Actor`
    identificando quem é. Rotas que só admin acessa continuam usando
    `get_current_user`; rotas exclusivas de cliente continuam usando
    `get_current_cliente`. Esta dependency é para os endpoints compartilhados.
    """
    token_data = decode_access_token(token)

    if token_data.tipo == "cliente":
        if not token_data.cpf:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de cliente sem CPF",
                headers={"WWW-Authenticate": "Bearer"},
            )
        cliente = ClienteRepository(db).buscar_por_cpf_cnpj(token_data.cpf)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cliente não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not cliente.ativo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cliente inativo",
            )
        return Actor(tipo="cliente", cliente=cliente)

    # admin
    if not token_data.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token admin sem username",
            headers={"WWW-Authenticate": "Bearer"},
        )
    usuario = UsuarioRepository(db).buscar_por_username(token_data.username)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not usuario.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return Actor(tipo="admin", admin=usuario)


def assert_pode_ver_ordem(actor: Actor, cliente_id_ordem: int) -> None:
    """
    Garante que o `Actor` pode enxergar ou agir sobre uma ordem de serviço.

    - Admin sempre pode.
    - Cliente só pode se a OS pertencer a ele (mesmo `cliente_id`).
    - Qualquer outro caso levanta 403.

    Recebe o `cliente_id` da OS já carregada em memória para evitar um
    round-trip extra ao banco só para autorizar.
    """
    if actor.is_admin:
        return
    if actor.is_cliente and actor.cliente_id == cliente_id_ordem:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Você não tem acesso a esta ordem de serviço",
    )
