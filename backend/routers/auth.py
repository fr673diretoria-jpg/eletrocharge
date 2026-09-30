from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import config, models, schemas, security
from ..database import get_db
from ..email_utils import enviar_email

router = APIRouter(prefix="/api/auth", tags=["autenticação"])


@router.post("/registrar", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def registrar(dados: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    usuario = models.Usuario(
        nome=dados.nome,
        email=dados.email,
        telefone=dados.telefone,
        senha_hash=security.hash_senha(dados.senha),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    usuario = security.sincronizar_admin(usuario, db)

    token = security.criar_token({"sub": str(usuario.id)})
    return schemas.Token(access_token=token, usuario=usuario)


@router.post("/login", response_model=schemas.Token)
def login(dados: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == dados.email).first()

    if not usuario or not security.verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    usuario = security.sincronizar_admin(usuario, db)
    token = security.criar_token({"sub": str(usuario.id)})
    return schemas.Token(access_token=token, usuario=usuario)


@router.get("/me", response_model=schemas.UsuarioOut)
def me(
    usuario: models.Usuario = Depends(security.obter_usuario_atual),
    db: Session = Depends(get_db),
):
    return security.sincronizar_admin(usuario, db)


@router.post("/esqueci-senha")
def esqueci_senha(dados: schemas.EsqueciSenha, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == dados.email).first()

    # Resposta genérica sempre, exista ou não o e-mail: evita revelar quais e-mails têm conta.
    if usuario:
        token = security.criar_token_reset_senha(usuario.id)
        link = f"{config.APP_BASE_URL}/?redefinir_senha={token}"
        corpo = (
            f"Olá, {usuario.nome}!\n\n"
            "Recebemos uma solicitação para redefinir a senha da sua conta EletroCharge.\n"
            f"Clique no link abaixo para escolher uma nova senha (válido por {config.RESET_SENHA_EXPIRA_MINUTOS} minutos):\n\n"
            f"{link}\n\n"
            "Se você não solicitou isso, apenas ignore este e-mail."
        )
        enviar_email(usuario.email, "Redefinição de senha - EletroCharge", corpo)

    return {"mensagem": "Se o e-mail existir, enviaremos um link de redefinição de senha."}


@router.post("/redefinir-senha")
def redefinir_senha(dados: schemas.RedefinirSenha, db: Session = Depends(get_db)):
    usuario_id = security.validar_token_reset_senha(dados.token)

    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link inválido ou expirado")

    usuario.senha_hash = security.hash_senha(dados.nova_senha)
    db.commit()

    return {"mensagem": "Senha redefinida com sucesso. Você já pode entrar com a nova senha."}
