import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer(auto_error=False)


@dataclass
class Actor:
    is_admin: bool
    customer_id: str | None = None


def get_actor(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> Actor:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("JWT_SECRET_KEY", ""), algorithms=[os.getenv("JWT_ALGORITHM", "HS256")])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    role = payload.get("role") or payload.get("tipo") or payload.get("perfil")
    return Actor(is_admin=role in {"ADMIN", "admin"}, customer_id=payload.get("sub"))
