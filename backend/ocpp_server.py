"""Servidor OCPP 1.6-J (subset do Core Profile) — carregadores físicos conectam aqui via WebSocket.

Suporta: BootNotification, Heartbeat, Authorize, StatusNotification, StartTransaction,
StopTransaction e MeterValues. Não é uma implementação 100% completa da especificação OCPP,
mas cobre o fluxo essencial para refletir o status real do conector e liberar a vaga quando
o carregamento termina de verdade (StopTransaction), em vez de depender só do GPS do motorista.
"""
import itertools
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from . import models
from .carregamento import liberar_vaga, recalcular_estacao_por_conectores
from .database import SessionLocal

router = APIRouter()

# Identidade do charge point (string configurada no carregador) -> WebSocket ativo.
conexoes_ativas: dict[str, WebSocket] = {}

CALL = 2
CALLRESULT = 3

_contador_mensagens = itertools.count(1)


def _agora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def enviar_comando(identidade: str, acao: str, payload: dict) -> bool:
    """Envia um comando (CALL) para um carregador conectado. Retorna True se foi enviado."""
    websocket = conexoes_ativas.get(identidade)
    if not websocket:
        return False

    unique_id = f"srv-{next(_contador_mensagens)}"
    await websocket.send_text(json.dumps([CALL, unique_id, acao, payload]))
    return True


async def iniciar_carregamento_remoto(identidade: str, id_tag: str) -> bool:
    """Chamado quando um pagamento é aprovado: pede ao carregador para iniciar a sessão
    já vinculada ao idTag desse pagamento, sem precisar de cartão/RFID físico."""
    return await enviar_comando(identidade, "RemoteStartTransaction", {"idTag": id_tag})


@router.websocket("/ocpp/{identidade}")
async def endpoint_ocpp(websocket: WebSocket, identidade: str):
    subprotocolos = websocket.scope.get("subprotocols") or []
    subprotocolo = "ocpp1.6" if "ocpp1.6" in subprotocolos else None
    await websocket.accept(subprotocol=subprotocolo)
    conexoes_ativas[identidade] = websocket

    db = SessionLocal()
    try:
        while True:
            bruto = await websocket.receive_text()
            try:
                mensagem = json.loads(bruto)
            except ValueError:
                continue

            if not mensagem or mensagem[0] != CALL:
                continue  # ignora CALLRESULT/CALLERROR: o backend ainda não envia comandos ao carregador

            unique_id = mensagem[1]
            acao = mensagem[2]
            payload = mensagem[3] if len(mensagem) > 3 else {}

            estacao = (
                db.query(models.Estacao)
                .filter(models.Estacao.ocpp_identity == identidade)
                .first()
            )

            resposta = _processar_acao(acao, payload, estacao, db)
            await websocket.send_text(json.dumps([CALLRESULT, unique_id, resposta]))
    except WebSocketDisconnect:
        pass
    finally:
        conexoes_ativas.pop(identidade, None)
        db.close()


def _processar_acao(acao: str, payload: dict, estacao, db: Session) -> dict:
    if acao == "BootNotification":
        return {"status": "Accepted", "currentTime": _agora_iso(), "interval": 300}

    if acao == "Heartbeat":
        return {"currentTime": _agora_iso()}

    if acao == "Authorize":
        id_tag = payload.get("idTag")
        pagamento = _buscar_pagamento_por_id_tag(id_tag, estacao, db)
        return {"idTagInfo": {"status": "Accepted" if pagamento else "Invalid"}}

    if acao == "StatusNotification":
        _tratar_status_notification(payload, estacao, db)
        return {}

    if acao == "StartTransaction":
        transaction_id = int(datetime.utcnow().timestamp())
        pagamento = _buscar_pagamento_por_id_tag(payload.get("idTag"), estacao, db)
        if pagamento:
            pagamento.ocpp_transaction_id = transaction_id
            db.commit()
        return {"transactionId": transaction_id, "idTagInfo": {"status": "Accepted"}}

    if acao == "StopTransaction":
        _tratar_stop_transaction(payload, estacao, db)
        return {"idTagInfo": {"status": "Accepted"}}

    # MeterValues, DataTransfer, FirmwareStatusNotification, etc.: apenas confirma.
    return {}


def _buscar_pagamento_por_id_tag(id_tag, estacao, db: Session):
    """Encontra o pagamento aprovado que gerou esse idTag, para esta estação."""
    if not id_tag or not estacao:
        return None
    return (
        db.query(models.Pagamento)
        .filter(
            models.Pagamento.estacao_id == estacao.id,
            models.Pagamento.ocpp_id_tag == id_tag,
            models.Pagamento.status == "aprovado",
        )
        .first()
    )


def _tratar_status_notification(payload: dict, estacao, db: Session) -> None:
    if not estacao:
        return

    connector_id = payload.get("connectorId", 0)
    if not connector_id or connector_id < 1:
        return  # connectorId 0 representa o charge point em si, não um conector físico

    conector = (
        db.query(models.Conector)
        .filter(models.Conector.estacao_id == estacao.id, models.Conector.connector_id == connector_id)
        .first()
    )
    if not conector:
        conector = models.Conector(estacao_id=estacao.id, connector_id=connector_id)
        db.add(conector)

    conector.status = payload.get("status", "Unavailable")
    db.flush()
    recalcular_estacao_por_conectores(estacao, db)
    db.commit()


def _tratar_stop_transaction(payload: dict, estacao, db: Session) -> None:
    if not estacao:
        return

    liberar_vaga(estacao)

    transaction_id = payload.get("transactionId")
    pagamento = None
    if transaction_id is not None:
        pagamento = (
            db.query(models.Pagamento)
            .filter(
                models.Pagamento.ocpp_transaction_id == transaction_id,
                models.Pagamento.status == "aprovado",
            )
            .first()
        )

    if not pagamento:
        # Fallback para carregadores que não devolvem transactionId rastreável: assume
        # o pagamento mais antigo em andamento nesta estação (heurística FIFO).
        pagamento = (
            db.query(models.Pagamento)
            .filter(models.Pagamento.estacao_id == estacao.id, models.Pagamento.status == "aprovado")
            .order_by(models.Pagamento.criado_em.asc())
            .first()
        )

    if pagamento:
        pagamento.status = "concluido"

    db.commit()
