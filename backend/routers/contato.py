from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import config, models, schemas, security
from ..database import get_db
from ..email_utils import enviar_email

router = APIRouter(prefix="/api/contato", tags=["contato"])

CHAVE_EMAIL_FALE_CONOSCO = "email_fale_conosco"


def obter_email_fale_conosco(db: Session) -> str:
    registro = db.query(models.Configuracao).filter(models.Configuracao.chave == CHAVE_EMAIL_FALE_CONOSCO).first()
    return registro.valor if registro else config.EMAIL_FALE_CONOSCO


@router.post("")
def enviar_mensagem(
    dados: schemas.ContatoCreate,
    usuario: models.Usuario = Depends(security.obter_usuario_atual),
    db: Session = Depends(get_db),
):
    # Remove quebras de linha para evitar injeção de cabeçalhos no assunto do e-mail.
    assunto_limpo = " ".join(dados.assunto.split())
    corpo = (
        f"Mensagem enviada pelo Fale conosco do EletroCharge\n\n"
        f"Nome: {usuario.nome}\n"
        f"E-mail: {usuario.email}\n"
        f"Telefone: {usuario.telefone or 'não informado'}\n\n"
        f"{dados.mensagem}"
    )
    enviar_email(
        obter_email_fale_conosco(db),
        f"[Fale conosco] {assunto_limpo}",
        corpo,
        responder_para=usuario.email,
    )
    return {"mensagem": "Mensagem enviada! Responderemos em breve pelo seu e-mail."}
