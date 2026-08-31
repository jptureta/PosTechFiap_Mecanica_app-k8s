"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabela de usuários
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("nome_completo", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_admin", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela de clientes
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cpf_cnpj", sa.String(14), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("endereco", sa.String(500), nullable=True),
        sa.Column("ativo", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela de veículos
    op.create_table(
        "veiculos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False, index=True),
        sa.Column("placa", sa.String(7), unique=True, nullable=False, index=True),
        sa.Column("marca", sa.String(100), nullable=False),
        sa.Column("modelo", sa.String(100), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ativo", sa.Boolean(), default=True, nullable=False),
        sa.Column("cor", sa.String(50), nullable=True),
        sa.Column("observacoes", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela de serviços
    op.create_table(
        "servicos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.String(1000), nullable=True),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("tempo_estimado_minutos", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tabela de peças
    op.create_table(
        "pecas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.String(1000), nullable=True),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantidade_estoque", sa.Integer(), default=0, nullable=False),
        sa.Column("ativo", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Enum de status
    status_enum = sa.Enum(
        "recebida", "em_diagnostico", "aguardando_aprovacao",
        "em_execucao", "finalizada", "entregue", "cancelada",
        name="status_ordem_servico",
    )

    # Tabela de ordens de serviço
    op.create_table(
        "ordens_servico",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False, index=True),
        sa.Column("veiculo_id", sa.Integer(), sa.ForeignKey("veiculos.id"), nullable=False, index=True),
        sa.Column("status", status_enum, default="recebida", nullable=False, index=True),
        sa.Column("observacoes", sa.String(2000), nullable=True),
        sa.Column("valor_total", sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("data_finalizacao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_entrega", sa.DateTime(timezone=True), nullable=True),
    )

    # Tabela de itens de serviço da OS
    op.create_table(
        "ordens_servico_servicos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ordem_servico_id", sa.Integer(), sa.ForeignKey("ordens_servico.id"), nullable=False, index=True),
        sa.Column("servico_id", sa.Integer(), sa.ForeignKey("servicos.id"), nullable=False),
        sa.Column("quantidade", sa.Integer(), default=1, nullable=False),
        sa.Column("valor_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
    )

    # Tabela de itens de peça da OS
    op.create_table(
        "ordens_servico_pecas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ordem_servico_id", sa.Integer(), sa.ForeignKey("ordens_servico.id"), nullable=False, index=True),
        sa.Column("peca_id", sa.Integer(), sa.ForeignKey("pecas.id"), nullable=False),
        sa.Column("quantidade", sa.Integer(), default=1, nullable=False),
        sa.Column("valor_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
    )

    # Tabela de histórico de status
    op.create_table(
        "ordens_servico_historico",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ordem_servico_id", sa.Integer(), sa.ForeignKey("ordens_servico.id"), nullable=False, index=True),
        sa.Column("status_anterior", sa.String(50), nullable=True),
        sa.Column("status_novo", sa.String(50), nullable=False),
        sa.Column("observacao", sa.String(500), nullable=True),
        sa.Column("data_alteracao", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ordens_servico_historico")
    op.drop_table("ordens_servico_pecas")
    op.drop_table("ordens_servico_servicos")
    op.drop_table("ordens_servico")
    op.drop_table("pecas")
    op.drop_table("servicos")
    op.drop_table("veiculos")
    op.drop_table("clientes")
    op.drop_table("usuarios")
    sa.Enum(name="status_ordem_servico").drop(op.get_bind())
