class OrdemServicoError(Exception):
    """Base exception for OrdemServico domain"""
    pass


class OrdemServicoNaoEncontradaError(OrdemServicoError):
    def __init__(self, message: str = "Ordem de serviço não encontrada"):
        self.message = message
        super().__init__(self.message)


class TransicaoStatusInvalidaError(OrdemServicoError):
    def __init__(self, status_atual: str, novo_status: str):
        self.message = f"Transição de status inválida: {status_atual} -> {novo_status}"
        super().__init__(self.message)


class OrdemServicoSemItensError(OrdemServicoError):
    def __init__(self, message: str = "Ordem de serviço deve ter ao menos um item (serviço ou peça)"):
        self.message = message
        super().__init__(self.message)
