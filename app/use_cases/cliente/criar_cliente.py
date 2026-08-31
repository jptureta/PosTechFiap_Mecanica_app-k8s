from app.domain.entities.cliente import Cliente
from app.domain.repositories.cliente_repository_interface import ClienteRepositoryInterface
from app.domain.exceptions.cliente_exceptions import ClienteJaCadastradoError


class CriarClienteUseCase:
    def __init__(self, repository: ClienteRepositoryInterface):
        self.repository = repository

    def execute(self, nome: str, cpf_cnpj: str, email: str = None, telefone: str = None, endereco: str = None) -> Cliente:
        if self.repository.buscar_por_cpf_cnpj(cpf_cnpj):
            raise ClienteJaCadastradoError()

        cliente = Cliente(
            nome=nome,
            cpf_cnpj=cpf_cnpj,
            email=email,
            telefone=telefone,
            endereco=endereco
        )
        return self.repository.salvar(cliente)
