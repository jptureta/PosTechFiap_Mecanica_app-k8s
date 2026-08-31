"""initial user admin

Revision ID: e62506a3852c
Revises: 001
Create Date: 2026-05-01 00:02:19.388192

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e62506a3852c'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO usuarios (id, username, email, hashed_password, nome_completo, is_active, is_admin, created_at, updated_at)
        VALUES (
            1,
            'administrator',
            'administrator.user@gmail.com',
            '$2b$12$MXf8.6U0MayuMcuYr0r/huoDKrJjdantMluH16KG6pgJYh8J6vp5.',
            'User Admin',
            true,
            true,
            now(),
            now()
        )
        ON CONFLICT (id) DO NOTHING;
        """
    )
    op.execute(
        "SELECT setval('usuarios_id_seq', (SELECT MAX(id) FROM usuarios));"
    )


def downgrade() -> None:
    op.execute("DELETE FROM usuarios WHERE id = 1;")
