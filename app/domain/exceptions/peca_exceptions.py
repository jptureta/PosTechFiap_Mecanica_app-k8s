class PecaError(Exception):
    """Base exception for Peca domain"""
    pass


class PecaNaoEncontradaError(PecaError):
    def __init__(self, message: str = "Peça não encontrada"):
        self.message = message
        super().__init__(self.message)


class PecaPrecoInvalidoError(PecaError):
    def __init__(self, message: str = "Preço da peça deve ser maior que zero"):
        self.message = message
        super().__init__(self.message)
