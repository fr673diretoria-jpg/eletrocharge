"""Envio de e-mails transacionais (ex.: redefinição de senha)."""
import logging
import smtplib
from email.message import EmailMessage

import requests

from . import config

logger = logging.getLogger("eletrocharge.email")


def enviar_email(destinatario: str, assunto: str, corpo_texto: str, responder_para: str | None = None) -> None:
    """Envia um e-mail transacional. Prioriza a API do Resend (HTTPS, funciona em
    hospedagens que bloqueiam SMTP de saída, como o plano gratuito do Render). Se
    RESEND_API_KEY não estiver definido, cai para SMTP; se nada estiver configurado,
    apenas registra o conteúdo no log (útil em desenvolvimento local).

    Qualquer falha de envio é apenas registrada no log: uma conta de e-mail mal configurada
    não pode derrubar o endpoint de "esqueci minha senha" (evita vazar detalhes e retornar 500)."""
    if config.RESEND_API_KEY:
        _enviar_via_resend(destinatario, assunto, corpo_texto, responder_para)
    elif config.SMTP_HOST:
        _enviar_via_smtp(destinatario, assunto, corpo_texto, responder_para)
    else:
        logger.warning("Nenhum provedor de e-mail configurado. E-mail para %s:\n%s\n%s", destinatario, assunto, corpo_texto)


def _enviar_via_resend(destinatario: str, assunto: str, corpo_texto: str, responder_para: str | None = None) -> None:
    payload = {
        "from": config.SMTP_FROM,
        "to": [destinatario],
        "subject": assunto,
        "text": corpo_texto,
    }
    if responder_para:
        payload["reply_to"] = responder_para

    try:
        resposta = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
            json=payload,
            timeout=10,
        )
        resposta.raise_for_status()
    except Exception:
        logger.exception("Falha ao enviar e-mail via Resend para %s", destinatario)


def _enviar_via_smtp(destinatario: str, assunto: str, corpo_texto: str, responder_para: str | None = None) -> None:
    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = config.SMTP_FROM
    mensagem["To"] = destinatario
    if responder_para:
        mensagem["Reply-To"] = responder_para
    mensagem.set_content(corpo_texto)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as servidor:
            servidor.starttls()
            if config.SMTP_USER:
                servidor.login(config.SMTP_USER, config.SMTP_PASSWORD)
            servidor.send_message(mensagem)
    except Exception:
        logger.exception("Falha ao enviar e-mail via SMTP para %s", destinatario)
