import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app import auth


def test_get_actor_requires_bearer_token():
    with pytest.raises(HTTPException) as error:
        auth.get_actor(None)

    assert error.value.status_code == 401


def test_get_actor_decodes_roles_and_rejects_bad_tokens(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "execution-secret")
    admin = jwt.encode({"sub": "admin-1", "role": "ADMIN"}, "execution-secret", algorithm="HS256")
    customer = jwt.encode({"sub": "customer-1", "tipo": "cliente"}, "execution-secret", algorithm="HS256")
    invalid_role = jwt.encode({"sub": "user-1", "perfil": "CUSTOMER"}, "execution-secret", algorithm="HS256")

    admin_actor = auth.get_actor(HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin))
    customer_actor = auth.get_actor(HTTPAuthorizationCredentials(scheme="Bearer", credentials=customer))
    assert admin_actor.is_admin is True
    assert customer_actor.is_admin is False
    assert customer_actor.customer_id == "customer-1"

    with pytest.raises(HTTPException) as invalid_token:
        auth.get_actor(HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid"))
    assert invalid_token.value.status_code == 401

    fallback_actor = auth.get_actor(HTTPAuthorizationCredentials(scheme="Bearer", credentials=invalid_role))
    assert fallback_actor.is_admin is False
    assert fallback_actor.customer_id == "user-1"
