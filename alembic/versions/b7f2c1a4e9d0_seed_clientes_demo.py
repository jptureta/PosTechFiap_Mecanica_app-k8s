"""seed clientes demo (autenticacao por CPF)

Popula a tabela `clientes` com registros usados na demonstração da Fase 3:
o cliente autenticado por CPF que aparece no vídeo. Todos os CPFs têm
dígitos verificadores válidos — a Lambda vai aceitá-los na validação.

- 52998224725 → Maria Silva (ativo)   — caminho feliz: 200 + JWT
- 11144477735 → João Pereira (ativo)  — segundo caminho feliz de demonstração
- 39053344705 → Ana Costa   (inativo) — demo do 400 "cliente inativo"

CPFs válidos, porém NÃO cadastrados, servem para demonstrar o 404
"cliente não encontrado" (não precisam existir no banco).

Revision ID: b7f2c1a4e9d0
Revises: a1b2c3d4e5f6
Create Date: 2026-09-12 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7f2c1a4e9d0"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO clientes (id, nome, cpf_cnpj, email, telefone, endereco, ativo, created_at, updated_at)
        VALUES
            (
                900,
                'Maria Silva',
                '52998224725',
                'maria.silva@exemplo.com',
                '11987654321',
                'Rua das Palmeiras 100, Sorocaba/SP',
                true,
                now(),
                now()
            ),
            (
                901,
                'João Pereira',
                '11144477735',
                'joao.pereira@exemplo.com',
                '11912345678',
                'Av. Brasil 2000, São Paulo/SP',
                true,
                now(),
                now()
            ),
            (
                902,
                'Ana Costa',
                '39053344705',
                'ana.costa@exemplo.com',
                '11988887777',
                'Rua Ipê 45, Campinas/SP',
                false,
                now(),
                now()
            )
        ON CONFLICT (cpf_cnpj) DO NOTHING;
        """
    )
    op.execute(
        "SELECT setval('clientes_id_seq', GREATEST((SELECT MAX(id) FROM clientes), 1));"
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM clientes
         WHERE cpf_cnpj IN ('52998224725', '11144477735', '39053344705');
        """
    )
