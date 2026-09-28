"""Integração OAuth do Mercado Pago (fluxo Marketplace) — usada para conectar parceiros."""
from datetime import datetime, timedelta
from typing import Optional

import requests
from sqlalchemy.orm import Session

from . import config, models

URL_AUTORIZAR = "https://auth.mercadopago.com/authorization"
URL_TOKEN = "https://api.mercadopago.com/oauth/token"


def url_de_autorizacao(parceiro_id: int) -> str:
    redirect_uri = f"{config.APP_BASE_URL}/api/admin/parceiros/oauth/callback"
    return (
        f"{URL_AUTORIZAR}?client_id={config.MP_CLIENT_ID}&response_type=code"
        f"&platform_id=mp&state={parceiro_id}&redirect_uri={redirect_uri}"
    )


def trocar_code_por_token(code: str) -> dict:
    redirect_uri = f"{config.APP_BASE_URL}/api/admin/parceiros/oauth/callback"
    resposta = requests.post(
        URL_TOKEN,
        json={
            "client_id": config.MP_CLIENT_ID,
            "client_secret": config.MP_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=15,
    )
    resposta.raise_for_status()
    return resposta.json()


def salvar_token_no_parceiro(parceiro: models.Parceiro, dados_token: dict, db: Session) -> None:
    parceiro.mp_user_id = str(dados_token.get("user_id", ""))
    parceiro.mp_access_token = dados_token.get("access_token")
    parceiro.mp_refresh_token = dados_token.get("refresh_token")
    parceiro.mp_token_expira_em = datetime.utcnow() + timedelta(
        seconds=dados_token.get("expires_in", 21600)
    )
    db.commit()


def token_valido_do_parceiro(parceiro: models.Parceiro, db: Session) -> Optional[str]:
    """Retorna um access_token utilizável do parceiro, renovando via refresh_token se necessário."""
    if not parceiro or not parceiro.mp_access_token:
        return None

    ainda_valido = (
        parceiro.mp_token_expira_em
        and parceiro.mp_token_expira_em > datetime.utcnow() + timedelta(minutes=5)
    )
    if ainda_valido:
        return parceiro.mp_access_token

    if not parceiro.mp_refresh_token:
        return parceiro.mp_access_token

    resposta = requests.post(
        URL_TOKEN,
        json={
            "client_id": config.MP_CLIENT_ID,
            "client_secret": config.MP_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": parceiro.mp_refresh_token,
        },
        timeout=15,
    )
    if resposta.status_code != 200:
        return parceiro.mp_access_token

    salvar_token_no_parceiro(parceiro, resposta.json(), db)
    return parceiro.mp_access_token
