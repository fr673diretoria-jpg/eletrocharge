from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

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
