from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.config import get_settings
from app.domain.entities.usuario import Usuario
from app.adapters.gateways.usuario_repository import UsuarioRepository
from app.schemas.usuario import UsuarioCreate
from app.schemas.token import Token, TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        tipo = payload.get("tipo", "admin")

        if tipo == "cliente":
            # Token emitido pela Lambda — identidade é o CPF (campo "sub")
            cpf: str | None = payload.get("sub")
            if not cpf:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token de cliente inválido",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return TokenData(cpf=cpf, tipo="cliente")

        # Token de usuário admin — identidade é o username (campo "sub")
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(username=username, tipo="admin")

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def registrar_usuario(db: Session, dados: UsuarioCreate) -> Usuario:
    repo = UsuarioRepository(db)

    if repo.buscar_por_username(dados.username):
        raise HTTPException(status_code=400, detail="Username já cadastrado")
    if repo.buscar_por_email(dados.email):
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    usuario = Usuario(
        username=dados.username,
        email=dados.email,
        nome_completo=dados.nome_completo,
        hashed_password=hash_password(dados.password),
        is_active=True,
        is_admin=True,
    )
    return repo.salvar(usuario)


def autenticar_usuario(db: Session, username: str, password: str) -> Token:
    repo = UsuarioRepository(db)
    usuario = repo.buscar_por_username(username)

    if not usuario or not verify_password(password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.is_active:
        raise HTTPException(status_code=400, detail="Usuário inativo")

    access_token = create_access_token(data={"sub": usuario.username})
    return Token(access_token=access_token)
