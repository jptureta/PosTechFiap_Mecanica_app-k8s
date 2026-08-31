"""
Endpoints de webhook para integrações externas.

2.3 — Aprovação/recusa de orçamento por sistemas externos (portal do cliente,
      gateway de pagamento, etc.) autenticados via API key no header X-Webhook-Key.

2.5 — Atualização de status via e-mail: recebe o payload de e-mail inbound
      (no formato de provedores como Mailgun, SendGrid ou AWS SES) e extrai
      o ID da OS e a ação desejada para processar a mudança de status.

Formato do e-mail inbound esperado:
    subject: "OS #42 APROVAR" | "OS 42 RECUSAR" | "OS #42 STATUS em_diagnostico"
    body   : campo opcional com texto livre do cliente
"""
import re
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.api.deps import get_webhook_api_key
from app.adapters.gateways.ordem_servico_repository import OrdemServicoRepository
from app.adapters.gateways.peca_repository import PecaRepository
from app.adapters.gateways.email_notificacao_service import EmailNotificacaoService
from app.use_cases.ordem_servico.atualizar_ordem_servico import (
    AtualizarStatusOrdemServicoUseCase,
    AprovarOrcamentoUseCase,
    RecusarOrcamentoUseCase,
)
from app.schemas.ordem_servico import OrdemServicoResponse
from app.domain.enums import StatusOrdemServico
from app.domain.exceptions.ordem_servico_exceptions import (
    OrdemServicoNaoEncontradaError,
    OrdemServicoError,
    TransicaoStatusInvalidaError,
)
from app.domain.exceptions.peca_exceptions import PecaError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhook",
    tags=["Webhooks Externos"],
    dependencies=[Depends(get_webhook_api_key)],
)

_STATUS_ALIASES: dict[str, StatusOrdemServico] = {
    "recebida": StatusOrdemServico.RECEBIDA,
    "em_diagnostico": StatusOrdemServico.EM_DIAGNOSTICO,
    "diagnostico": StatusOrdemServico.EM_DIAGNOSTICO,
    "aguardando_aprovacao": StatusOrdemServico.AGUARDANDO_APROVACAO,
    "aguardando": StatusOrdemServico.AGUARDANDO_APROVACAO,
    "em_execucao": StatusOrdemServico.EM_EXECUCAO,
    "execucao": StatusOrdemServico.EM_EXECUCAO,
    "finalizada": StatusOrdemServico.FINALIZADA,
    "entregue": StatusOrdemServico.ENTREGUE,
    "cancelada": StatusOrdemServico.CANCELADA,
}


def _handle_error(e: Exception) -> None:
    if isinstance(e, OrdemServicoNaoEncontradaError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, (OrdemServicoError, TransicaoStatusInvalidaError, PecaError)):
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# ── 2.3 — Aprovação/recusa de orçamento por sistema externo ─────────────────

@router.post(
    "/orcamento/{ordem_id}/aprovar",
    response_model=OrdemServicoResponse,
    summary="Aprovação externa de orçamento",
    description=(
        "Recebe notificação de aprovação de orçamento de um sistema externo "
        "(portal do cliente, gateway de pagamento, etc.). "
        "Requer header **X-Webhook-Key** com a API key configurada."
    ),
)
def aprovar_orcamento_externo(ordem_id: int, db: Session = Depends(get_db)):
    repo = OrdemServicoRepository(db)
    notificacao = EmailNotificacaoService()
    use_case = AprovarOrcamentoUseCase(repo, PecaRepository(db), notificacao_service=notificacao)
    try:
        resultado = use_case.execute(ordem_id)
        logger.info("[WEBHOOK] Orçamento da OS #%d aprovado via sistema externo", ordem_id)
        return resultado
    except Exception as e:
        _handle_error(e)


@router.post(
    "/orcamento/{ordem_id}/recusar",
    response_model=OrdemServicoResponse,
    summary="Recusa externa de orçamento",
    description=(
        "Recebe notificação de recusa de orçamento de um sistema externo. "
        "Requer header **X-Webhook-Key** com a API key configurada."
    ),
)
def recusar_orcamento_externo(ordem_id: int, db: Session = Depends(get_db)):
    repo = OrdemServicoRepository(db)
    notificacao = EmailNotificacaoService()
    use_case = RecusarOrcamentoUseCase(repo, notificacao_service=notificacao)
    try:
        resultado = use_case.execute(ordem_id)
        logger.info("[WEBHOOK] Orçamento da OS #%d recusado via sistema externo", ordem_id)
        return resultado
    except Exception as e:
        _handle_error(e)


# ── 2.5 — Atualização de status via e-mail inbound ──────────────────────────

class EmailInboundPayload(BaseModel):
    """Payload de e-mail recebido de provedores como Mailgun, SendGrid ou AWS SES."""
    sender: str = Field(..., description="Endereço de e-mail do remetente")
    subject: str = Field(..., description="Assunto do e-mail")
    body: Optional[str] = Field(None, description="Corpo do e-mail (texto livre)")


class EmailProcessadoResponse(BaseModel):
    ordem_id: int
    acao: str
    status_resultante: str
    mensagem: str


def _extrair_ordem_id(texto: str) -> Optional[int]:
    """Extrai o ID da OS do subject: aceita 'OS #42', 'OS42', '#42', '42'."""
    match = re.search(r"(?:OS\s*)?#?\s*(\d+)", texto, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _detectar_acao(subject: str, body: Optional[str]) -> Optional[str]:
    """Retorna 'aprovar', 'recusar' ou um valor de StatusOrdemServico, ou None."""
    alvo = f"{subject} {body or ''}".upper()

    if re.search(r"\bAPROV", alvo):
        return "aprovar"
    if re.search(r"\bRECUS|\bREJEIT", alvo):
        return "recusar"

    for alias in _STATUS_ALIASES:
        if alias.upper() in alvo:
            return alias

    return None


@router.post(
    "/email-inbound",
    response_model=EmailProcessadoResponse,
    summary="Recebimento de e-mail inbound para atualização de status",
    description=(
        "Processa um e-mail recebido (payload de provedor inbound) para atualizar "
        "o status de uma OS. O **subject** deve conter o ID da OS e a ação desejada.\n\n"
        "**Exemplos de subject válidos:**\n"
        "- `OS #42 APROVAR` → aprova o orçamento da OS 42\n"
        "- `OS 15 RECUSAR` → recusa o orçamento da OS 15\n"
        "- `#7 STATUS em_diagnostico` → avança a OS 7 para Em Diagnóstico\n\n"
        "Requer header **X-Webhook-Key** com a API key configurada."
    ),
)
def processar_email_inbound(payload: EmailInboundPayload, db: Session = Depends(get_db)):
    logger.info(
        "[EMAIL-INBOUND] De: %s | Assunto: %s", payload.sender, payload.subject
    )

    ordem_id = _extrair_ordem_id(payload.subject)
    if not ordem_id:
        raise HTTPException(
            status_code=422,
            detail=(
                "Não foi possível identificar o ID da OS no subject. "
                "Use o formato: 'OS #<id> APROVAR|RECUSAR|STATUS <status>'"
            ),
        )

    acao = _detectar_acao(payload.subject, payload.body)
    if not acao:
        raise HTTPException(
            status_code=422,
            detail=(
                "Ação não reconhecida no e-mail. "
                "Use APROVAR, RECUSAR ou STATUS <nome_do_status> no subject."
            ),
        )

    repo = OrdemServicoRepository(db)
    notificacao = EmailNotificacaoService()

    try:
        if acao == "aprovar":
            resultado = AprovarOrcamentoUseCase(
                repo, PecaRepository(db), notificacao_service=notificacao
            ).execute(ordem_id)
            status_resultante = str(resultado.status)
            mensagem = f"Orçamento da OS #{ordem_id} aprovado via e-mail de {payload.sender}"

        elif acao == "recusar":
            resultado = RecusarOrcamentoUseCase(
                repo, notificacao_service=notificacao
            ).execute(ordem_id)
            status_resultante = str(resultado.status)
            mensagem = f"Orçamento da OS #{ordem_id} recusado via e-mail de {payload.sender}"

        else:
            novo_status = _STATUS_ALIASES.get(acao)
            if not novo_status:
                raise HTTPException(status_code=422, detail=f"Status desconhecido: {acao}")
            resultado = AtualizarStatusOrdemServicoUseCase(
                repo, PecaRepository(db), notificacao_service=notificacao
            ).execute(ordem_id, novo_status, observacao=f"Atualizado via e-mail de {payload.sender}")
            status_resultante = str(resultado.status)
            mensagem = f"Status da OS #{ordem_id} atualizado para '{novo_status}' via e-mail"

        logger.info("[EMAIL-INBOUND] %s", mensagem)
        return EmailProcessadoResponse(
            ordem_id=ordem_id,
            acao=acao,
            status_resultante=status_resultante,
            mensagem=mensagem,
        )

    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)
