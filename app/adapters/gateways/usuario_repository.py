from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.domain.entities.usuario import Usuario
from app.domain.repositories.usuario_repository_interface import UsuarioRepositoryInterface


class UsuarioRepository(UsuarioRepositoryInterface):
    """Implementação concreta do repositório de usuários.

    Opera sobre o model Usuario (que herda de Base) diretamente,
    pois a entidade de domínio e o model são o mesmo objeto neste caso.
    Em uma refatoração futura, o model pode ser separado da entidade de domínio.
    """

    def __init__(self, db: Session):
        self.db = db

    def buscar_por_username(self, username: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.username == username)
        return self.db.scalars(stmt).first()

    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        stmt = select(Usuario).where(Usuario.email == email)
        return self.db.scalars(stmt).first()

    def salvar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario
