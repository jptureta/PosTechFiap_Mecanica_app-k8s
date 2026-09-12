"""
Testes para a dependency híbrida `get_current_actor` — a que sabe distinguir
um token de admin (username/senha) de um token de cliente (CPF, emitido pela
Lambda) e devolve um `Actor` já resolvido, pronto para os endpoints usarem.

Cobre a decisão principal da Fase 3: as rotas compartilhadas aceitam qualquer
um dos dois tokens, e a autorização por regra de negócio acontece em cima do
`Actor`.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.api.deps import Actor, get_current_actor
from app.config import get_settings
from app.domain.entities.cliente import Cliente
from app.domain.entities.usuario import Usuario


settings = get_settings()


def _token_cliente(cpf: str = "52998224725") -> str:
    """Gera um token igual ao que a Lambda emitiria após validar o CPF."""
    return jwt.encode(
        {"sub": cpf, "tipo": "cliente", "cliente_id": 42, "nome": "Maria Silva"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _token_admin(username: str = "operador") -> str:
    """Gera um token igual ao que o /api/v1/auth/login emitiria."""
    return jwt.encode(
        {"sub": username},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


# ─────────────────────────────────────────────────────────────
# Testes do próprio dataclass Actor — atalhos usados pelos endpoints
# ─────────────────────────────────────────────────────────────

def test_actor_admin_expone_is_admin_e_nao_tem_cliente_id():
    usuario = Usuario()
    usuario.id = 1
    usuario.username = "operador"
    actor = Actor(tipo="admin", admin=usuario)

    assert actor.is_admin is True
    assert actor.is_cliente is False
    assert actor.cliente_id is None


def test_actor_cliente_expone_is_cliente_e_cliente_id():
    cliente = Cliente(id=42, nome="Maria Silva", cpf_cnpj="52998224725")
    actor = Actor(tipo="cliente", cliente=cliente)

    assert actor.is_cliente is True
    assert actor.is_admin is False
    assert actor.cliente_id == 42


# ─────────────────────────────────────────────────────────────
# Testes de get_current_actor — cliente
# ─────────────────────────────────────────────────────────────

def test_get_current_actor_com_token_cliente_retorna_actor_cliente(monkeypatch):
    cliente = Cliente(id=42, nome="Maria Silva", cpf_cnpj="52998224725", ativo=True)

    repo_mock = MagicMock()
    repo_mock.buscar_por_cpf_cnpj.return_value = cliente
    monkeypatch.setattr("app.api.deps.ClienteRepository", lambda db: repo_mock)

    actor = get_current_actor(token=_token_cliente(), db=MagicMock())

    assert actor.is_cliente
    assert actor.cliente_id == 42
    repo_mock.buscar_por_cpf_cnpj.assert_called_once_with("52998224725")


def test_get_current_actor_recusa_cliente_inexistente(monkeypatch):
    repo_mock = MagicMock()
    repo_mock.buscar_por_cpf_cnpj.return_value = None
    monkeypatch.setattr("app.api.deps.ClienteRepository", lambda db: repo_mock)

    with pytest.raises(HTTPException) as exc:
        get_current_actor(token=_token_cliente(), db=MagicMock())

    assert exc.value.status_code == 401
    assert "não encontrado" in exc.value.detail.lower()


def test_get_current_actor_recusa_cliente_inativo(monkeypatch):
    cliente = Cliente(id=42, nome="Maria Silva", cpf_cnpj="52998224725", ativo=False)

    repo_mock = MagicMock()
    repo_mock.buscar_por_cpf_cnpj.return_value = cliente
    monkeypatch.setattr("app.api.deps.ClienteRepository", lambda db: repo_mock)

    with pytest.raises(HTTPException) as exc:
        get_current_actor(token=_token_cliente(), db=MagicMock())

    assert exc.value.status_code == 400
    assert "inativo" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────────
# Testes de get_current_actor — admin
# ─────────────────────────────────────────────────────────────

def test_get_current_actor_com_token_admin_retorna_actor_admin(monkeypatch):
    usuario = Usuario()
    usuario.id = 1
    usuario.username = "operador"
    usuario.is_active = True

    repo_mock = MagicMock()
    repo_mock.buscar_por_username.return_value = usuario
    monkeypatch.setattr("app.api.deps.UsuarioRepository", lambda db: repo_mock)

    actor = get_current_actor(token=_token_admin(), db=MagicMock())

    assert actor.is_admin
    assert actor.admin.username == "operador"
    repo_mock.buscar_por_username.assert_called_once_with("operador")


def test_get_current_actor_recusa_admin_inexistente(monkeypatch):
    repo_mock = MagicMock()
    repo_mock.buscar_por_username.return_value = None
    monkeypatch.setattr("app.api.deps.UsuarioRepository", lambda db: repo_mock)

    with pytest.raises(HTTPException) as exc:
        get_current_actor(token=_token_admin(), db=MagicMock())

    assert exc.value.status_code == 401


def test_get_current_actor_recusa_admin_inativo(monkeypatch):
    usuario = Usuario()
    usuario.id = 1
    usuario.username = "operador"
    usuario.is_active = False

    repo_mock = MagicMock()
    repo_mock.buscar_por_username.return_value = usuario
    monkeypatch.setattr("app.api.deps.UsuarioRepository", lambda db: repo_mock)

    with pytest.raises(HTTPException) as exc:
        get_current_actor(token=_token_admin(), db=MagicMock())

    assert exc.value.status_code == 400
    assert "inativo" in exc.value.detail.lower()
