"""Lógica de vagas/status compartilhada entre a liberação por GPS e o servidor OCPP."""
import logging
from datetime import datetime, timedelta

import mercadopago
from sqlalchemy.orm import Session

from . import config, models

logger = logging.getLogger("eletrocharge.carregamento")

STATUS_LIVRE = {"Available"}
STATUS_INDISPONIVEL = {"Unavailable", "Faulted"}


def liberar_vaga(estacao: models.Estacao) -> None:
    """Incrementa 1 vaga livre (sem passar do total) e volta o status para 'livre' se aplicável."""
    estacao.vagas_livres = min(estacao.vagas_total, estacao.vagas_livres + 1)
    if estacao.vagas_livres > 0 and estacao.status != "offline":
        estacao.status = "livre"


def recalcular_estacao_por_conectores(estacao: models.Estacao, db: Session) -> None:
    """Recalcula vagas/status a partir do status real reportado pelos conectores via OCPP."""
    conectores = db.query(models.Conector).filter(models.Conector.estacao_id == estacao.id).all()
    if not conectores:
        return

    livres = sum(1 for c in conectores if c.status in STATUS_LIVRE)
    estacao.vagas_total = max(estacao.vagas_total, len(conectores))
    estacao.vagas_livres = livres

    if livres > 0:
        estacao.status = "livre"
    elif all(c.status in STATUS_INDISPONIVEL for c in conectores):
        estacao.status = "offline"
    else:
        estacao.status = "ocupado"


def _token_para_estorno(pagamento: models.Pagamento, db: Session) -> str | None:
    """Resolve o access token correto (parceiro ou master) para estornar o pagamento no Mercado Pago."""
    if pagamento.parceiro_id:
        from . import mp_oauth  # import tardio: evita qualquer acoplamento desnecessário

        parceiro = db.query(models.Parceiro).filter(models.Parceiro.id == pagamento.parceiro_id).first()
        return mp_oauth.token_valido_do_parceiro(parceiro, db) if parceiro else None
    return config.MP_ACCESS_TOKEN or None


def estornar_pagamento(pagamento: models.Pagamento, db: Session) -> bool:
    """Devolve o valor ao cliente quando a reserva expira sem ele iniciar o carregamento."""
    if not pagamento.mp_payment_id:
        return False

    token = _token_para_estorno(pagamento, db)
    if not token:
        logger.error("Sem token válido para estornar pagamento %s", pagamento.id)
        return False

    try:
        resposta = mercadopago.SDK(token).refund().create(pagamento.mp_payment_id)
        if resposta.get("status") in (200, 201):
            return True
        logger.error("Falha ao estornar pagamento %s: %s", pagamento.id, resposta)
    except Exception:
        logger.exception("Erro ao estornar pagamento %s", pagamento.id)
    return False


async def expirar_reservas_ocpp(db: Session) -> int:
    from . import ocpp_server  # import tardio: evita import circular (ocpp_server importa deste módulo)

    limite = datetime.utcnow() - timedelta(minutes=config.RESERVA_EXPIRA_MINUTOS)
    pagamentos = (
        db.query(models.Pagamento)
        .join(models.Estacao)
        .filter(
            models.Pagamento.status == "aprovado",
            models.Pagamento.ocpp_transaction_id.is_(None),
            models.Pagamento.atualizado_em < limite,
            models.Estacao.ocpp_identity.isnot(None),
        )
        .all()
    )

    for pagamento in pagamentos:
        pagamento.status = "reembolsado" if estornar_pagamento(pagamento, db) else "expirado"
        if pagamento.estacao:
            liberar_vaga(pagamento.estacao)
            if pagamento.estacao.ocpp_identity:
                # Libera a reserva no carregador antes do previsto, para o conector voltar
                # a aceitar outros veículos imediatamente (não precisa esperar o expiryDate).
                await ocpp_server.cancelar_reserva(pagamento.estacao.ocpp_identity, pagamento.id)

    if pagamentos:
        db.commit()

    return len(pagamentos)
