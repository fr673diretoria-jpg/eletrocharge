import secrets

import mercadopago
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import config, mp_oauth, models, ocpp_server, schemas, security
from ..carregamento import liberar_vaga
from ..database import get_db
from ..geo import calcular_distancia_km

router = APIRouter(prefix="/api/pagamentos", tags=["pagamentos"])


def _sdk(token: str) -> mercadopago.SDK:
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Pagamentos não configurados: defina MP_ACCESS_TOKEN no arquivo .env",
        )
    return mercadopago.SDK(token)


@router.post("", response_model=schemas.PagamentoOut, status_code=201)
def criar_pagamento(
    dados: schemas.PagamentoCreate,
    usuario: models.Usuario = Depends(security.obter_usuario_atual),
    db: Session = Depends(get_db),
):
    estacao = db.query(models.Estacao).filter(models.Estacao.id == dados.estacao_id).first()
    if not estacao:
        raise HTTPException(status_code=404, detail="Estação não encontrada")
    if estacao.vagas_livres <= 0:
        raise HTTPException(status_code=400, detail="Não há carregador disponível nesta estação")

    parceiro = estacao.parceiro
    token_cobranca = config.MP_ACCESS_TOKEN
    comissao_valor = None

    if parceiro:
        token_cobranca = mp_oauth.token_valido_do_parceiro(parceiro, db)
        if not token_cobranca:
            raise HTTPException(
                status_code=409,
                detail="Pagamento temporariamente indisponível nesta estação. Tente novamente mais tarde.",
            )
        percentual = (
            parceiro.comissao_percentual
            if parceiro.comissao_percentual is not None
            else config.COMISSAO_PADRAO_PERCENTUAL
        )
        comissao_valor = round(dados.valor * percentual / 100, 2)

    pagamento = models.Pagamento(
        usuario_id=usuario.id,
        estacao_id=estacao.id,
        parceiro_id=parceiro.id if parceiro else None,
        valor=dados.valor,
        comissao_valor=comissao_valor,
        metodo=dados.metodo,
        status="pendente",
        ocpp_id_tag=secrets.token_hex(6).upper(),
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    sdk = _sdk(token_cobranca)
    preferencia = {
        "items": [{
            "title": f"Recarga - {estacao.nome}",
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": float(dados.valor),
        }],
        "payer": {"email": usuario.email, "name": usuario.nome},
        "external_reference": str(pagamento.id),
        "back_urls": {
            "success": f"{config.APP_BASE_URL}/?pagamento=sucesso&pagamento_id={pagamento.id}",
            "failure": f"{config.APP_BASE_URL}/?pagamento=falha&pagamento_id={pagamento.id}",
            "pending": f"{config.APP_BASE_URL}/?pagamento=pendente&pagamento_id={pagamento.id}",
        },
        "auto_return": "approved",
        "notification_url": f"{config.APP_BASE_URL}/api/pagamentos/webhook",
    }

    # Split de pagamento: quando a estação tem parceiro conectado, a cobrança é feita com o
    # access_token DELE (via OAuth), e marketplace_fee é o valor que a plataforma retém como comissão.
    if comissao_valor is not None:
        preferencia["marketplace_fee"] = comissao_valor

    resposta = sdk.preference().create(preferencia)
    if resposta["status"] not in (200, 201):
        raise HTTPException(status_code=502, detail="Falha ao criar cobrança no Mercado Pago")

    pref = resposta["response"]
    pagamento.mp_preference_id = pref["id"]
    db.commit()
    db.refresh(pagamento)

    saida = schemas.PagamentoOut.model_validate(pagamento)
    saida.checkout_url = pref.get("init_point")
    return saida



@router.get("/meus", response_model=list[schemas.PagamentoOut])
def meus_pagamentos(
    usuario: models.Usuario = Depends(security.obter_usuario_atual),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Pagamento)
        .filter(models.Pagamento.usuario_id == usuario.id)
        .order_by(models.Pagamento.criado_em.desc())
        .all()
    )


@router.post("/{pagamento_id}/finalizar")
def finalizar_carregamento(
    pagamento_id: int,
    dados: schemas.FinalizarCarregamento,
    usuario: models.Usuario = Depends(security.obter_usuario_atual),
    db: Session = Depends(get_db),
):
    """Libera a vaga automaticamente quando o GPS confirma que o motorista se afastou da estação."""
    pagamento = (
        db.query(models.Pagamento)
        .filter(models.Pagamento.id == pagamento_id, models.Pagamento.usuario_id == usuario.id)
        .first()
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    if pagamento.status != "aprovado":
        raise HTTPException(status_code=400, detail="Este carregamento não está em andamento")

    estacao = db.query(models.Estacao).filter(models.Estacao.id == pagamento.estacao_id).first()
    if not estacao:
        raise HTTPException(status_code=404, detail="Estação não encontrada")

    distancia_km = calcular_distancia_km(dados.lat, dados.lng, estacao.latitude, estacao.longitude)
    distancia_m = distancia_km * 1000

    if distancia_m < config.DISTANCIA_LIBERACAO_VAGA_METROS:
        return {
            "liberado": False,
            "distancia_m": round(distancia_m),
            "mensagem": "Você ainda está próximo da estação. Afaste-se para liberar a vaga automaticamente.",
        }

    liberar_vaga(estacao)
    pagamento.status = "concluido"
    db.commit()

    return {
        "liberado": True,
        "distancia_m": round(distancia_m),
        "mensagem": "Vaga liberada com sucesso. Obrigado por usar o EletroCharge!",
    }


@router.get("/{pagamento_id}", response_model=schemas.PagamentoOut)
def status_pagamento(
    pagamento_id: int,
    usuario: models.Usuario = Depends(security.obter_usuario_atual),
    db: Session = Depends(get_db),
):
    pagamento = (
        db.query(models.Pagamento)
        .filter(models.Pagamento.id == pagamento_id, models.Pagamento.usuario_id == usuario.id)
        .first()
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return pagamento


def _buscar_pagamento_mp(payment_id: str, db: Session) -> dict:
    """Localiza o pagamento no Mercado Pago testando o token master e o de cada parceiro
    conectado (pagamentos com split só são visíveis pelo token do parceiro que os recebeu)."""
    tokens_candidatos = []
    if config.MP_ACCESS_TOKEN:
        tokens_candidatos.append(config.MP_ACCESS_TOKEN)

    parceiros = db.query(models.Parceiro).filter(models.Parceiro.mp_access_token.isnot(None)).all()
    for parceiro in parceiros:
        token = mp_oauth.token_valido_do_parceiro(parceiro, db)
        if token:
            tokens_candidatos.append(token)

    for token in tokens_candidatos:
        try:
            resposta = mercadopago.SDK(token).payment().get(payment_id)
        except Exception:
            continue
        if resposta.get("status") == 200:
            return resposta.get("response", {})

    return {}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Notificação (IPN) do Mercado Pago. Sempre revalidamos o pagamento direto na API deles."""
    parametros = dict(request.query_params)
    corpo = {}
    try:
        corpo = await request.json()
    except Exception:
        pass

    payment_id = parametros.get("data.id") or corpo.get("data", {}).get("id") or parametros.get("id")
    tipo = parametros.get("type") or corpo.get("type")

    if tipo != "payment" or not payment_id:
        return {"recebido": True}

    pagamento_mp = _buscar_pagamento_mp(payment_id, db)
    if not pagamento_mp:
        return {"recebido": True}

    referencia = pagamento_mp.get("external_reference")
    if not referencia:
        return {"recebido": True}

    pagamento = db.query(models.Pagamento).filter(models.Pagamento.id == int(referencia)).first()
    if not pagamento:
        return {"recebido": True}

    ja_estava_aprovado = pagamento.status == "aprovado"

    mapa_status = {
        "approved": "aprovado",
        "rejected": "recusado",
        "pending": "pendente",
        "in_process": "pendente",
        "cancelled": "cancelado",
    }
    pagamento.status = mapa_status.get(pagamento_mp.get("status"), pagamento.status)
    pagamento.mp_payment_id = str(pagamento_mp.get("id", pagamento.mp_payment_id))

    estacao = None
    if pagamento.status == "aprovado":
        estacao = db.query(models.Estacao).filter(models.Estacao.id == pagamento.estacao_id).first()
        if estacao and estacao.vagas_livres > 0:
            estacao.vagas_livres -= 1
            if estacao.vagas_livres == 0:
                estacao.status = "ocupado"

    db.commit()

    # Dispara o início remoto no carregador real via OCPP, só na primeira vez que aprovar
    # (webhooks podem chegar duplicados) e só se a estação tiver um carregador conectado.
    if pagamento.status == "aprovado" and not ja_estava_aprovado and estacao and estacao.ocpp_identity:
        await ocpp_server.iniciar_carregamento_remoto(estacao.ocpp_identity, pagamento.ocpp_id_tag)

    return {"recebido": True}
