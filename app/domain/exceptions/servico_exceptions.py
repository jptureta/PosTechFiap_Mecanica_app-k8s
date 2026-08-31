class ServicoError(Exception):
    """Base exception for Servico domain"""
    pass


class ServicoNaoEncontradoError(ServicoError):
    def __init__(self, message: str = "Serviço não encontrado"):
        self.message = message
        super().__init__(self.message)


class ServicoPrecoInvalidoError(ServicoError):
    def __init__(self, message: str = "Preço do serviço deve ser maior que zero"):
        self.message = message
        super().__init__(self.message)
