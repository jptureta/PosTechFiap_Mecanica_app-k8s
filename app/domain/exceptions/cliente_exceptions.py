class ClienteError(Exception):
    """Base exception for Cliente domain"""
    pass


class ClienteNaoEncontradoError(ClienteError):
    def __init__(self, message: str = "Cliente não encontrado"):
        self.message = message
        super().__init__(self.message)


class ClienteJaCadastradoError(ClienteError):
    def __init__(self, message: str = "Cliente com este CPF/CNPJ já cadastrado"):
        self.message = message
        super().__init__(self.message)


class ClientePossuiPendenciasError(ClienteError):
    def __init__(self, message: str = "Cliente possui ordens de serviço em andamento e não pode ser inativado"):
        self.message = message
        super().__init__(self.message)
