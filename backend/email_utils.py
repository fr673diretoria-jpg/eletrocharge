"""Envio de e-mails transacionais (ex.: redefinição de senha)."""
import logging
import smtplib
from email.message import EmailMessage

from . import config

logger = logging.getLogger("eletrocharge.email")


def enviar_email(destinatario: str, assunto: str, corpo_texto: str) -> None:
    """Envia um e-mail via SMTP. Se SMTP_HOST não estiver configurado, apenas registra
    o conteúdo no log (útil em desenvolvimento local, sem servidor de e-mail).

    Qualquer falha de SMTP é apenas registrada no log: uma conta de e-mail mal configurada
    não pode derrubar o endpoint de "esqueci minha senha" (evita vazar detalhes e retornar 500)."""
    if not config.SMTP_HOST:
        logger.warning("SMTP não configurado. E-mail para %s:\n%s\n%s", destinatario, assunto, corpo_texto)
        return

    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = config.SMTP_FROM
    mensagem["To"] = destinatario
    mensagem.set_content(corpo_texto)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as servidor:
            servidor.starttls()
            if config.SMTP_USER:
                servidor.login(config.SMTP_USER, config.SMTP_PASSWORD)
            servidor.send_message(mensagem)
    except Exception:
        logger.exception("Falha ao enviar e-mail via SMTP para %s", destinatario)
        servidor.send_message(mensagem)
