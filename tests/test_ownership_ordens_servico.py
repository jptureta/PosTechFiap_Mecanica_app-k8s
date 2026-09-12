"""
Testes da autorização por ownership nas ordens de serviço.

A regra da fase é: o cliente autenticado por CPF só enxerga e age sobre
as OSs dele. Admin (funcionário da oficina) enxerga tudo. A checagem
concentra-se em `assert_pode_ver_ordem`.
"""

import pytest
from fastapi import HTTPException

from app.api.deps import Actor, assert_pode_ver_ordem
from app.domain.entities.cliente import Cliente
from app.domain.entities.usuario import Usuario


def _admin() -> Actor:
    usuario = Usuario()
    usuario.id = 1
    usuario.username = "operador"
    return Actor(tipo="admin", admin=usuario)


def _cliente(cliente_id: int) -> Actor:
    cliente = Cliente(id=cliente_id, nome="Maria Silva", cpf_cnpj="52998224725")
    return Actor(tipo="cliente", cliente=cliente)


# ─────────────────────────────────────────────────────────────
# Admin passa sempre
# ─────────────────────────────────────────────────────────────

def test_admin_pode_ver_qualquer_ordem_de_qualquer_cliente():
    assert_pode_ver_ordem(_admin(), cliente_id_ordem=42)
    assert_pode_ver_ordem(_admin(), cliente_id_ordem=99)
    assert_pode_ver_ordem(_admin(), cliente_id_ordem=1)


# ─────────────────────────────────────────────────────────────
# Cliente só passa quando a OS é dele
# ─────────────────────────────────────────────────────────────

def test_cliente_pode_ver_ordem_que_pertence_a_ele():
    assert_pode_ver_ordem(_cliente(cliente_id=42), cliente_id_ordem=42)


def test_cliente_nao_pode_ver_ordem_de_outro_cliente():
    with pytest.raises(HTTPException) as exc:
        assert_pode_ver_ordem(_cliente(cliente_id=42), cliente_id_ordem=99)

    assert exc.value.status_code == 403
    assert "acesso" in exc.value.detail.lower()


def test_ator_sem_tipo_valido_e_bloqueado():
    """Segurança em profundidade: um Actor construído com tipo inesperado
    também é barrado — nunca chega a passar como se fosse admin."""
    ator_estranho = Actor(tipo="desconhecido")

    with pytest.raises(HTTPException) as exc:
        assert_pode_ver_ordem(ator_estranho, cliente_id_ordem=42)

    assert exc.value.status_code == 403
