from datetime import datetime
from app.domain.repositories.ordem_servico_repository_interface import OrdemServicoRepositoryInterface
from app.domain.enums import StatusOrdemServico


class RelatoriosOrdemServicoUseCase:
    def __init__(self, repository: OrdemServicoRepositoryInterface):
        self.repository = repository

    def calcular_tempo_medio_execucao(self) -> dict:
        ordens = self.repository.listar_todas(status=StatusOrdemServico.FINALIZADA)
        
        total_minutos = 0
        count = 0
        
        for ordem in ordens:
            # Simplificado: No mundo real, buscaríamos do histórico a transição para EM_EXECUCAO
            # Aqui usaremos created_at como início para fins de exemplo/testes legados
            if ordem.data_finalizacao and ordem.created_at:
                delta = ordem.data_finalizacao - ordem.created_at
                total_minutos += delta.total_seconds() / 60
                count += 1
        
        tempo_medio = total_minutos / count if count > 0 else 0
        
        return {
            "tempo_medio_minutos": round(tempo_medio, 2),
            "total_ordens_finalizadas": count
        }
