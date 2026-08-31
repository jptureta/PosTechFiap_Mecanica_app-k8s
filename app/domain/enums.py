import enum


class StatusOrdemServico(str, enum.Enum):
    RECEBIDA = "recebida"
    EM_DIAGNOSTICO = "em_diagnostico"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    EM_EXECUCAO = "em_execucao"
    FINALIZADA = "finalizada"
    ENTREGUE = "entregue"
    CANCELADA = "cancelada"


TRANSICOES_VALIDAS: dict[StatusOrdemServico, list[StatusOrdemServico]] = {
    StatusOrdemServico.RECEBIDA: [StatusOrdemServico.EM_DIAGNOSTICO, StatusOrdemServico.CANCELADA],
    StatusOrdemServico.EM_DIAGNOSTICO: [StatusOrdemServico.AGUARDANDO_APROVACAO, StatusOrdemServico.CANCELADA],
    StatusOrdemServico.AGUARDANDO_APROVACAO: [StatusOrdemServico.EM_EXECUCAO, StatusOrdemServico.CANCELADA],
    StatusOrdemServico.EM_EXECUCAO: [StatusOrdemServico.FINALIZADA, StatusOrdemServico.CANCELADA],
    StatusOrdemServico.FINALIZADA: [StatusOrdemServico.ENTREGUE],
    StatusOrdemServico.ENTREGUE: [],
    StatusOrdemServico.CANCELADA: [],
}
