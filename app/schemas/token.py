from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    # Token de usuário admin (autenticação por username/senha)
    username: Optional[str] = None

    # Token de cliente (autenticação por CPF via Lambda)
    cpf: Optional[str] = None

    # Distingue o tipo do token para roteamento nas dependências
    # "admin"   → emitido pelo endpoint /api/v1/auth/login
    # "cliente" → emitido pela Lambda /auth/cpf
    tipo: str = "admin"
