"""Add catalog and stock control fields to pecas

Revision ID: a1b2c3d4e5f6
Revises: 48126106b1df
Create Date: 2026-05-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "48126106b1df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pecas", sa.Column("codigo", sa.String(50), nullable=True))
    op.create_unique_constraint("uq_pecas_codigo", "pecas", ["codigo"])
    op.create_index("ix_pecas_codigo", "pecas", ["codigo"], unique=True)

    op.add_column("pecas", sa.Column("unidade_medida", sa.String(50), nullable=True))

    op.add_column("pecas", sa.Column("quantidade_reservada", sa.Integer(), nullable=False, server_default="0"))

    op.add_column("pecas", sa.Column("estoque_minimo", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_index("ix_pecas_codigo", table_name="pecas")
    op.drop_constraint("uq_pecas_codigo", "pecas", type_="unique")
    op.drop_column("pecas", "codigo")
    op.drop_column("pecas", "unidade_medida")
    op.drop_column("pecas", "quantidade_reservada")
    op.drop_column("pecas", "estoque_minimo")
