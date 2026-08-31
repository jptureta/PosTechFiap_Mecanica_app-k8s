class VeiculoError(Exception):
    """Base exception for Veiculo domain"""
    pass


class VeiculoNaoEncontradoError(VeiculoError):
    def __init__(self, message: str = "Veículo não encontrado"):
        self.message = message
        super().__init__(self.message)


class VeiculoPlacaDuplicadaError(VeiculoError):
    def __init__(self, message: str = "Placa já cadastrada"):
        self.message = message
        super().__init__(self.message)
