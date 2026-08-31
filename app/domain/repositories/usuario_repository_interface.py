from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.usuario import Usuario


class UsuarioRepositoryInterface(ABC):
    """Interface de repositório de usuários no domínio."""

    @abstractmethod
    def buscar_por_username(self, username: str) -> Optional[Usuario]:
        pass

    @abstractmethod
    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        pass

    @abstractmethod
    def salvar(self, usuario: Usuario) -> Usuario:
        pass
